# RaktSetu prototype commands. Needs GNU make: on Windows install it via MSYS2 (Git Bash alone has no make).
# Each recipe is a single python / npm command, so it can be copied into PowerShell if make is missing.
# Targets marked (Stage N) do nothing useful until that stage lands.

ifeq ($(OS),Windows_NT)
  PY_SYS ?= python
  VENV_PY := .venv/Scripts/python.exe
else
  PY_SYS ?= python3
  VENV_PY := .venv/bin/python
endif

SIM_DIR := ../RaktSetu_simulator_and_prototype/sim_v3

.PHONY: help setup setup-web test test-parity golden seed api web build-web dev parser-eval clean demo demo-check

help:
	@echo "setup        create .venv and install backend deps (Stage 1)"
	@echo "setup-web    npm install in frontend/ (Stage 3)"
	@echo "test         run all backend tests"
	@echo "test-parity  golden parity tests; FAILS if the simulator folder is missing"
	@echo "golden       regenerate golden fixtures from the read-only simulator (Stage 1; needs numpy)"
	@echo "seed         rebuild the SQLite demo DB from data/seed (Stage 2)"
	@echo "api          run the API on :8000 (Stage 2)"
	@echo "web          run the Vite dev server on :5173 (Stage 3)"
	@echo "build-web    build the UI into frontend/dist for FastAPI to serve (Stage 3)"
	@echo "dev          print the two commands to run API and UI side by side"
	@echo "parser-eval  parser accuracy on the frozen test split (Stage 4)"
	@echo "demo         demo day: checks, fresh seed, API + UI on :8000, opens the browser"
	@echo "demo-check   pre-demo checks only (memory, port, UI build, tests)"
	@echo "clean        remove caches and the demo DB"

setup:
	$(PY_SYS) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -e "./backend[dev]"

setup-web:
	npm --prefix frontend install

test:
	$(VENV_PY) -m pytest backend/tests -q

test-parity:
	RAKTSETU_REQUIRE_SIM=1 $(VENV_PY) -m pytest backend/tests/parity -q

golden:
	$(VENV_PY) scripts/gen_golden.py --sim-dir $(SIM_DIR) --out backend/tests/golden

seed:
	$(VENV_PY) scripts/seed_demo.py --reset

api:
	$(VENV_PY) -m uvicorn app.main:create_app --factory --app-dir backend --reload --port 8000

web:
	npm --prefix frontend run dev

build-web:
	npm --prefix frontend run build

dev:
	@echo "Run these in two terminals:"
	@echo "  make api"
	@echo "  make web"

parser-eval:
	$(VENV_PY) scripts/parser_eval.py --split test

clean:
	$(PY_SYS) -c "import pathlib,shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]; [p.unlink() for p in pathlib.Path('data').glob('*.db')]"

demo:
	$(VENV_PY) scripts/demo_start.py

demo-check:
	$(VENV_PY) scripts/demo_start.py --check
