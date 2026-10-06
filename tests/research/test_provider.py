import httpx
import json
import pytest

from digital_archaeologist.config import Settings
from digital_archaeologist.research.provider import OpenAIResponsesProvider, ProviderError, ResearchRequest, create_research_provider


def test_openai_provider_sends_evidence_context_and_returns_json_without_storing_response():
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"verdict":"POSSIBLE"}'}]}]})

    provider = OpenAIResponsesProvider("secret", "test-model", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.generate(ResearchRequest(candidate={"url": "https://github.com/o/r"}, evidence=[{"id": "source-1"}], phase="adversarial", instructions="challenge it"))
    assert result == {"verdict": "POSSIBLE"}
    assert sent["store"] is False
    assert sent["text"]["format"]["type"] == "json_object"
    assert '"source-1"' in sent["input"]


def test_provider_factory_requires_explicit_supported_provider_and_key():
    settings = Settings()
    assert create_research_provider(settings) is None
    object.__setattr__(settings, "ai_provider", "openai")
    with pytest.raises(ProviderError, match="DA_AI_API_KEY"):
        create_research_provider(settings)
