from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from digital_archaeologist.config import Settings
from digital_archaeologist.domain.models import CandidateDraft


class WebCollector:
    def __init__(self, client: httpx.Client | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.client = client or httpx.Client(timeout=self.settings.request_timeout_seconds, follow_redirects=True, headers={"User-Agent": "digital-archaeologist/0.1"})

    def inspect(self, url: str) -> CandidateDraft:
        base = dict(canonical_identity=f"web:{url}", source="web", url=url, category="website", provenance_urls=[url])
        try:
            response = self.client.get(url)
        except httpx.HTTPError as exc:
            return CandidateDraft(**base, metadata={"ok": False, "error": "request_failed", "detail": str(exc)})
        if len(response.content) > self.settings.max_response_bytes:
            return CandidateDraft(**base, metadata={"ok": False, "status_code": response.status_code, "error": "response_too_large"})
        if response.status_code >= 400:
            return CandidateDraft(**base, metadata={"ok": False, "status_code": response.status_code, "error": "http_error"})
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        description = None
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            description = meta.get("content")
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
        return CandidateDraft(
            **base,
            title=title,
            metadata={"ok": True, "status_code": response.status_code, "description": description, "headings": headings, "content_type": response.headers.get("content-type")},
        )

    def collect(self) -> list[CandidateDraft]:
        return [self.inspect(url) for url in self.settings.web_seed_urls]
