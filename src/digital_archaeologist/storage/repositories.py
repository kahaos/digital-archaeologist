from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from digital_archaeologist.domain.models import Candidate, Evidence, OpportunityReport
from .database import Base, Database


class CandidateRow(Base):
    __tablename__ = "candidates"
    __table_args__ = (UniqueConstraint("canonical_identity", name="uq_candidate_identity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_identity: Mapped[str] = mapped_column(String(512), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    provenance_json: Mapped[str] = mapped_column(Text, default="[]")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    claim: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    supporting_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ReportRow(Base):
    __tablename__ = "opportunity_reports"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    component_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    total_score: Mapped[float] = mapped_column(Float, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    verdict: Mapped[str] = mapped_column(String(64), index=True)
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    recommendation: Mapped[str] = mapped_column(Text)
    adversarial_review: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="Human review required before any action")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Repository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_candidate(self, candidate: Candidate) -> Candidate:
        with Session(self.database.engine) as session:
            row = session.scalar(select(CandidateRow).where(CandidateRow.canonical_identity == candidate.canonical_identity))
            if row is None:
                row = CandidateRow(id=candidate.id)
                session.add(row)
            row.canonical_identity = candidate.canonical_identity
            row.source = candidate.source
            row.url = candidate.url
            row.category = candidate.category
            row.title = candidate.title
            row.metadata_json = json.dumps(candidate.metadata, sort_keys=True, default=str)
            row.provenance_json = json.dumps(candidate.provenance_urls, sort_keys=True)
            row.discovered_at = candidate.discovered_at
            row.updated_at = datetime.now(timezone.utc)
            row.status = candidate.status
            row.score = candidate.score
            session.commit()
            candidate.id = row.id
            candidate.updated_at = row.updated_at
            return candidate

    def get_candidate(self, candidate_id: str) -> Candidate | None:
        with Session(self.database.engine) as session:
            row = session.get(CandidateRow, candidate_id)
            return _candidate_from_row(row) if row else None

    def list_candidates(self, *, status: str | None = None) -> list[Candidate]:
        with Session(self.database.engine) as session:
            stmt = select(CandidateRow).order_by(CandidateRow.discovered_at.desc())
            if status:
                stmt = stmt.where(CandidateRow.status == status)
            return [_candidate_from_row(row) for row in session.scalars(stmt)]

    def add_evidence(self, evidence: Evidence) -> Evidence:
        with Session(self.database.engine) as session:
            if session.get(CandidateRow, evidence.candidate_id) is None:
                raise ValueError(f"candidate {evidence.candidate_id} does not exist")
            row = EvidenceRow(
                id=evidence.id, candidate_id=evidence.candidate_id, claim=evidence.claim,
                evidence_type=evidence.evidence_type, source_url=evidence.source_url,
                summary=evidence.summary, supporting_evidence_ids_json=json.dumps(evidence.supporting_evidence_ids), collected_at=evidence.collected_at,
            )
            session.add(row)
            session.commit()
            return evidence

    def get_evidence(self, candidate_id: str) -> list[Evidence]:
        with Session(self.database.engine) as session:
            rows = session.scalars(select(EvidenceRow).where(EvidenceRow.candidate_id == candidate_id).order_by(EvidenceRow.collected_at.asc()))
            return [_evidence_from_row(row) for row in rows]

    def save_report(self, report: OpportunityReport) -> OpportunityReport:
        with Session(self.database.engine) as session:
            row = session.get(ReportRow, report.candidate_id)
            if row is None:
                row = ReportRow(candidate_id=report.candidate_id)
                session.add(row)
            row.component_scores_json = json.dumps(report.component_scores, sort_keys=True)
            row.total_score = report.total_score
            row.confidence = report.confidence
            row.verdict = report.verdict
            row.risks_json = json.dumps(report.risks)
            row.recommendation = report.recommendation
            row.adversarial_review = report.adversarial_review
            row.next_action = report.next_action
            row.evidence_ids_json = json.dumps(report.evidence_ids)
            row.created_at = report.created_at
            session.commit()
            return report

    def get_report(self, candidate_id: str) -> OpportunityReport | None:
        with Session(self.database.engine) as session:
            row = session.get(ReportRow, candidate_id)
            if row is None:
                return None
            return OpportunityReport(
                candidate_id=row.candidate_id,
                component_scores=json.loads(row.component_scores_json),
                total_score=row.total_score,
                confidence=row.confidence,
                verdict=row.verdict,
                risks=json.loads(row.risks_json),
                recommendation=row.recommendation,
                adversarial_review=row.adversarial_review,
                next_action=row.next_action,
                evidence_ids=json.loads(row.evidence_ids_json),
                created_at=row.created_at,
            )


def _candidate_from_row(row: CandidateRow) -> Candidate:
    return Candidate(
        id=row.id, canonical_identity=row.canonical_identity, source=row.source, url=row.url,
        category=row.category, title=row.title, metadata=json.loads(row.metadata_json),
        provenance_urls=json.loads(row.provenance_json), discovered_at=row.discovered_at,
        updated_at=row.updated_at, status=row.status, score=row.score,
    )


def _evidence_from_row(row: EvidenceRow) -> Evidence:
    return Evidence(
        id=row.id, candidate_id=row.candidate_id, claim=row.claim, evidence_type=row.evidence_type,
        source_url=row.source_url, summary=row.summary, collected_at=row.collected_at,
        supporting_evidence_ids=json.loads(row.supporting_evidence_ids_json),
    )
