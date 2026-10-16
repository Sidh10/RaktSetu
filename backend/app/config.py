"""Settings from environment variables (.env.example lists them). No secrets are read here except by name."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from app.core import margin


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def load_env_file(path) -> int:
    """Load KEY=VALUE lines from a .env file into os.environ without overriding variables already set in the shell.
    Values are never logged or returned. Returns how many variables were set."""
    from pathlib import Path
    p = Path(path)
    if not p.is_file():
        return 0
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            n += 1
    return n


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./data/raktsetu_demo.db"))
    demo_mode: bool = field(default_factory=lambda: _env("RAKTSETU_DEMO_MODE", "true").lower() == "true")
    tz_name: str = field(default_factory=lambda: _env("RAKTSETU_TZ", "Asia/Kolkata"))
    default_policy: str = field(default_factory=lambda: _env("RAKTSETU_DEFAULT_POLICY", "strict"))
    margin_hours: float = field(default_factory=lambda: float(_env("RAKTSETU_MARGIN_HOURS",
                                                                     str(margin.MARGIN_HOURS))))
    default_transport_min: float = field(default_factory=lambda: float(_env("RAKTSETU_DEFAULT_TRANSPORT_MIN",
                                                                              str(margin.DEFAULT_TRANSPORT_MIN))))

    parser_mode: str = field(default_factory=lambda: _env("RAKTSETU_PARSER_MODE", "auto"))      # rules | llm | auto
    llm_model: str = field(default_factory=lambda: _env("RAKTSETU_LLM_MODEL", "claude-opus-5-5"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("RAKTSETU_LLM_TIMEOUT_S", "15")))

    @property
    def llm_key_present(self) -> bool:
        """Whether ANTHROPIC_API_KEY is set. The key itself is never read into settings, logged or returned."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)


LABELS = ["simulated data", "mock channel", "not clinically validated"]
