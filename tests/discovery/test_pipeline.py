from digital_archaeologist.collectors.base import CollectorError
from digital_archaeologist.domain.models import CandidateDraft
from digital_archaeologist.discovery.pipeline import DiscoveryPipeline
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


class FakeCollector:
    def __init__(self, drafts): self.drafts = drafts
    def collect(self): return list(self.drafts)

class FailingCollector:
    def collect(self): raise CollectorError("source unavailable")


def test_pipeline_normalizes_deduplicates_persists_and_scores():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    drafts = [
        CandidateDraft(source="web", url="https://Example.com/tool/?utm_source=x", category="website", metadata={"demand_score": 20}),
        CandidateDraft(source="web", url="https://example.com/tool", category="website", metadata={"demand_score": 20}),
    ]
    summary = DiscoveryPipeline([FakeCollector(drafts)], repo).run()
    candidates = repo.list_candidates()
    assert summary.discovered == 2
    assert summary.duplicates == 1
    assert summary.new == 1
    assert len(candidates) == 1
    assert candidates[0].score == 20


def test_pipeline_rerun_is_idempotent_and_isolates_collector_failures():
    repo = Repository(Database("sqlite+pysqlite:///:memory:"))
    draft = CandidateDraft(source="web", url="https://example.com", category="website")
    pipeline = DiscoveryPipeline([FailingCollector(), FakeCollector([draft])], repo)
    first = pipeline.run()
    second = pipeline.run()
    assert first.failed == 1 and first.new == 1
    assert second.failed == 1 and second.new == 0
    assert len(repo.list_candidates()) == 1
