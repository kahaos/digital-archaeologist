from __future__ import annotations
import logging
import uuid
from digital_archaeologist.collectors.github import GitHubCollector
from digital_archaeologist.collectors.web import WebCollector
from digital_archaeologist.config import Settings
from digital_archaeologist.discovery.pipeline import DiscoveryPipeline, DiscoveryRunSummary
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository

logger = logging.getLogger(__name__)

def run_discovery_job(*, pipeline: DiscoveryPipeline | None = None) -> DiscoveryRunSummary:
    run_id = uuid.uuid4().hex
    logger.info("discovery run started run_id=%s", run_id)
    if pipeline is None:
        settings = Settings()
        repo = Repository(Database(settings.database_url))
        pipeline = DiscoveryPipeline([GitHubCollector(settings=settings), WebCollector(settings=settings)], repo)
    summary = pipeline.run()
    logger.info("discovery run finished run_id=%s discovered=%s new=%s failed=%s", run_id, summary.discovered, summary.new, summary.failed)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print((run_discovery_job() if "run_discovery_job" in globals() else run_investigation_job()).model_dump_json())
