"""Shared by scripts/gen_golden.py and the parity tests: load the READ-ONLY simulator by file path,
hash it, and digest run records canonically. Never imported by the app."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SIM_DIR = APP_ROOT.parent / "RaktSetu_simulator_and_prototype" / "sim_v3"
GOLDEN_DIR = APP_ROOT / "backend" / "tests" / "golden"
SIM_FILE = "raktsetu_sim_v3.py"
BANDS_FILE = "bands_v3.py"


def sim_dir() -> Path:
    return Path(os.environ.get("RAKTSETU_SIM_DIR", DEFAULT_SIM_DIR))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    """Import one file as a module without putting its folder on sys.path or writing __pycache__ into it
    (the simulator folder is read-only)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    prev, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = prev
    return mod


def load_sim(directory: Path | None = None):
    d = directory or sim_dir()
    return load_module(d / SIM_FILE, "raktsetu_sim_v3_readonly")


def load_bands(directory: Path | None = None):
    d = directory or sim_dir()
    return load_module(d / BANDS_FILE, "bands_v3_readonly")


def _default(o):
    if hasattr(o, "item"):          # numpy scalar
        return o.item()
    if hasattr(o, "tolist"):        # numpy array
        return o.tolist()
    raise TypeError(type(o))


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def run_digests(record, callog, visitlog) -> dict:
    return dict(record=digest(record), per_day=[digest(r)[:16] for r in record],
                callog=digest(callog), visitlog=digest(visitlog),
                n_calls=len(callog), n_visits=len(visitlog))


def load_fixture(name: str) -> dict:
    path = GOLDEN_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing golden fixture {path}; run `make golden`")
    return json.loads(path.read_text(encoding="utf-8"))
