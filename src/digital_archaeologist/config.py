from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, repr=False)
class Settings:
    database_url: str = field(default="sqlite:///data/digital_archaeologist.db")
    dry_run: bool = field(default=True)
    allow_side_effects: bool = field(default=False)
    github_token: str | None = field(default=None, repr=False)
    ai_api_key: str | None = field(default=None, repr=False)
    ai_provider: str = "none"
    ai_model: str = "gpt-4o-mini"
    request_timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000

    def __init__(self) -> None:
        object.__setattr__(self, "database_url", os.getenv("DA_DATABASE_URL", "sqlite:///data/digital_archaeologist.db"))
        object.__setattr__(self, "dry_run", _env_bool("DA_DRY_RUN", True))
        object.__setattr__(self, "allow_side_effects", _env_bool("DA_ALLOW_SIDE_EFFECTS", False))
        object.__setattr__(self, "github_token", os.getenv("DA_GITHUB_TOKEN"))
        object.__setattr__(self, "ai_api_key", os.getenv("DA_AI_API_KEY"))
        object.__setattr__(self, "ai_provider", os.getenv("DA_AI_PROVIDER", "none"))
        object.__setattr__(self, "ai_model", os.getenv("DA_AI_MODEL", "gpt-4o-mini"))
        object.__setattr__(self, "request_timeout_seconds", float(os.getenv("DA_REQUEST_TIMEOUT_SECONDS", "15")))
        object.__setattr__(self, "max_response_bytes", int(os.getenv("DA_MAX_RESPONSE_BYTES", "2000000")))
        object.__setattr__(self, "github_queries", _env_list("DA_GITHUB_QUERIES", ["abandoned tool", "deprecated project", "unmaintained saas"]))
        object.__setattr__(self, "web_seed_urls", _env_list("DA_WEB_SEEDS", []))

    def __repr__(self) -> str:
        return (
            "Settings("
            f"database_url={self.database_url!r}, "
            f"dry_run={self.dry_run!r}, "
            f"allow_side_effects={self.allow_side_effects!r}, "
            f"ai_provider={self.ai_provider!r}, "
            f"ai_model={self.ai_model!r}, "
            f"request_timeout_seconds={self.request_timeout_seconds!r}, "
            f"max_response_bytes={self.max_response_bytes!r})"
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]
