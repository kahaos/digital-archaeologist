from digital_archaeologist.domain.models import CandidateDraft
from digital_archaeologist.discovery.deduplicator import deduplicate
from digital_archaeologist.discovery.normalizer import normalize_candidate


def test_equivalent_github_urls_collapse_to_one():
    drafts = [
        normalize_candidate(CandidateDraft(source="github", url="https://github.com/Owner/Repo/", category="software")),
        normalize_candidate(CandidateDraft(source="github", url="https://github.com/owner/repo", category="software")),
    ]
    result = deduplicate(drafts)
    assert len(result) == 1


def test_duplicate_provenance_is_retained():
    a = normalize_candidate(CandidateDraft(source="github", url="https://github.com/owner/repo", category="software"))
    b = normalize_candidate(CandidateDraft(source="web", url="https://github.com/owner/repo/", category="software"))
    result = deduplicate([a, b])
    assert len(result) == 1
    assert set(result[0].provenance_urls) == {"https://github.com/owner/repo", "https://github.com/owner/repo/"}
    assert set(result[0].metadata["sources"]) == {"github", "web"}
