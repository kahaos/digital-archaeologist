import pytest

from digital_archaeologist.domain.models import Candidate, Evidence
from digital_archaeologist.research.investigator import ResearchInvestigator
from digital_archaeologist.research.provider import ResearchResponse
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return next(self.responses)


def response(phase="initial", verdict="POSSIBLE", review="Counterpoint checked"):
    return ResearchResponse(
        verdict=verdict, total_score=72, confidence=0.8,
        component_scores={"demand": 18, "existing_traction": 15, "neglect": 12, "ease_of_resurrection": 11, "monetisation": 10, "competition": 3, "licence_ownership": 3},
        evidence=[{"id": f"{phase}-claim", "claim": "Issue activity may indicate unresolved need", "evidence_type": "INFERRED", "source_evidence_ids": ["source-1"], "summary": "Issue activity is an imperfect demand proxy."}],
        adversarial_findings=([{"id": "counter", "claim": "Buyer demand is not established", "evidence_type": "INFERRED", "source_evidence_ids": ["source-1"], "summary": "Repository activity does not establish willingness to pay."}] if phase == "adversarial" else []),
        risks=["Competition may be strong"], recommendation="Continue research", adversarial_review=review, next_action="Check market evidence",
    )


def setup_candidate():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    candidate = Candidate(canonical_identity="github:example/project", source="github", url="https://github.com/example/project", category="software")
    repo.upsert_candidate(candidate)
    repo.add_evidence(Evidence(id="source-1", candidate_id=candidate.id, claim="GitHub reports 12 open issues", evidence_type="observed", source_url="https://api.github.com/repos/example/project", summary="12 open issues returned by GitHub API."))
    return repo, candidate


def test_investigator_persists_source_facts_findings_and_adversarial_review():
    repo, candidate = setup_candidate()
    provider = FakeProvider([response(), response("adversarial")])
    report = ResearchInvestigator(provider, repo).investigate(candidate)
    assert report.verdict == "POSSIBLE"
    assert report.adversarial_review.endswith("Counterpoint checked")
    assert report.next_action == "Human review required before any action"
    assert report.recommendation.startswith("AI analysis for human review only")
    assert report.adversarial_review.startswith("AI sceptical analysis")
    assert report.risks == ["[INFERRED] Buyer demand is not established"]
    assert provider.requests[1].phase == "adversarial"
    assert provider.requests[1].prior_analysis
    records = repo.get_evidence(candidate.id)
    assert records[0].evidence_type == "observed"
    assert len(records) == 4
    assert all(item.supporting_evidence_ids == ["source-1"] for item in records[1:])
    assert set(report.evidence_ids) == {item.id for item in records}
    stored = repo.get_report(candidate.id)
    assert stored.adversarial_review.endswith("Counterpoint checked")
    assert stored.next_action.startswith("Human review")


def test_strong_verdict_requires_a_real_sceptical_pass_and_counterpoint():
    repo, candidate = setup_candidate()
    provider = FakeProvider([response(verdict="STRONG OPPORTUNITY"), response("adversarial", "STRONG OPPORTUNITY", "")])
    with pytest.raises(ValueError, match="adversarial"):
        ResearchInvestigator(provider, repo).investigate(candidate)
    assert repo.get_report(candidate.id) is None


def test_investigation_requires_collected_source_evidence_before_provider_calls():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    candidate = Candidate(canonical_identity="github:example/project", source="github", url="https://github.com/example/project", category="software")
    repo.upsert_candidate(candidate)
    provider = FakeProvider([])
    with pytest.raises(ValueError, match="source evidence"):
        ResearchInvestigator(provider, repo).investigate(candidate)
    assert provider.requests == []
