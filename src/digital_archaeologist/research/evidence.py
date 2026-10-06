from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx

from digital_archaeologist.collectors.base import CollectorError
from digital_archaeologist.collectors.web import WebCollector
from digital_archaeologist.config import Settings
from digital_archaeologist.domain.models import Candidate, Evidence


class GitHubEvidenceCollector:
    """Fetch source records from a candidate's public GitHub repository."""

    BASE_URL = "https://api.github.com"

    def __init__(self, client: httpx.Client | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "digital-archaeologist/0.1"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        self.client = client or httpx.Client(timeout=self.settings.request_timeout_seconds, headers=headers)

    def collect(self, candidate: Candidate) -> list[Evidence]:
        parsed = urlparse(candidate.url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.hostname not in {"github.com", "www.github.com"} or len(parts) < 2:
            raise CollectorError("candidate is not a GitHub repository URL")
        owner, repository = parts[0], parts[1].removesuffix(".git")
        api_url = f"{self.BASE_URL}/repos/{owner}/{repository}"
        metadata = self._get(api_url)
        records = [Evidence(
            candidate_id=candidate.id,
            claim=f"GitHub repository metadata for {metadata.get('full_name') or owner + '/' + repository}",
            evidence_type="observed",
            source_url=api_url,
            summary=json.dumps({key: metadata.get(key) for key in (
                "full_name", "description", "created_at", "updated_at", "pushed_at", "archived",
                "disabled", "fork", "stargazers_count", "forks_count", "open_issues_count",
                "license", "language", "topics", "size", "has_issues",
            )}, sort_keys=True, default=str),
        )]
        issues_url = f"{api_url}/issues?state=all&per_page=20&sort=updated&direction=desc"
        try:
            response = self.client.get(issues_url, headers=self._headers())
            if response.status_code >= 400:
                raise CollectorError(f"GitHub issue evidence returned HTTP {response.status_code}")
            issues = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CollectorError(f"GitHub issue evidence request failed: {exc}") from exc
        if not isinstance(issues, list):
            raise CollectorError("GitHub issue evidence response was not a list")
        for issue in [item for item in issues if isinstance(item, dict) and "pull_request" not in item][:10]:
            records.append(Evidence(
                candidate_id=candidate.id,
                claim=f"GitHub issue #{issue.get('number')}: {issue.get('title') or 'Untitled'}",
                evidence_type="observed",
                source_url=issue.get("html_url") or issues_url,
                summary=json.dumps({key: (issue.get(key)[:5000] if key == "body" and isinstance(issue.get(key), str) else issue.get(key)) for key in ("number", "title", "state", "created_at", "updated_at", "comments", "body")}, sort_keys=True, default=str),
            ))
        return records

    def _get(self, url: str) -> dict:
        try:
            response = self.client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise CollectorError(f"GitHub repository evidence request failed: {exc}") from exc
        if response.status_code >= 400:
            raise CollectorError(f"GitHub repository evidence returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise CollectorError("GitHub repository evidence response was invalid JSON") from exc
        if not isinstance(payload, dict):
            raise CollectorError("GitHub repository evidence response was not an object")
        return payload

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "digital-archaeologist/0.1"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers


class CandidateEvidenceCollector:
    """Dispatch read-only source collection for the candidate's discovery source."""

    def __init__(self, *, github: GitHubEvidenceCollector | None = None, web: WebCollector | None = None) -> None:
        self.github = github or GitHubEvidenceCollector()
        self.web = web or WebCollector()

    def collect(self, candidate: Candidate) -> list[Evidence]:
        if candidate.source == "github":
            return self.github.collect(candidate)
        if candidate.source == "web":
            draft = self.web.inspect(candidate.url)
            if draft.metadata.get("ok") is not True:
                raise CollectorError("public web evidence could not be retrieved")
            return [Evidence(
                candidate_id=candidate.id,
                claim="Public page metadata retrieved",
                evidence_type="observed",
                source_url=draft.url,
                summary=json.dumps({"title": draft.title, **draft.metadata}, sort_keys=True, default=str),
            )]
        raise CollectorError(f"no public evidence collector for source: {candidate.source}")
