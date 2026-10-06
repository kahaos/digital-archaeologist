from digital_archaeologist.domain.models import Candidate, OpportunityReport
from digital_archaeologist.jobs.run_discovery import run_discovery_job
from digital_archaeologist.jobs.run_investigation import run_investigation_job
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


class FakePipeline:
    def __init__(self): self.calls = 0
    def run(self):
        self.calls += 1
        return type("Summary", (), {"discovered": 1, "new": 1, "duplicates": 0, "failed": 0, "scoreable": 1})()


class FakeInvestigator:
    def __init__(self, repo, failing_id=None): self.repo = repo; self.failing_id = failing_id; self.seen = []
    def investigate(self, candidate):
        self.seen.append(candidate.id)
        if candidate.id == self.failing_id: raise RuntimeError("bad candidate")
        report = OpportunityReport(candidate_id=candidate.id, total_score=candidate.score or 0, confidence=0.7, verdict="POSSIBLE", recommendation="Review")
        self.repo.save_report(report)
        return report


def test_repeated_discovery_job_delegates_cleanly_to_idempotent_pipeline():
    pipeline = FakePipeline()
    first = run_discovery_job(pipeline=pipeline)
    second = run_discovery_job(pipeline=pipeline)
    assert first.discovered == second.discovered == 1
    assert pipeline.calls == 2


def test_investigation_only_processes_candidates_above_threshold_and_skips_existing_reports():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    low = Candidate(canonical_identity="low", source="web", url="https://low.test", category="website", score=60)
    high = Candidate(canonical_identity="high", source="web", url="https://high.test", category="website", score=80)
    done = Candidate(canonical_identity="done", source="web", url="https://done.test", category="website", score=95)
    for c in [low, high, done]: repo.upsert_candidate(c)
    repo.save_report(OpportunityReport(candidate_id=done.id, total_score=95, confidence=0.9, verdict="POSSIBLE", recommendation="Done"))
    investigator = FakeInvestigator(repo)
    summary = run_investigation_job(repository=repo, investigator=investigator, limit=10, threshold=75)
    assert summary.investigated == 1
    assert summary.failed == 0
    assert investigator.seen == [high.id]


def test_failed_investigation_does_not_stop_subsequent_candidates():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    a = Candidate(canonical_identity="a", source="web", url="https://a.test", category="website", score=90)
    b = Candidate(canonical_identity="b", source="web", url="https://b.test", category="website", score=89)
    repo.upsert_candidate(a); repo.upsert_candidate(b)
    investigator = FakeInvestigator(repo, failing_id=a.id)
    summary = run_investigation_job(repository=repo, investigator=investigator, limit=10, threshold=75)
    assert summary.failed == 1
    assert summary.investigated == 1
    assert set(investigator.seen) == {a.id, b.id}


def test_default_investigation_selects_twenty_highest_scores_including_scores_below_old_threshold():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    candidates = [Candidate(canonical_identity=f"github:o/r{i}", source="github", url=f"https://github.com/o/r{i}", category="software", score=float(i)) for i in range(25)]
    for candidate in candidates:
        repo.upsert_candidate(candidate)
    investigator = FakeInvestigator(repo)
    summary = run_investigation_job(repository=repo, investigator=investigator)
    assert summary.investigated == 20
    assert set(investigator.seen) == {c.id for c in candidates[5:]}
    assert investigator.seen == [c.id for c in reversed(candidates[5:])]
    assert all(repo.get_candidate(c.id).status == "WATCH" for c in candidates[5:])


def test_job_reports_unavailable_provider_without_processing_candidates(monkeypatch):
    monkeypatch.setenv("DA_AI_PROVIDER", "none")
    monkeypatch.delenv("DA_AI_API_KEY", raising=False)
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    candidate = Candidate(canonical_identity="github:o/r", source="github", url="https://github.com/o/r", category="software", score=90)
    repo.upsert_candidate(candidate)
    import pytest
    with pytest.raises(RuntimeError, match="Real provider investigation NOT RUN"):
        run_investigation_job(repository=repo)
    assert repo.get_candidate(candidate.id).status == "NEW"
