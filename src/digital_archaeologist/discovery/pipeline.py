from __future__ import annotations

from pydantic import BaseModel

from digital_archaeologist.collectors.base import Collector
from digital_archaeologist.domain.models import Candidate, CandidateDraft
from digital_archaeologist.scoring.scorer import score_candidate
from digital_archaeologist.storage.repositories import Repository
from .deduplicator import deduplicate
from .normalizer import normalize_candidate


class DiscoveryRunSummary(BaseModel):
    discovered: int = 0
    new: int = 0
    duplicates: int = 0
    failed: int = 0
    scoreable: int = 0


class DiscoveryPipeline:
    def __init__(self, collectors: list[Collector], repository: Repository) -> None:
        self.collectors = collectors
        self.repository = repository

    def run(self) -> DiscoveryRunSummary:
        summary = DiscoveryRunSummary()
        drafts: list[CandidateDraft] = []
        for collector in self.collectors:
            try:
                collected = collector.collect()
            except Exception:
                summary.failed += 1
                continue
            summary.discovered += len(collected)
            drafts.extend(collected)
        normalized = [normalize_candidate(draft) for draft in drafts]
        unique = deduplicate(normalized)
        summary.duplicates = len(normalized) - len(unique)
        for draft in unique:
            existing = next((c for c in self.repository.list_candidates() if c.canonical_identity == draft.canonical_identity), None)
            candidate = _candidate_from_draft(draft, existing)
            if existing is None:
                summary.new += 1
            score = score_candidate(candidate)
            candidate.score = score.total_score
            self.repository.upsert_candidate(candidate)
            summary.scoreable += 1
        return summary


def _candidate_from_draft(draft: CandidateDraft, existing: Candidate | None) -> Candidate:
    if existing is None:
        return Candidate(
            canonical_identity=draft.canonical_identity,
            source=draft.source,
            url=draft.url,
            category=draft.category,
            title=draft.title,
            metadata=draft.metadata,
            provenance_urls=draft.provenance_urls,
            discovered_at=draft.discovered_at,
        )
    return existing.model_copy(update={
        "source": draft.source,
        "url": draft.url,
        "category": draft.category,
        "title": draft.title or existing.title,
        "metadata": {**existing.metadata, **draft.metadata},
        "provenance_urls": list(dict.fromkeys([*existing.provenance_urls, *draft.provenance_urls])),
    })
