from __future__ import annotations

from typing import Protocol

from digital_archaeologist.domain.models import CandidateDraft


class CollectorError(RuntimeError):
    """A recoverable external-source collection failure."""


class Collector(Protocol):
    def collect(self) -> list[CandidateDraft]: ...
