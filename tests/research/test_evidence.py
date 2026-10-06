import httpx

from digital_archaeologist.domain.models import Candidate
from digital_archaeologist.collectors.web import WebCollector
from digital_archaeologist.research.evidence import CandidateEvidenceCollector, GitHubEvidenceCollector


def test_github_collector_creates_observed_records_from_repository_and_issues():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/issues"):
            return httpx.Response(200, json=[
                {"number": 9, "title": "Need import support", "state": "open", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-02-01T00:00:00Z", "comments": 2, "body": "Please add CSV import.", "html_url": "https://github.com/o/r/issues/9"},
                {"number": 10, "title": "PR", "pull_request": {"url": "https://api.github.com/pulls/10"}},
            ])
        return httpx.Response(200, json={"full_name": "o/r", "stargazers_count": 12, "open_issues_count": 1, "archived": False})

    collector = GitHubEvidenceCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    candidate = Candidate(canonical_identity="github:o/r", source="github", url="https://github.com/o/r", category="software")
    records = collector.collect(candidate)
    assert calls == ["/repos/o/r", "/repos/o/r/issues"]
    assert len(records) == 2
    assert all(record.evidence_type == "observed" and record.candidate_id == candidate.id for record in records)
    assert records[1].source_url == "https://github.com/o/r/issues/9"
    assert "Please add CSV import" in records[1].summary


def test_web_source_is_collected_as_observed_and_failed_fetch_is_not_an_opportunity():
    def handler(request):
        return httpx.Response(200, text="<html><title>Archive</title><meta name='description' content='A public project'></html>")

    web = WebCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    candidate = Candidate(canonical_identity="web:example.test", source="web", url="https://example.test", category="website")
    records = CandidateEvidenceCollector(web=web).collect(candidate)
    assert records[0].evidence_type == "observed"
    assert records[0].source_url == "https://example.test"
    assert "A public project" in records[0].summary

    failed_web = WebCollector(client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))))
    import pytest
    from digital_archaeologist.collectors.base import CollectorError
    with pytest.raises(CollectorError, match="could not be retrieved"):
        CandidateEvidenceCollector(web=failed_web).collect(candidate)
