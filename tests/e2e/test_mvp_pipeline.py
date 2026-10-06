from digital_archaeologist.collectors.web import WebCollector
from digital_archaeologist.domain.models import CandidateDraft, Evidence
from digital_archaeologist.discovery.pipeline import DiscoveryPipeline
from digital_archaeologist.research.investigator import ResearchInvestigator
from digital_archaeologist.research.provider import ResearchResponse
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


class FakeCollector:
    def collect(self):
        return [CandidateDraft(source="web", url="https://example.com/legacy", category="website", title="Legacy Tool", metadata={
            "demand_score": 22, "traction_score": 18, "neglect_score": 14, "resurrection_score": 12, "monetization_score": 12, "competition_score": 4, "license_clarity_score": 4,
        })]


class FakeAI:
    def __init__(self): self.calls = 0
    def generate(self, request):
        self.calls += 1
        return ResearchResponse(
            verdict="POSSIBLE", total_score=86, confidence=0.88,
            component_scores={"demand": 22, "existing_traction": 18, "neglect": 14, "ease_of_resurrection": 12, "monetisation": 12, "competition": 4, "licence_ownership": 4},
            evidence=[{"id": "e2e-1", "claim": "Public demand may remain visible", "evidence_type": "INFERRED", "source_evidence_ids": ["e2e-source"], "summary": "This is inferred from the supplied source."}],
            adversarial_findings=[{"id": "e2e-risk", "claim": "Commercial demand is not established", "evidence_type": "UNKNOWN", "source_evidence_ids": [], "summary": "No willingness-to-pay source was collected."}],
            risks=["Ownership needs confirmation"], recommendation="Manually investigate acquisition/rebuild options", adversarial_review="Demand may have shifted, so verify before investing.", next_action="Manual review",
        )


def test_mvp_pipeline_persists_candidate_evidence_and_report():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    discovery = DiscoveryPipeline([FakeCollector()], repo)
    summary = discovery.run()
    assert summary.new == 1
    candidate = repo.list_candidates()[0]
    repo.add_evidence(Evidence(id="e2e-source", candidate_id=candidate.id, claim="Source page was retrieved", evidence_type="observed", source_url="https://example.com/legacy", summary="Fixture source response."))
    ai = FakeAI()
    report = ResearchInvestigator(ai, repo).investigate(candidate)
    stored = repo.get_report(candidate.id)
    assert stored is not None
    assert stored.verdict == "POSSIBLE"
    assert "e2e-source" in stored.evidence_ids
    assert any(item.claim == "Public demand may remain visible" for item in repo.get_evidence(candidate.id))
    assert ai.calls == 2
