# RaktSetu prototype (`raktsetu-app/`)

**RaktSetu** is a trust-aware, confirm-first platelet transfer layer between blood centres. This folder holds the
**Round 2 working prototype** of the flow the deck promises: **list stock → match → confirm → approve**, plus a
public platelet finder and a stock-message parser.

Team Trex · VIT Code_Apex 3.0 · Open Innovation track.

> **Read this first.**
> - Every centre, unit, message and user here is **simulated data**. No real patient, donor or centre data.
> - The WhatsApp/SMS input is a **mock channel** (a paste-in box and a local webhook). No message leaves the machine.
> - The matching policy is **not clinically validated**. A transfusion-medicine specialist must review it before any
>   real use (`docs/MATCHING_POLICY.md`).
> - Demo login is a role switcher. It is **not real authentication**.

## Status (updated at every checkpoint)

Status at **Stage 5, 16 Oct 2026** (demo hardening; feature freeze at the end of Day 3): core library (parity-checked against the simulator), backend API, seeded demo city, full transfer workflow, browser UI, and the mock-channel message parser with human check. Not yet available: a reportable parser accuracy result (waiting for the hand-written test messages).

| Component | Status | Notes |
|---|---|---|
| Planning docs (`docs/`) | **built** | This checkpoint |
| Core library: trust, matcher, ABO/RhD tiers, 12-h margin, finder bands (`backend/app/core/`) | **built** | Ported from `sim_v3/raktsetu_sim_v3.py`; 23 golden parity tests incl. 17 whole-run replays pass; 82 unit tests (`docs/TESTING.md` §2) |
| Backend API + database + seed (`backend/app/`) | **built** | FastAPI + SQLAlchemy on SQLite; list → match → confirm → approve → dispatch → deliver, roles, 12-h margin re-checks, trust updates, one-hop, audit, bands-only finder; 24 API/workflow tests |
| Coordinator board, transfer cards, public finder (`frontend/`) | **built** | React + Vite, served by FastAPI; role switcher, banner, board, role-aware transfer cards, match panel, report-trust and audit views, staff page, bands-only public finder; walked through in the browser 16 Oct |
| Stock-message parser (rule-based + LLM) and mock channel | **built** (LLM path tested with a fake client only; no API key yet) | English and Hinglish; drafts need a human check; Inbox page |
| Parser accuracy evaluation | **tooling built; no result yet** | Waiting for at least 60 hand-written messages, then freeze split and targets |
| Not built: WhatsApp Cloud API, SMS gateway | **mock only** | Mock channel stands in; see `docs/DECISIONS.md` ADR-002 |
| Hindi / Marathi parsing, regulator view, e-RaktKosh prior | planned (after Round 2) | Listed as planned in the deck too |

Status words: **built** = runs and is tested; **mock** = a stand-in that is labelled as such in the UI;
**planned** = not built.

## How to run

Tested on Windows 11 with Python 3.13.11 and Node 24.11.0 (16 Oct 2026). Needs Python 3.11+, Node 18+, internet
for the first install, and about 1 GB of free memory: close heavy apps if Python reports `MemoryError`.

### First run, PowerShell (no `make` needed)

From the `raktsetu-app` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
npm --prefix frontend install
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts\seed_demo.py --reset
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir backend --port 8000
```

Open <http://localhost:8000>. Pick a role in **Acting as**; the public finder needs no role. API docs are at
<http://localhost:8000/docs>. Stop the server with Ctrl+C.

### Same steps with `make` (Git Bash / MSYS2)

```bash
make setup && make setup-web && make build-web   # once
make seed                                         # every time you want a fresh demo city
make api                                          # serves UI + API on :8000 (auto-reload)
```

### Before a demo

1. `make seed` (or the seed command above). It re-anchors the **demo clock** at 09:00 IST today (ADR-013), so the
   scripted suggestions in `docs/DEMO_SCRIPT.md` appear exactly. Re-seed shortly before presenting.
2. Optional LLM parsing: put `ANTHROPIC_API_KEY=...` in `.env` (copy `.env.example`; `.env` is git-ignored) or set it
   in the shell, then start the API. Without a key the rule-based parser is used; the demo works offline.
3. Run through `docs/TESTING.md` §6 (pre-demo checklist).

### Tests and scripts

```bash
make test                               # all backend tests (core, parity, API, parser, claims audit)
make test-parity                        # golden parity tests only
python scripts/demo_flow.py             # walk the demo flow through a running API, printing each step
python scripts/parser_eval.py --split preview   # parser pipeline check on generated messages (not reportable)
python scripts/parser_split.py          # parser test-set status; --freeze once the hand-written set is in
```

In PowerShell, use `.\.venv\Scripts\python.exe` instead of `python`, and
`.\.venv\Scripts\python.exe -m pytest backend/tests -q` instead of `make test`.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `MemoryError` / `Unable to allocate` in Python | Windows is short of commit memory; close other apps (on the dev laptop the page file looked disabled). Tests can also be run per folder: `backend/tests/core`, `parity`, `api`. |
| Port 8000 already in use | Stop the other server, or add `--port 8010` and open that port. |
| UI says "API not reachable" or shows an old screen | The API is not running, or the UI was rebuilt: restart the API and reload the page. |
| `No time zone found with key Asia/Kolkata` | Reinstall the backend dependencies (they include `tzdata`, which Windows needs). |
| `npm` not found | Install Node.js 18+ and open a new terminal. |
| Demo suggestions differ from the script | The demo clock moved on (units expired); re-run the seed. |

## Repo map

```
raktsetu-app/
├── README.md              this file
├── CLAUDE.md              working rules for Claude Code sessions
├── Makefile               cross-platform commands
├── .env.example           settings (no secrets)
├── docs/
│   ├── SPEC.md            requirements with IDs, roles, acceptance tests, non-goals
│   ├── ARCHITECTURE.md    components, data flow, sequence diagrams, real vs simulated
│   ├── DATA_MODEL.md      tables, transfer state machine, seed plan
│   ├── API.md             endpoints, schemas, errors, role permissions
│   ├── MATCHING_POLICY.md ABO/RhD tiers, near-expiry, one-hop, 12-h margin, sources
│   ├── PARSER_SPEC.md     message schema, LLM + rule-based parser, accuracy plan
│   ├── TESTING.md         golden parity tests, API tests, pre-demo checklist
│   ├── DECISIONS.md       ADR log, open questions, deviations from the deck
│   ├── TASKLIST.md        stages, checkpoints, estimates, owners
│   ├── DEMO_SCRIPT.md     5-minute demo and the hardest jury questions
│   ├── CLAIMS_AND_LIMITS.md what the demo may and may not claim
│   ├── RISKS.md           top risks, mitigations, fallbacks
│   └── REPORT_INSERTS.md  paste-ready text for the Round 2 report and slides
├── backend/
│   ├── app/api/           HTTP routes (Stage 2)
│   ├── app/core/          pure trust/matcher library, no I/O (Stage 1)
│   ├── app/models/        SQLAlchemy models (Stage 2)
│   ├── app/services/      transfer workflow, parser, channel (Stage 2/4)
│   └── tests/             unit, parity, API, parser and claims-audit tests; parser test data
├── frontend/              React + Vite UI (src/; built into dist/)
├── data/seed/             fictional demo city, labelled simulated (Stage 2)
└── scripts/               seed, demo flow, golden fixtures, parser messages / split / eval
```

## Where the numbers come from

The prototype does not produce outcome numbers. Any number quoted in the UI or the docs comes from the v3 simulator
and cites its file, for example `RaktSetu_simulator_and_prototype/sim_v3/RESULTS_v3.md` or
`sim_v3/results/finder_bands.json`. Those are **simulated** results with **assumed** data-error rates
(`sim_v3/RESULTS_v3.md`, header). See `docs/CLAIMS_AND_LIMITS.md`.

## Disclaimers

- **Simulated data.** The demo city, its stock and its trust history are fictional.
- **Mock channel.** No WhatsApp Business account, no SMS gateway.
- **Not clinically validated.** The ABO/RhD policy follows the sources in `docs/MATCHING_POLICY.md` but has had no
  specialist review. The 12-hour margin is a team choice, not a regulation
  (`sim_v3/PREREGISTRATION_v3.md`, Amendment 2).
- **Not real authentication.** Seeded demo users with roles.
- **No patient data is stored.** Unit IDs are opaque and not linkable to donors.
- A medical officer approves every transfer in the workflow; the software never dispatches on its own.
