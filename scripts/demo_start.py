"""Demo day, one command: pre-demo checks, fresh demo city, API + UI on :8000, browser opened.

    .venv\\Scripts\\python.exe scripts\\demo_start.py            # checks, re-seed, start server, open browser
    .venv\\Scripts\\python.exe scripts\\demo_start.py --check    # checks only (adds the full test run)
    make demo / make demo-check                                # same, with GNU make

Checks (docs/TESTING.md section 6): memory, port 8000, built UI is current, simulator folder for parity, no .env in
git, optional test run. A FAIL stops the start; WARN lets you continue. Simulated data, mock channel, not clinically
validated.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = Path(sys.executable)
PORT = 8000
URL = f"http://localhost:{PORT}"
MIN_COMMIT_MB = 1024        # below this, Python crashed with MemoryError on the dev laptop (16 Oct)
WARN_COMMIT_MB = 2048

results: list[tuple[str, str, str]] = []


def report(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    print(f"  [{status:4}] {name}{': ' + detail if detail else ''}", flush=True)


def commit_free_mb() -> int | None:
    """Windows commit memory available (RAM + page file), the limit Python hit on 16 Oct."""
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    s = MEMORYSTATUSEX()
    s.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
        return None
    return int(s.ullAvailPageFile / 2**20)


def health() -> dict | None:
    try:
        with urllib.request.urlopen(f"{URL}/api/health", timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return None


def port_in_use() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def newest_mtime(folder: Path) -> float:
    return max((p.stat().st_mtime for p in folder.rglob("*") if p.is_file()), default=0.0)


def run_checks(with_tests: bool) -> None:
    print("Pre-demo checks")
    v = sys.version_info
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    report("OK" if v >= (3, 11) and in_venv else "FAIL", "Python",
           f"{v.major}.{v.minor}.{v.micro}" + ("" if in_venv else " (NOT the project venv: use .venv\\Scripts\\python.exe)"))

    mb = commit_free_mb()
    if mb is None:
        report("OK", "Memory", "not Windows; not checked")
    else:
        st = "FAIL" if mb < MIN_COMMIT_MB else "WARN" if mb < WARN_COMMIT_MB else "OK"
        report(st, "Free commit memory", f"{mb:,} MB" + ("" if st == "OK" else
               " - close other apps (browsers, IDEs, chat apps, MySQL) or enable the Windows page file"))

    h = health()
    if h:
        report("OK", "Port 8000", "the RaktSetu API is already running there (will be re-used)")
    elif port_in_use():
        report("FAIL", "Port 8000", "something else is using it; stop it first")
    else:
        report("OK", "Port 8000", "free")

    dist = ROOT / "frontend" / "dist" / "index.html"
    if not dist.exists():
        report("FAIL", "Built UI", "frontend/dist missing: run `npm --prefix frontend run build`")
    elif newest_mtime(ROOT / "frontend" / "src") > dist.stat().st_mtime:
        report("WARN", "Built UI", "frontend/src changed after the last build: run `npm --prefix frontend run build`")
    else:
        report("OK", "Built UI", "frontend/dist is current")

    sim = Path(os.environ.get("RAKTSETU_SIM_DIR", ROOT.parent / "RaktSetu_simulator_and_prototype" / "sim_v3"))
    report("OK" if (sim / "raktsetu_sim_v3.py").exists() else "WARN", "Simulator folder (whole-run parity)",
           str(sim) if (sim / "raktsetu_sim_v3.py").exists() else f"not found at {sim}: 17 parity tests will skip")

    tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    report("FAIL" if tracked else "OK", ".env not in git", "TRACKED - remove it from git" if tracked else "")
    if (ROOT / ".env").exists():
        report("OK", "LLM key", "a .env exists; parsing uses the Claude API if it holds a key (rules otherwise)")
    else:
        report("OK", "LLM key", "none: the parser runs offline with rules (expected for the demo)")

    if with_tests:
        for folder in ("backend/tests/core", "backend/tests/parity", "backend/tests/api",
                       "backend/tests/test_claims_audit.py"):
            r = subprocess.run([str(PY), "-m", "pytest", folder, "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                               capture_output=True, text=True)
            last = (r.stdout.strip().splitlines() or ["no output (crashed? check memory)"])[-1]
            report("OK" if r.returncode == 0 and "skipped" not in last else "WARN" if r.returncode == 0 else "FAIL",
                   f"Tests {folder}", last)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks only, including the full test run")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    run_checks(with_tests=a.check)
    fails = [r for r in results if r[0] == "FAIL"]
    warns = [r for r in results if r[0] == "WARN"]
    print(f"\n{len(fails)} FAIL, {len(warns)} WARN")
    if a.check:
        return 1 if fails else 0
    if fails:
        print("Fix the FAIL items above, then run this again.")
        return 1

    print("\nRe-seeding the demo city (demo clock 09:00 IST, simulated data)")
    r = subprocess.run([str(PY), "scripts/seed_demo.py", "--reset"], cwd=ROOT, capture_output=True, text=True)
    print("  " + (r.stdout.strip() or r.stderr.strip()).replace("\n", "\n  "))
    if r.returncode != 0:
        return 1

    server = None
    if not health():
        print(f"\nStarting the API + UI on {URL}  (Ctrl+C to stop)")
        server = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:create_app", "--factory",
                                   "--app-dir", "backend", "--port", str(PORT)], cwd=ROOT)
        for _ in range(40):
            if health():
                break
            time.sleep(0.5)
        else:
            print("The server did not start; see the messages above.")
            server.terminate()
            return 1
    h = health()
    print(f"  ready: demo clock {h['now']}, parser {h['parser_mode']} (LLM {'on' if h['llm_available'] else 'off'})")
    if not a.no_browser:
        webbrowser.open(f"{URL}/#/board")
    print(f"\nOpen {URL}/#/board as Coordinator. Re-run this script between rehearsals to reset the city.")
    if server:
        try:
            server.wait()
        except KeyboardInterrupt:
            server.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
