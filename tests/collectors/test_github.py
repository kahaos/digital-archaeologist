import httpx
import pytest

from digital_archaeologist.collectors.github import GitHubCollector, CollectorError


def test_github_maps_repository_signals():
    payload = {
        "full_name": "owner/repo", "html_url": "https://github.com/owner/repo", "name": "repo",
        "description": "Useful project", "stargazers_count": 123, "forks_count": 17,
        "open_issues_count": 4, "updated_at": "2024-01-02T03:04:05Z",
        "license": {"spdx_id": "MIT"}, "archived": False,
    }
    def handler(request):
        return httpx.Response(200, json={"items": [payload]})
    collector = GitHubCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    results = collector.search("neglected tool")
    assert len(results) == 1
    draft = results[0]
    assert draft.url == payload["html_url"]
    assert draft.metadata["stars"] == 123
    assert draft.metadata["forks"] == 17
    assert draft.metadata["open_issues"] == 4
    assert draft.metadata["last_activity"] == "2024-01-02T03:04:05Z"
    assert draft.metadata["license"] == "MIT"


def test_github_missing_optional_fields_do_not_crash():
    payload = {"full_name": "owner/empty", "html_url": "https://github.com/owner/empty", "name": "empty"}
    def handler(request):
        return httpx.Response(200, json={"items": [payload]})
    collector = GitHubCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    draft = collector.search("empty")[0]
    assert draft.metadata["stars"] is None
    assert draft.metadata["forks"] is None
    assert draft.metadata["open_issues"] is None
    assert draft.metadata["archived"] is None
    assert draft.metadata["license"] is None


def test_github_rate_limit_is_controlled_error():
    def handler(request):
        return httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={"message": "API rate limit exceeded"})
    collector = GitHubCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(CollectorError, match="rate limit"):
        collector.search("anything")
