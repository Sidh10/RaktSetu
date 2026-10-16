# Task list

Time box: about **3 working days**: Day 1 = Thu 15 Oct (afternoon onward), Day 2 = Fri 16 Oct, Day 3 = Sat 17 Oct.
Sun 18 Oct is buffer / presentation. These dates come from the deck's "Round 2 (15–18 Oct)" (slide 6) and are
**UNVERIFIED** (`DECISIONS.md` Q1). Estimates are working hours, including tests. Owner: **H** = human (team Trex),
**CC** = Claude Code. Every stage ends at a **checkpoint**: Claude Code stops, reports, and waits for "go".

Rule: when time runs short, cut scope (§3), never verification.

## Stage 0: Planning and skeleton (done at Checkpoint A)

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 0.1 | Read simulator, results, dashboard, deck | CC | 1 h | — |
| 0.2 | Write the 13 docs, config files, empty skeleton | CC | 2 h | files exist; every number cites a file or is marked ASSUMPTION / UNVERIFIED |

### ✋ Checkpoint A: decisions
Human: approve or change ADR-001…012; answer Q1, Q2, Q6, Q8; decide git repo. **Go/no-go:** Stage 1 starts only after
ADR-006 (and ideally all ADRs) are approved.

## Stage 1: Core library + golden parity (Day 1 afternoon, ~4.5 h) — **done 15 Oct, except 1.1 and 1.6 (human)**

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 1.1 | `git init`, private remote (if approved) | H | 0.2 h | repo exists — **open** (Q6) |
| 1.2 | `backend/pyproject.toml` (FastAPI, SQLAlchemy, pydantic, anthropic; dev: pytest, httpx, numpy) and `make setup` | CC | 0.3 h | `make setup` works on Windows ✅ |
| 1.3 | `scripts/gen_golden.py` + fixtures for P-01…P-07, P-09, P-10 | CC | 1 h | fixtures committed, each records the simulator SHA-256 ✅ |
| 1.4 | Port into `core/`: groups & `pref_list`, `apportion`, `surplus_near`/`own_offerable`, view ageing, greedy ordering, margin, trust, finder ranking & bands | CC | 1.5 h | P-01…P-07, P-09, P-10 pass; core unit tests pass ✅ |
| 1.5 | P-08 whole-run replay harness on dev seeds 9000–9004 | CC | 1.2 h | metric dicts identical for every case ✅ |
| 1.6 | Review the port side by side with the simulator (spot-check 3 functions) | H | 0.3 h | sign-off — **open** |

### ✋ Checkpoint B: parity
Report: test counts, any deviation found. **Go/no-go:** all parity green (or P-08 explicitly deferred by the human)
before Stage 2.

## Stage 2: Backend, DB, seed, workflow (Day 1 evening → Day 2 morning, ~6 h) — **done 16 Oct, except 2.8 (human)**

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 2.1 | SQLAlchemy models (`DATA_MODEL.md` §2), SQLite engine, `create_all` | CC | 0.8 h | tables created; privacy test passes ✅ |
| 2.2 | Demo users, `X-Demo-User` dependency, role matrix (`API.md` §2) | CC | 0.5 h | role tests pass ✅ |
| 2.3 | Stock posts, shortfalls, board endpoint | CC | 1 h | FR-L1, L2, L4, L6, L7 tests pass ✅ |
| 2.4 | Match run service using `core/` + reasons | CC | 1 h | FR-M1…M6 tests pass ✅ |
| 2.5 | Transfer state machine + trust updates + audit | CC | 1.5 h | `test_state_machine_table`, FR-T1…T8 pass ✅ |
| 2.6 | Finder endpoint (bands only) | CC | 0.4 h | FR-F1, F2, F5 pass ✅ |
| 2.7 | Seed city (`data/seed/`) + `make seed` + seed contract test | CC | 0.8 h | `test_demo_seed_contract` passes ✅ |
| 2.8 | Review seed: fictional names, phones, plausible stock | H | 0.2 h | sign-off — **open** |

### ✋ Checkpoint C: API end to end
Demonstrate the full flow through `/docs` or a script: list → match → confirm (partial) → approve → dispatch →
deliver, plus one forbidden action (staff approving → 403). **Go/no-go:** all API tests green.

## Stage 3: Frontend (Day 2, ~6 h) — **done 16 Oct, except 3.6 (human)**

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 3.1 | Vite + React scaffold, API client, role switcher, banner, CSS from the v3 mock-up | CC | 1 h | app loads; banner on every page ✅ |
| 3.2 | Coordinator board: KPI tiles, centre table (listed, ≤ 2 days, last update, trust band), run-matcher button | CC | 1.5 h | matches `DEMO_SCRIPT.md` steps 1–2 ✅ |
| 3.3 | Transfer cards with role-aware actions (request confirmation, confirm with count, approve/reject, dispatch, deliver), margin and policy chips, "why" text | CC | 2 h | steps 3–6 clickable ✅ |
| 3.4 | Public finder page (no login), bands only, call-first advice, band note | CC | 0.7 h | step 8; no % visible ✅ |
| 3.5 | Build + serve from FastAPI (`make build-web`) | CC | 0.3 h | one process serves UI + API ✅ |
| 3.6 | Click through as each role; note confusing copy | H | 0.5 h | list of fixes — **open** (Claude Code did one pass; see Checkpoint D) |

### ✋ Checkpoint D: UI flow
**Go/no-go:** the demo script steps 1–6 and 8 run in the browser. If not by end of Day 2 → ADR-005 fallback.

## Stage 4: Parser + mock channel + evaluation (Day 2 evening → Day 3 morning, ~6.5 h incl. 2 h human, parallel) — **built 16 Oct; evaluation waits for 4.1**

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 4.1 | Write ≥ 60 synthetic messages by hand (English + Hinglish) with gold labels; second person checks labels | **H** | 2 h (parallel with 4.2–4.4) | JSONL in `backend/tests/parser/data/` — **open** (in progress by the team) |
| 4.2 | Template generator for the remaining ~90 messages; split 50 dev / 100 test; freeze test hash | CC | 0.5 h | `test_set.sha256` committed — generator ✅; freeze waits for 4.1 |
| 4.3 | Rule-based parser + post-checks + flags | CC | 1.5 h | parser unit tests pass on `PARSER_SPEC.md` §3 formats ✅ |
| 4.4 | Mock channel endpoint, paste box, parser inbox with human check and commit | CC | 1.2 h | FR-P1, P4 pass; step 7 clickable ✅ |
| 4.5 | LLM path (Claude API structured output, fallback) | CC | 0.8 h | `test_llm_failure_falls_back` passes; works with key ✅ |
| 4.6 | Freeze targets (`PARSER_SPEC.md` §6.3), then run `make parser-eval` on the test split, rules and LLM | CC + H | 0.5 h | results JSON + summary; numbers quoted only from it — targets **frozen** 16 Oct ✅; scoring waits for 4.1 |

### ✋ Checkpoint E: parser evidence
Report accuracy with CIs, critical errors, human-check rate. **Go/no-go:** critical errors examined; demo copy updated.

## Stage 5: Demo hardening and deliverables (Day 3, ~4 h) — **Claude Code parts done 16 Oct; human parts open**

| # | Task | Owner | Est. | Acceptance |
|---|---|---|---|---|
| 5.1 | Claims audit test + manual read of every screen | CC + H | 0.5 h | test green; no forbidden phrase — claims-audit test ✅ (52 checks); manual read of every screen: **open** (human) |
| 5.2 | README: run instructions, status table updated to "built / mock / planned" truthfully | CC | 0.4 h | a teammate runs it from scratch on Windows — written and verified from a clean copy on 16 Oct ✅; teammate run: **open** |
| 5.3 | Rehearse `DEMO_SCRIPT.md` twice, timed | H | 0.7 h | ≤ 5 min |
| 5.4 | Record the backup video (screen + voice), and step screenshots | H | 0.8 h | file on desktop + USB |
| 5.5 | Report / slide inserts: what is built, parity result, parser result, limits | CC + H | 1 h | every number cites a file — `docs/REPORT_INSERTS.md` ✅; parser numbers to fill after the frozen test run |
| 5.6 | Pre-demo checklist on the demo machine (`TESTING.md` §6) | H | 0.4 h | all items ticked |

### ✋ Checkpoint F: feature freeze (end of Day 3)
No new features after this point; only fixes to failing tests or wrong copy.

## Stretch (only after Checkpoint F's scope is green)

| Task | Pri | Est. |
|---|---|---|
| CSV upload (FR-L5) | P1 | 0.7 h |
| Audit view (FR-X3) | P1 | 0.5 h |
| Postgres run of the API suite via docker-compose | P2 | 0.7 h |
| GitHub Actions running `make test` | P2 | 0.4 h |
| Par-gap hint on the board | P2 | 0.5 h |
| Playwright smoke test of the demo path | P2 | 1 h |

## 3. Cut order (first to go)

1. Stretch items above.
2. LLM parser path and its eval (keep rules + its eval).
3. Standard / relaxed policies in the UI (keep strict; API keeps them).
4. CSV upload; audit view UI (audit rows still written).
5. Dispatch / deliver screens (stop the visual demo at "approved"; API still tested end to end).

Never cut: parity tests, state-machine and role tests, finder "bands only" test, the banner and labels, the claims
audit, the pre-demo checklist.

## 4. Total

Stages 1–5 ≈ 27 h of work (4.5 + 6.2 + 6.0 + 6.5 + 3.8), of which ~5 h are human-only tasks (1.1, 1.6, 2.8, 3.6,
4.1, 5.3, 5.4, 5.6) that partly run in parallel with Claude Code. That fills three long days with little slack; the cut
order above is the plan for slippage, not an afterthought.
