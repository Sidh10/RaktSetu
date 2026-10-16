"""Rebuild the demo database from data/seed/demo_city.json (SIMULATED DATA).

    python scripts/seed_demo.py --reset [--anchor 2026-10-16T09:00:00+05:30]

The demo clock is anchored at --anchor (default: today 09:00 local) and then runs in real time.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings, load_env_file  # noqa: E402
from app.db import init_db, make_engine, make_sessionmaker  # noqa: E402
from app.services import seed  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete the SQLite file first")
    ap.add_argument("--anchor", type=datetime.fromisoformat, default=None)
    a = ap.parse_args()
    load_env_file(ROOT / ".env")   # optional; shell variables win
    s = Settings()
    url = s.database_url
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        path = Path(url.removeprefix("sqlite:///"))
        if not path.is_absolute():
            path = ROOT / path
            url = f"sqlite:///{path.as_posix()}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if a.reset and path.exists():
            path.unlink()
    engine = make_engine(url)
    init_db(engine)
    with make_sessionmaker(engine)() as session:
        anchor = seed.load(session, datetime.now(timezone.utc), s.tz, a.anchor)
        session.commit()
    print(f"seeded {url}; demo clock anchored at {anchor.isoformat()} (simulated data)")


if __name__ == "__main__":
    main()
