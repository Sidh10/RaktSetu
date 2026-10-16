# CLAUDE.md: working rules for Claude Code in `raktsetu-app/`

Read this before touching any file. Then read `docs/TASKLIST.md` to find the current stage and stop point.

## What this is

A 3-day Round 2 prototype of RaktSetu: list stock → match → confirm → approve, a public finder and a stock-message
parser. The scientific evidence lives in the **read-only** simulator folder
`../RaktSetu_simulator_and_prototype/` (simulator v3, results, deck). This folder turns that evidence into running
software. It does not produce new outcome claims.

## Stack (subject to the pending decisions in `docs/DECISIONS.md`)

| Layer | Choice | ADR |
|---|---|---|
| Language | Python 3.11+ (dev machine has 3.13) | — |
| API | FastAPI + Pydantic v2 + Uvicorn | ADR-007 |
| DB | SQLAlchemy 2.x; SQLite file for the demo, Postgres optional | ADR-001 |
| Core logic | `backend/app/core/`: pure Python, no I/O, no DB, no numpy at runtime | ADR-006 |
| Frontend | React + Vite (JavaScript), built and served by FastAPI for the demo | ADR-005 |
| Parser | Rule-based always on; Claude API extraction when a key is set | ADR-003 |
| Channel | Mock WhatsApp/SMS: paste-in box + local webhook; CSV upload | ADR-002 |
| Auth | Seeded demo users with roles, sent as a header; **not real auth** | ADR-004 |
| Tests | pytest, httpx TestClient; golden parity fixtures from the simulator | `docs/TESTING.md` |

## Commands (from `raktsetu-app/`)

```bash
make setup         # venv + backend deps (+ frontend deps once Stage 3 starts)
make test          # all backend tests
make test-parity   # golden parity tests only
make golden        # regenerate golden fixtures from the simulator (needs numpy; rarely)
make seed          # fresh SQLite demo DB
make api           # uvicorn on :8000
make web           # vite dev server on :5173
make parser-eval   # parser accuracy on the frozen test split
```

Windows: shells are PowerShell or Git Bash. Use `python`, never `python3`. The venv interpreter is
`.venv/Scripts/python.exe` on Windows and `.venv/bin/python` elsewhere; the Makefile picks the right one.
If `make` is missing, copy the command from the Makefile target.

## Hard rules

1. **No fabricated numbers, sources or citations.** Quote values only from files in
   `../RaktSetu_simulator_and_prototype/` and cite the path. Anything else is marked **ASSUMPTION** or **UNVERIFIED**.
2. **Never modify anything outside `raktsetu-app/`.** The simulator folder is read-only.
3. **No real patient, donor or centre data.** Seed data is fictional and labelled simulated.
4. **Secrets only via environment variables.** Never commit `.env` or a key. Never log a key.
5. **Deck constraints are invariants:** a medical officer approves every transfer; no patient data is stored; unit
   IDs are opaque and not linkable to donors. Code that would weaken one of these needs an ADR and the user's approval.
6. **Do not import the simulator at runtime.** Only `scripts/gen_golden.py` and the parity tests may import
   `raktsetu_sim_v3.py`, and only from its read-only path.
7. **Stop at every checkpoint** in `docs/TASKLIST.md`. Report, then wait for "go".
8. Where the plan conflicts with the deck, log it under "Deviations from deck" in `docs/DECISIONS.md` and flag it.
9. Small, verifiable steps. Each task has acceptance criteria; meet them with a test before moving on.
10. Cut scope before cutting verification. Parity tests and the claims audit are never cut.

## Never claim (in code, UI text, docs, commit messages or the demo)

- "clinically validated", "safe for clinical use", "approved by" any authority or specialist
- "real-time WhatsApp integration", "live WhatsApp", "SMS gateway" (it is a **mock channel**)
- any percentage or probability shown to the public finder user (bands only: High / Medium / Low)
- "reduces wastage by X%" or any outcome number as if measured; simulator numbers are **simulated** and cite the file
- "OR-Tools", "optimal matching" (the matcher is greedy: `sim_v3/MODEL_SPEC_v3.md` §4)
- "exponential decay", "half-life" for trust (there is none: `sim_v3/MODEL_SPEC_v3.md` §5)
- "parser accuracy X%" on real messages (only the synthetic test set exists)
- "secure", "authenticated", "production-ready", "deployed"
- "0 wasted trips" without "by design" (`sim_v3/RESULTS_v3.md` §2)
- that G1 or G2 passed (both FAILED: `sim_v3/RESULTS_v3.md` §1)

Required labels wherever they apply: **simulated data**, **mock channel**, **not clinically validated**.
Full list: `docs/CLAIMS_AND_LIMITS.md`.

## Conventions

- `backend/app/core/` is pure and deterministic: plain functions and dataclasses, no clock reads (pass `now` in),
  no randomness, no DB. Everything in it has unit tests; anything ported from the simulator has a parity test.
- Function names in `core/` keep the simulator's names where they port one-to-one (`pref_list`, `surplus_near`,
  `apportion`) so a reviewer can diff them side by side. The docstring cites the simulator line it ports.
- Blood groups are strings `"O+" … "AB-"` at the API; inside `core/` the simulator's index `g = 2*abo + rhneg`
  (order `O+, O-, A+, A-, B+, B-, AB+, AB-`) is used, with converters.
- Times are timezone-aware, stored in UTC, shown in Asia/Kolkata.
- State changes to a transfer go through one service function that checks the role, the allowed transition and
  writes an audit row. Routes never set `status` directly.
- Every UI screen that shows simulated data carries the banner "Simulated data · mock channel · not clinically
  validated".
- Keep comments sparse; cite sources in docstrings, not inline essays.

## Golden parity tests (how to run, what they mean)

- Fixtures in `backend/tests/golden/*.json` are produced by `scripts/gen_golden.py`, which imports
  `../RaktSetu_simulator_and_prototype/sim_v3/raktsetu_sim_v3.py` read-only and records inputs and outputs of the
  functions we port, plus whole-run metrics on **dev seeds 9000–9004 only** (dev seeds are never reported as results:
  `sim_v3/PREREGISTRATION_v3.md` §1).
- `make test-parity` checks that `backend/app/core/` reproduces every fixture **exactly**. Any mismatch is a bug in the
  port, never a reason to edit the fixture. Regenerate fixtures only if the simulator file's SHA-256 (recorded in each
  fixture) changes, and say so at the next checkpoint.
- Details and the list of parity cases: `docs/TESTING.md` §2.

## Model use

Planning and checkpoints: Opus. Mechanical implementation inside an approved stage: Sonnet is fine. The parser's
runtime LLM is configured by `RAKTSETU_LLM_MODEL` (see `.env.example`, ADR-003); never hard-code a key.
