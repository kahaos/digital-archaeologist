from __future__ import annotations
import logging
import uuid
from pydantic import BaseModel
from digital_archaeologist.config import Settings
from digital_archaeologist.research.evidence import CandidateEvidenceCollector, GitHubEvidenceCollector
from digital_archaeologist.research.investigator import ResearchInvestigator
from digital_archaeologist.research.provider import ProviderError, create_research_provider
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository

logger = logging.getLogger(__name__)

class InvestigationRunSummary(BaseModel):
    investigated: int = 0
    failed: int = 0
    skipped: int = 0


def run_investigation_job(*, repository: Repository | None = None, investigator: ResearchInvestigator | None = None, limit: int = 20, threshold: float | None = None) -> InvestigationRunSummary:
    run_id = uuid.uuid4().hex
    settings = Settings()
    repository = repository or Repository(Database(settings.database_url))
    if investigator is None:
        try:
            provider = create_research_provider(settings)
        except ProviderError as exc:
            raise RuntimeError(str(exc)) from exc
        if provider is None:
            raise RuntimeError("Real provider investigation NOT RUN — provider credentials/configuration unavailable.")
        investigator = ResearchInvestigator(provider, repository, CandidateEvidenceCollector(github=GitHubEvidenceCollector(settings=settings)))
    candidates = [c for c in repository.list_candidates() if c.score is not None and (threshold is None or c.score >= threshold)]
    candidates.sort(key=lambda item: (-float(item.score or 0), item.canonical_identity))
    summary = InvestigationRunSummary()
    for candidate in candidates[:limit]:
        if repository.get_report(candidate.id) is not None:
            summary.skipped += 1
            continue
        candidate.status = "RESEARCH"
        repository.upsert_candidate(candidate)
        try:
            report = investigator.investigate(candidate)
            candidate.status = "REJECTED" if report.verdict == "REJECT" else "IGNORE" if report.verdict == "WEAK" else "WATCH"
            repository.upsert_candidate(candidate)
            summary.investigated += 1
        except Exception as exc:
            summary.failed += 1
            candidate.status = "NEW"
            repository.upsert_candidate(candidate)
            logger.exception("investigation failed run_id=%s candidate=%s error=%s", run_id, candidate.id, exc)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print((run_discovery_job() if "run_discovery_job" in globals() else run_investigation_job()).model_dump_json())
