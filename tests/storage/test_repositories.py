from datetime import datetime, timezone
import sqlite3

from digital_archaeologist.domain.models import Candidate, Evidence, OpportunityReport
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


def make_repo():
    return Repository(Database("sqlite+pysqlite:///:memory:"))


def test_candidate_insert_and_retrieval():
    repo = make_repo()
    candidate = Candidate(canonical_identity="github:owner/repo", source="github", url="https://github.com/owner/repo", category="software")
    repo.upsert_candidate(candidate)
    found = repo.get_candidate(candidate.id)
    assert found is not None
    assert found.canonical_identity == "github:owner/repo"


def test_candidate_upsert_is_idempotent_on_canonical_identity():
    repo = make_repo()
    first = Candidate(canonical_identity="github:owner/repo", source="github", url="https://github.com/owner/repo", category="software")
    second = Candidate(canonical_identity="github:owner/repo", source="github", url="https://github.com/owner/repo", category="software", status="WATCH")
    a = repo.upsert_candidate(first)
    b = repo.upsert_candidate(second)
    assert a.id == b.id
    assert repo.list_candidates() and len(repo.list_candidates()) == 1
    assert repo.get_candidate(a.id).status == "WATCH"


def test_evidence_references_existing_candidate():
    repo = make_repo()
    candidate = Candidate(canonical_identity="web:example.com", source="web", url="https://example.com", category="website")
    repo.upsert_candidate(candidate)
    evidence = Evidence(candidate_id=candidate.id, claim="Site returned 200", evidence_type="observed", source_url="https://example.com", summary="HTTP 200")
    stored = repo.add_evidence(evidence)
    assert stored.candidate_id == candidate.id
    assert repo.get_evidence(candidate.id)[0].claim == "Site returned 200"


def test_report_can_be_stored_and_retrieved_with_evidence_ids():
    repo = make_repo()
    candidate = Candidate(canonical_identity="github:owner/repo", source="github", url="https://github.com/owner/repo", category="software")
    repo.upsert_candidate(candidate)
    report = OpportunityReport(candidate_id=candidate.id, total_score=82, confidence=0.8, verdict="STRONG OPPORTUNITY", risks=["unknown demand"], recommendation="Research further", evidence_ids=[])
    repo.save_report(report)
    found = repo.get_report(candidate.id)
    assert found is not None
    assert found.total_score == 82
    assert found.verdict == "STRONG OPPORTUNITY"

def test_default_database_creates_parent_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = Database()
    assert (tmp_path / "data" / "digital_archaeologist.db").exists()
    assert db.engine is not None


def test_database_additive_migration_adds_research_provenance_columns(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE evidence (id VARCHAR(36) PRIMARY KEY, candidate_id VARCHAR(36), claim TEXT, evidence_type VARCHAR(32), source_url TEXT, summary TEXT, collected_at DATETIME)")
        connection.execute("CREATE TABLE opportunity_reports (candidate_id VARCHAR(36) PRIMARY KEY, component_scores_json TEXT, total_score FLOAT, confidence FLOAT, verdict VARCHAR(64), risks_json TEXT, recommendation TEXT, evidence_ids_json TEXT, created_at DATETIME)")
    Database(f"sqlite+pysqlite:///{path}")
    with sqlite3.connect(path) as connection:
        evidence_columns = {row[1] for row in connection.execute("PRAGMA table_info(evidence)")}
        report_columns = {row[1] for row in connection.execute("PRAGMA table_info(opportunity_reports)")}
    assert "supporting_evidence_ids_json" in evidence_columns
    assert {"adversarial_review", "next_action"} <= report_columns
