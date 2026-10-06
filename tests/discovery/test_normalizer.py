from digital_archaeologist.domain.models import CandidateDraft
from digital_archaeologist.discovery.normalizer import canonical_identity, normalize_candidate


def test_normalize_url_removes_tracking_and_canonicalizes_host():
    draft = CandidateDraft(source="web", url="HTTPS://Example.COM/tool/?utm_source=x&ref=abc&keep=1", category="website")
    normalized = normalize_candidate(draft)
    assert normalized.url == "https://example.com/tool?keep=1"
    assert normalized.provenance_urls == ["HTTPS://Example.COM/tool/?utm_source=x&ref=abc&keep=1"]


def test_github_urls_get_stable_identity():
    draft = CandidateDraft(source="github", url="https://github.com/Owner/Repo/", category="software")
    assert canonical_identity(draft) == "github:owner/repo"
