from __future__ import annotations

from typing import Any

import httpx

from digital_archaeologist.config import Settings
from digital_archaeologist.domain.models import CandidateDraft
from .base import CollectorError


class GitHubCollector:
    BASE_URL = "https://api.github.com"

    def __init__(self, client: httpx.Client | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._owned_client = client is None
        self.client = client or httpx.Client(timeout=self.settings.request_timeout_seconds, headers=self._headers())

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "digital-archaeologist/0.1"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    def search(self, query: str, page: int = 1) -> list[CandidateDraft]:
        try:
            response = self.client.get(f"{self.BASE_URL}/search/repositories", params={"q": query, "page": page, "per_page": 100}, headers=self._headers())
        except httpx.HTTPError as exc:
            raise CollectorError(f"github request failed: {exc}") from exc
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise CollectorError("github rate limit exceeded")
        if response.status_code >= 400:
            raise CollectorError(f"github returned HTTP {response.status_code}")
        try:
            items = response.json().get("items", [])
        except ValueError as exc:
            raise CollectorError("github returned invalid JSON") from exc
        return [self._to_draft(item) for item in items]

    def collect(self) -> list[CandidateDraft]:
        drafts: list[CandidateDraft] = []
        for query in self.settings.github_queries:
            drafts.extend(self.search(query))
        return drafts

    @staticmethod
    def _to_draft(item: dict[str, Any]) -> CandidateDraft:
        full_name = item.get("full_name") or item.get("name") or "unknown"
        license_info = item.get("license") or {}
        return CandidateDraft(
            canonical_identity=f"github:{full_name.lower()}",
            source="github",
            url=item.get("html_url") or f"https://github.com/{full_name}",
            category="software",
            title=item.get("name") or full_name,
            metadata={
                "description": item.get("description"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "open_issues": item.get("open_issues_count"),
                "last_activity": item.get("updated_at"),
                "license": license_info.get("spdx_id") if isinstance(license_info, dict) else None,
                "archived": item.get("archived"),
                "owner": (item.get("owner") or {}).get("login") if isinstance(item.get("owner"), dict) else None,
            },
            provenance_urls=[item.get("html_url") or f"https://github.com/{full_name}"],
        )
