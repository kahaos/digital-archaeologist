from __future__ import annotations

import json
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from digital_archaeologist.config import Settings
from .validator import ResearchResponse


class ResearchRequest(BaseModel):
    candidate: dict[str, Any]
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    phase: str = "initial"
    instructions: str = ""
    prior_analysis: dict[str, Any] | None = None


class ResearchProvider(Protocol):
    def generate(self, request: ResearchRequest) -> Any: ...


class ProviderError(RuntimeError):
    pass


class OpenAIResponsesProvider:
    """Minimal OpenAI Responses API adapter using structured JSON mode."""

    ENDPOINT = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, model: str, *, client: httpx.Client | None = None, timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def generate(self, request: ResearchRequest) -> Any:
        prompt = {
            "candidate": request.candidate,
            "source_evidence": request.evidence,
            "phase": request.phase,
            "prior_analysis": request.prior_analysis,
            "required_output": "Return one JSON object matching the research response contract.",
        }
        try:
            response = self.client.post(
                self.ENDPOINT,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "instructions": request.instructions,
                    "input": json.dumps(prompt, sort_keys=True, default=str),
                    "text": {"format": {"type": "json_object"}},
                    "store": False,
                },
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"research provider request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"research provider returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("research provider returned invalid JSON") from exc
        output_text = payload.get("output_text") if isinstance(payload, dict) else None
        if not output_text and isinstance(payload, dict):
            output_text = next((part.get("text") for item in payload.get("output", []) if isinstance(item, dict)
                                for part in item.get("content", []) if isinstance(part, dict) and part.get("type") == "output_text"), None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ProviderError("research provider returned no output text")
        try:
            return json.loads(output_text)
        except ValueError as exc:
            raise ProviderError("research provider returned malformed response JSON") from exc


def create_research_provider(settings: Settings | None = None, *, client: httpx.Client | None = None) -> ResearchProvider | None:
    settings = settings or Settings()
    provider_name = settings.ai_provider.strip().lower()
    if provider_name in {"", "none"}:
        return None
    if provider_name != "openai":
        raise ProviderError(f"unsupported research provider: {settings.ai_provider}")
    if not settings.ai_api_key:
        raise ProviderError("DA_AI_API_KEY is required when DA_AI_PROVIDER=openai")
    return OpenAIResponsesProvider(settings.ai_api_key, settings.ai_model, client=client, timeout=settings.request_timeout_seconds)
