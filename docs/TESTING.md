# Testing

Status: **planned** (Checkpoint A). Framework: pytest; API tests with FastAPI's `TestClient`; no network in any
automated test (the LLM client is mocked). Verification is never cut to save time (`CLAUDE.md`, hard rule 10).

## 1. Test layers

| Layer | Folder | Runs in `make test` | Purpose |
|---|---|---|---|
| Core unit tests | `backend/tests/core/` | yes | properties of pure functions (edge cases, invariants) |
| **Golden parity** | `backend/tests/parity/` + fixtures in `backend/tests/golden/` | yes (`make test-parity` alone) | production `core/` reproduces the simulator's decisions exactly |
| Service / state-machine tests | `backend/tests/services/` | yes | transitions, guards, trust updates, one-hop, audit |
| API tests | `backend/tests/api/` | yes | routes, roles, error codes, privacy, finder output |
| Seed contract | `backend/tests/test_demo_seed_contract.py` | yes | the demo script's expected suggestions still hold |
| Parser unit tests | `backend/tests/parser/` | yes (rules path; LLM mocked) | formats in `PARSER_SPEC.md` §3, flags, fallback |
| Parser accuracy eval | `scripts/parser_eval.py` | no (`make parser-eval`) | accuracy on the frozen synthetic test split |
| Claims audit | `backend/tests/test_claims_audit.py` | yes | forbidden phrases absent from UI strings and docs |
| UI smoke | manual checklist (§6) | no | Playwright is P2 |

## 2. Golden parity tests

**Goal.** Show that the trust and matcher code in the prototype makes the same decisions as the simulator whose results
the deck reports (`sim_v3/raktsetu_sim_v3.py`). This answers "is the demo running the same model as your results?".

**How fixtures are made.** `make golden` runs `scripts/gen_golden.py`, which loads `raktsetu_sim_v3.py` and
`bands_v3.py` **read-only** by file path (no `sys.path` change, no `__pycache__` written; never at app runtime,
ADR-006). It draws property-style inputs from `random.Random(20261015)`, calls the simulator, and writes
`backend/tests/golden/<case>.json` as `{"meta": {sim_file_sha256, bands_file_sha256, numpy, python, generated_at},
"cases": [{"input": …, "expected": …}]}`. Fixtures are committed. If the simulator's SHA-256 changes, P-08 fails
loudly instead of re-baselining.

**Rule.** A parity failure is a bug in `core/`. Fixtures are never hand-edited.

**Status (Checkpoint B, 15 Oct 2026): all parity tests pass** (6 function-level tests over 2,342 fixture cases + 17
whole runs). The simulator has no standalone function for the greedy order, the 12-h margin or the trust update; they
are inline in `run()`. Those decisions are therefore checked **in context** by the whole-run replay P-08, plus unit
tests in `backend/tests/core/`.

| ID | What | Simulator source | How checked | Cases | Pass |
|---|---|---|---|---|---|
| P-01 | `pref_list(g, policy)`, 8 groups × strict/standard/relaxed | `pref_list` | fixture | 24 | identical lists, in order |
| P-02 | Group shares `DIST_WEST`, `DIST_NORTH` | `_dist` | fixture | 2 | **bit-identical** floats |
| P-03 | `apportion(total, w)`, incl. par for the 8 centres | `apportion` | fixture | 8 + 500 random | identical |
| P-04 | `surplus_near` and `own_offerable` on random unit lists (received flags, mixed groups, varied d̄·w_g) | `surplus_near`, `Centre.own_offerable` | fixture | 1,000 | identical |
| P-05 | Listed-view ageing minus units moved out; never-posted centres | `Centre.view` | fixture | 300 | identical |
| P-06 | Greedy order: needs largest-first; candidates by tier, then offered count descending, stable; skip self and empty offers | greedy block of `run()` | **P-08** + `test_plan_matches_greedy_with_always_successful_attempts` | 17 runs + 300 | identical |
| P-07 | 12-h margin. Simulator form `15 + 24(r−1) − (T_c+T_t)/60 ≥ 12` (P-08 via `blocked_12h`), and the prototype's timestamp form agrees with it at 09:00 | rule12 branch of `attempt()` | **P-08** + `test_p07_margin_forms_agree_at_decision_time` | 17 runs + 60 | identical |
| P-08 | **Whole-run replay.** `backend/tests/parity/sim_harness.py` copies the simulated world (random draws, production, posting with ghosts, demand, issuing) and delegates every ported decision to `app.core` | `run()` | fixture: per-day digests of the full `record` (stocks, listing ages, daily trust), call log, visit log, `rates()` | 17 runs (below) | **identical**; the first divergent day is reported on failure |
| P-09 | Beta(2,1) finder trust: α += found, β += requested − found; visit ±1; p = α/(α+β); bucket = min(2, days since post) | `attempt()`, family block | **P-08** (daily `ftrust` in the record) + unit tests | 17 runs | identical |
| P-10 | Band thresholds (from `bands_v3.BANDS`) and finder ranking (listed × p, ties by centre, top 3) | `bands_v3.py`; family block | fixture (bands) + **P-08** (ranking via visit log) | 508 + 17 runs | identical |

P-08 cases (all dev seeds, 180 days): arm E + trust finder, strict, 12-h margin, seeds 9000–9004 in S1 and in S2
(10); standard policy (9000, S1); relaxed policy with anti-D (9001, S1); raw finder (9002, S1); naive matcher arm C
(9003, S2); no-platform arm A (9004, S1); single-group mode, no margin (9000, S1); officer no-answer q = 0.3 with
180-min transport (9001, S1). Runtime: about 4 s for all 23 parity tests on the dev laptop (measured 15 Oct).

**Mutation check (run once at Checkpoint B, scratch script, not committed).** Deliberate bugs were injected into
`core/` and the replay re-run: trust β update halved, finder tie-break reversed, candidates by ascending offer, near-
expiry 2 → 3 days, and margin 12 h → 11 h were all caught. Margin 12 h → 13 h is caught by the 90-minute cases but not
by the 180-minute case, so no single case covers both directions; the suite as a whole does.

Notes:
- Dev seeds 9000–9019 are "never reported" (`sim_v3/PREREGISTRATION_v3.md` §1). P-08 uses them only to check
  equality; no number from them is quoted anywhere.
- Not covered by parity: arms B (oracle) and D (adaptive), the LP matcher and the mis-specified error generators
  (none is used by the prototype), and the deliberate deviations S-01 … S-06 in `DECISIONS.md`, which are tested as
  product behaviour in §3.
- P-08 needs numpy (dev dependency only) and the simulator folder (`RAKTSETU_SIM_DIR` overrides the default path).
  Without the simulator its 17 tests are skipped and the test summary prints a red "WHOLE-RUN PARITY NOT CHECKED"
  banner; with `RAKTSETU_REQUIRE_SIM=1` (set by `make test-parity`) they fail instead. Found by the fresh-clone
  check on 16 Oct: before this, a bare clone reported a green run while P-08 had silently not run.

## 3. Service and API tests (selected)

**Status (Checkpoint C, 16 Oct 2026):** implemented in `backend/tests/api/` (`test_workflow.py`, `test_roles_privacy_finder.py`, `test_demo_seed_contract.py`): 24 tests, all passing; total suite 129 (82 core, 23 parity, 24 API). Names differ slightly from the plan below; every row except CSV upload, the parser rows and the claims audit (Stages 4–5) is covered.

| Test | Checks | Spec |
|---|---|---|
| `test_state_machine_table` | every (from, to, role) in `DATA_MODEL.md` §3 allowed; every other pair → 409 | FR-T1 |
| `test_confirm_partial`, `test_confirm_zero_fails` | quantities, statuses, shortfall reopened | FR-T2, FR-T8 |
| `test_confirm_updates_trust` | α, β change by found / requested − found in the recorded bucket | FR-T3 |
| `test_only_mo_can_approve` | staff and coordinator get 403 `forbidden_role` | FR-T4 |
| `test_no_dispatch_without_approval` | no path reaches `dispatched` without an approval audit row | FR-T4 |
| `test_margin_rechecked_at_dispatch` | moving the clock forward makes dispatch return 409 `margin_failed` | FR-T5 |
| `test_every_transition_audited` | audit row count equals transitions | FR-T6 |
| `test_one_hop_received_units_never_offered` | delivered units never appear in offers | FR-L6 |
| `test_strict_never_crosses_groups` | 1,000 random cities: all strict suggestions tier 0 | FR-M2 |
| `test_relaxed_sets_anti_d_flag` | RhD+ → RhD− suggestions carry the flag | FR-M2 |
| `test_unit_schema_has_no_identifying_fields` | model columns ∩ {donor, patient, name, bag, phone, dob, age, sex, ward, bed} = ∅ (phone allowed only on `centre.public_phone`) | FR-L2 |
| `test_shortfall_has_no_patient_fields` | extra fields in body → 400 | FR-L4 |
| `test_finder_response_has_no_probability` | no float in [0, 1] and no `%` in any result object; band ∈ {High, Medium, Low} | FR-F2 |
| `test_finder_writes_nothing` | DB row counts unchanged after 50 finder calls | FR-F5 |
| `test_draft_does_not_change_stock` | inbound message → draft only; stock unchanged until commit | FR-P4 |
| `test_llm_failure_falls_back` | mocked client raises / times out / returns refusal → draft `parser="rules"` with a note | FR-P3 |
| `test_demo_seed_contract` | after `make seed` with fixed `--now`, the match run returns exactly the suggestions `DEMO_SCRIPT.md` expects | FR-X2 |
| `test_claims_audit` | §5 phrase list absent from `frontend/src`, API strings and `docs/` (except where quoted as forbidden) | NFR-5 |

## 4. Parser accuracy test

**Status (16 Oct):** parser unit and inbox tests pass (`backend/tests/core/test_parser_rules.py`, `backend/tests/api/test_inbox.py`, incl. the LLM path with a fake client). The accuracy evaluation itself waits for the hand-written messages; see PARSER_SPEC §8.

Plan in `PARSER_SPEC.md` §6: 150 synthetic labelled messages (≥ 60 hand-written by the team), 50 dev / 100 frozen
test, metrics item exact match, field accuracy, critical error rate, human-check rate, fallback rate, latency, cost,
with bootstrap CIs. `make parser-eval` writes `scripts/out/parser_eval_<timestamp>.json` (git-ignored) and a short
Markdown summary that is copied into the report by hand.

## 5. Claims audit phrases

**Status (16 Oct):** implemented in `backend/tests/test_claims_audit.py` (52 checks). It scans the UI source, backend code, seed data, README, DEMO_SCRIPT and REPORT_INSERTS. A phrase passes only when negated or asked as a question, and one test proves 10 planted overclaims are caught. The list below was the plan; the test's `FORBIDDEN` dictionary is the current source of truth.

Fail the build if any of these appear in UI strings or API messages (case-insensitive): "clinically validated" (unless
preceded by "not"), "probability", "chance of stock", a `%` next to a finder result, "real-time WhatsApp", "live
WhatsApp", "secure login", "optimal", "OR-Tools", "half-life", "decay", "production-ready", "deployed". The full list
lives in `CLAIMS_AND_LIMITS.md` §4.

## 6. Pre-demo checklist (run in order, on the demo machine, the day of the demo)

1. `git status` clean (or the folder copied); `.env` present **without** a committed key; `ANTHROPIC_API_KEY` set only
   if the LLM path is to be shown.
2. Close heavy apps first. On the dev laptop on 16 Oct, Windows had only ~0.75 GB of commit memory free (commit
   limit = RAM, so the page file looks disabled or small), and Python hit `MemoryError`. That interrupted a full
   test run, and on stage it would crash the API. Then `make test` → all green, including parity. Note the count.
3. `make seed` with today's date; open the app; banner visible on every page.
4. Walk the whole `DEMO_SCRIPT.md` once, timing it (≤ 5 min).
5. Unplug the network (or set `RAKTSETU_PARSER_MODE=rules`) and repeat the parser step: it must still work.
6. Check the finder shows bands only, and "Call before travelling".
7. Check every centre name, phone and message is from the seed (fictional).
8. Re-seed (`make seed`) so the live run starts from the clean state.
9. Browser: zoom 125% for projector, close other tabs, notifications off, a second browser profile with the public
   finder open.
10. Backup: the recorded demo video on the desktop and on a USB stick; screenshots of each step in a folder.
11. Open `docs/CLAIMS_AND_LIMITS.md` and the jury Q&A in `DEMO_SCRIPT.md` §4 on a second screen or printed.
