from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from pathlib import Path
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str = "sqlite:///data/digital_archaeologist.db") -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        if url.startswith("sqlite") and ":memory:" not in url:
            database_path = make_url(url).database
            if database_path:
                Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(url, future=True, connect_args=connect_args)
        self._initialise()

    def _initialise(self) -> None:
        from .repositories import CandidateRow, EvidenceRow, ReportRow  # noqa: F401
        Base.metadata.create_all(self.engine)
        # Additive migration for SQLite databases created by the earlier v0.1 schema.
        migrations = {
            "evidence": {"supporting_evidence_ids_json": "TEXT NOT NULL DEFAULT '[]'"},
            "opportunity_reports": {
                "adversarial_review": "TEXT NOT NULL DEFAULT ''",
                "next_action": "TEXT NOT NULL DEFAULT 'Human review required before any action'",
            },
        }
        with self.engine.begin() as connection:
            for table, columns in migrations.items():
                present = {column["name"] for column in inspect(connection).get_columns(table)}
                for name, definition in columns.items():
                    if name not in present:
                        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
