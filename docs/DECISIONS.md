# Decisions (ADR log), open questions, deviations

Status values: **pending approval** (recommendation only; nothing is built on it until approved) · **accepted** ·
**superseded**. Paths are relative to `RaktSetu_simulator_and_prototype/` unless they start with `raktsetu-app/`.

| ADR | Decision | Recommendation | Status |
|---|---|---|---|
| 001 | Database | SQLite file via SQLAlchemy; Postgres via Docker optional | **accepted** 15 Oct 2026 |
| 002 | Input channel | Mock WhatsApp/SMS channel (paste box + local webhook) + CSV upload | **accepted** 15 Oct 2026 |
| 003 | LLM parser | Claude API, model via env var, rule-based fallback always on | **accepted** 15 Oct 2026 |
| 004 | Auth | Seeded demo users with roles via a role switcher; not real auth | **accepted** 15 Oct 2026 |
| 005 | Frontend | React + Vite (JavaScript), served by FastAPI for the demo; plain-HTML fallback | **accepted** 15 Oct 2026 |
| 006 | Code reuse | Port trust + matcher into `backend/app/core/` with golden parity tests | **accepted** 15 Oct 2026 |
| 007 | Backend framework | FastAPI (as in the deck) | **accepted** 15 Oct 2026 |
| 008 | Where needs come from | Explicit shortfall posts; par-gap kept in core for parity only | **accepted** 15 Oct 2026 |
| 009 | Who approves | Medical officer of the sending centre | **accepted** 15 Oct 2026 (also a specialist question) |
| 010 | "Near-expiry" cut-off | Keep simulator's r ≤ 2 days; label "expires within 2 days" | **accepted** 15 Oct 2026 |
| 011 | What a confirmation refreshes | Only the confirmed group at that centre | **accepted** 15 Oct 2026 |
| 012 | Trust learning sources | Confirmation outcomes only; family-visit feedback deferred | **accepted** 15 Oct 2026 |
| 013 | Demo clock | Seed anchors "now" at 09:00 IST and it then runs in real time | **accepted** 16 Oct 2026 |
| 014 | Received units in later stock posts | Posts do not supersede received units; they expire naturally | **accepted** 16 Oct 2026 |
| 015 | Committing a parsed stock message | Default "add to listing" (listing age unchanged); "replace" for full stock updates | **accepted** 16 Oct 2026 |

---

## ADR-001 Database

**Context.** The deck's stack says PostgreSQL (`out_v3/RaktSetu_TeamTrex_CodeApex3_v3.pdf`, slide 4). The prototype
runs on one laptop for a 3-day build and a live or recorded demo. Docker 29.4 is installed on the dev machine
(checked 15 Oct); whether it runs on the demo machine is unknown.

**Options.**
| Option | For | Against |
|---|---|---|
| A. SQLite file + SQLAlchemy 2.x | zero setup, works offline, trivial reset (`make seed` deletes and rebuilds), no daemon to fail on stage | not the deck's stack; weaker concurrency (irrelevant for one demo user); some type differences (JSON, timezone handling) |
| B. Postgres in Docker + SQLAlchemy | matches the deck; closer to production | Docker Desktop on Windows can fail to start (WSL, virtualisation, RAM); one more moving part in a live demo; setup time on a teammate's machine |
| C. Both: SQLite default, Postgres profile via `DATABASE_URL` + `docker-compose.yml` | demo safety plus a path to the deck's stack | must keep types portable; Postgres path needs one CI-style test run |

**Recommendation: C, with SQLite as the demo default.** Keep SQLAlchemy and portable types (store times as UTC
`DateTime(timezone=True)`, JSON via SQLAlchemy `JSON`), so the swap is a `DATABASE_URL` change. Run the API test suite
once against Postgres in Stage 5 only if time allows (P2). Log the deviation (D-01).

**Consequences.** No migrations framework for Round 2 (`create_all` + seed). If Postgres is added later, introduce
Alembic then.

## ADR-002 Input channel

**Context.** The deck names "WhatsApp / SMS / CSV" inputs and the WhatsApp Cloud API (slide 3 step 1, slide 4).
WhatsApp Business Platform access needs a Meta business account, phone number registration and business verification;
we have none of these, and they are unlikely to complete in 3 days (**UNVERIFIED** timing; no Meta document was read
for this plan). Sending real messages would also risk real phone numbers in a demo.

**Options.**
| Option | For | Against |
|---|---|---|
| A. WhatsApp Cloud API (test number) | real channel | business setup, webhook needs a public HTTPS URL (tunnel), verification timing unknown, demo depends on Meta + network |
| B. SMS gateway (paid Indian provider) | real channel | DLT registration in India, cost, same network dependency |
| C. **Mock channel**: paste box in the UI + `POST /api/channel/mock/inbound` + CSV upload | ready in hours, offline, no real numbers, same parser path a real webhook would call | not a real integration; must be labelled clearly |

**Recommendation: C.** Label it **"mock channel"** in the UI, API responses, README, demo voice-over and report. The
webhook takes a simple `{channel, sender, text}` body; we do **not** imitate Meta's payload, to avoid implying
compatibility we have not tested. Real WhatsApp becomes a post-Round-2 item.

**Consequences.** Deviation D-02. The demo shows messages being pasted, not arriving on a phone.

## ADR-003 LLM parser

**Context.** Deck: "LLM parser + human check" (slide 4). Jury: no accuracy evidence (weakness 8). The demo must not
depend on the network or on a key being present.

**Options (provider).**
| Option | For | Against |
|---|---|---|
| A. Claude API via the official `anthropic` Python SDK, structured outputs | schema-constrained JSON; we already use Claude Code; one key | network + key dependency; cost (small, `PARSER_SPEC.md` §7) |
| B. Another hosted LLM | — | no account set up; no advantage for this task |
| C. Local small model | offline | setup time, weak on Hinglish, laptop RAM |
| D. Rule-based only | offline, deterministic, fast | brittle on free text; does not show the deck's LLM step |

**Options (model, Claude API).** Prices per million input / output tokens from the Claude API reference bundled with
Claude Code (cached 2026-10-06; **re-check before quoting**): `claude-opus-5-5` $4 / $20; `claude-sonnet-5-5` $2 / $10;
`claude-haiku-5-5` $0.10 / $0.50. Estimated eval cost for 150 messages: about $1.20 / $0.60 / $0.03 (assumed
~1,000 in + ~200 out tokens per message; `PARSER_SPEC.md` §7).

**Recommendation: A + D together.** Rule-based parser always present and used whenever there is no key, a timeout
(15 s), an API error, a refusal or a schema-invalid response. LLM path uses `claude-opus-5-5` by default, configurable
through `RAKTSETU_LLM_MODEL`; run the dev split on Opus and on Haiku and pick on measured accuracy and latency, since
cost is negligible at this volume. **Your call on the model.** Key only from `ANTHROPIC_API_KEY` in the environment;
never written to disk by the app, never logged, `.env` git-ignored.

**Consequences.** Two parser paths to test; the eval reports both. Demo runs in `auto` mode and still works offline.

## ADR-004 Auth

**Context.** Roles matter to the story (a medical officer approves every transfer). Real auth is out of scope.

**Options.** A. Seeded demo users + role switcher, identity in an `X-Demo-User` header. B. Password login with hashed
seeded passwords. C. OAuth.

**Recommendation: A.** The server enforces role rules on every endpoint (so the demo can show a staff member being
refused approval), but anyone can pick any user. Label: **"Demo users · not real authentication"** in the header bar
and README. B adds work without making it secure; C is out of scope.

**Consequences.** Never describe the prototype as secure or authenticated (`CLAIMS_AND_LIMITS.md`).

## ADR-005 Frontend

**Context.** Deck: "React + Vite PWA dashboard · public finder page" (slide 4). The existing mock-up is static HTML
generated by `dashboard_v3/build_dashboard_v3.py`; its layout and labels (KPI tiles, centre table with trust bands,
transfer cards with chips and approve buttons, finder panel) should be reused. Node 24 and Python 3.13 are installed.
About 6 hours are budgeted for the UI (`TASKLIST.md` Stage 3).

**Options.**
| Option | For | Against |
|---|---|---|
| A. **React + Vite** (JavaScript, no TypeScript), plain CSS ported from the mock-up | matches the deck; fast for Claude Code to write; component per panel; build served by FastAPI so the demo is one process | a second toolchain (npm); build step |
| B. Streamlit | fastest for data views | hard to do role-specific action cards and a public page; looks like a notebook; not the deck |
| C. Plain HTML + vanilla JS (or htmx) served by FastAPI | no build, one toolchain, can reuse the mock-up's HTML almost verbatim | more manual DOM code for the interactive transfer flow; not the deck |

**Recommendation: A**, without PWA features (deviation D-05). JavaScript rather than TypeScript to save time. Reuse the
mock-up's CSS colours and panel layout. Fallback trigger: if the UI is not showing the full list → confirm → approve
flow by the end of Day 2, switch to C for the remaining screens, reusing the same API.

**Consequences.** `make build-web` produces `frontend/dist/`, mounted by FastAPI at `/`; the demo needs only
`make api` after a build.

## ADR-006 Code reuse from the simulator

**Context.** The deck's claims rest on `sim_v3/raktsetu_sim_v3.py`. The jury asked for the trust model and matcher to
be specified and real (weaknesses 3, 5). The simulator is research code: integer days, numpy, one big `run()` loop.

**Options.** A. Import the simulator at runtime. B. Re-implement from the spec without checking. C. **Port** the
needed functions into a pure library and check them against the simulator with golden fixtures.

**Recommendation: C.** Port `pref_list`, `_dist`/`DIST_WEST`, `surplus_near`, `apportion`, `own_offerable`, the greedy
candidate ordering, the 12-h margin, the Beta(2,1) update and estimate, the staleness bucket and the finder ranking into
`backend/app/core/` (stdlib only). Golden parity tests (`TESTING.md` §2) compare against fixtures generated by
`scripts/gen_golden.py`, which imports the simulator read-only. The strongest test replays whole simulator runs on dev
seeds 9000–9004 with a test-only harness that calls the ported functions, and requires the metric dictionaries to match
exactly. The simulator is never imported by the app.

**Consequences.** Any port bug shows up as a parity failure. Behaviour that differs on purpose (ADR-008, 011, 012) is
outside `core/` and documented as a deviation from the simulator.

## ADR-007 Backend framework

**Context.** Deck: "Python FastAPI" (slide 4). **Recommendation:** FastAPI + Pydantic v2 + Uvicorn, no change.
Consequence: OpenAPI docs at `/docs` are a free demo aid.

## ADR-008 Where needs come from

**Context.** In the simulator, a centre's need per group is `max(0, par_g − stock_g)` with
`par = ceil(1.2·d̄)` apportioned by demand shares (`MODEL_SPEC_v3.md` §4). The deck says centres post "near-expiry
units and shortfalls" (slide 3 step 1). Under strict matching the par rule gives every centre a par of 0 for most
RhD-negative groups (`RESULTS_v3.md` §2).

**Options.** A. Explicit shortfall posts only. B. Par-gap only. C. Both, merged.

**Recommendation: A** for the product; keep `apportion`/par in `core/` for the parity harness and show the par-gap as a
hint on the board (P2). Explicit shortfalls also let a centre request an RhD-negative unit, which the par rule never
does.

**Consequences.** The prototype's needs differ from the simulator's, so its behaviour is not a replay of the simulated
results (deviation from simulator S-01).

## ADR-009 Who approves

**Context.** Deck: "Sending centre confirms; medical officer approves" (slide 3) and "medical officer signs off"
(slide 4) without saying which centre's officer.

**Recommendation:** the **sending** centre's medical officer approves release (the issuing centre is responsible for
what it issues); the receiving centre's staff record delivery. Flagged for the specialist (`MATCHING_POLICY.md` §8 Q5).

## ADR-010 Near-expiry cut-off

**Recommendation:** keep the simulator's r ≤ 2 days for parity; UI wording "expires within 2 days", hours shown per
unit. Flagged as deviation D-10 because the deck says "48 h".

## ADR-011 What a confirmation refreshes

**Context.** In the simulator a confirmation call refreshes the donor's whole snapshot to its true stock
(`refresh_snapshot`, `MODEL_SPEC_v3.md` §4 step 2). In the prototype there is no hidden "true stock"; staff report a
count for one group.

**Recommendation:** the confirmation corrects only that group's listing (missing units marked `not_found`) and does not
reset the centre's listing age. A full re-post is a separate staff action. Deviation from simulator S-02.

## ADR-012 Trust learning sources

**Context.** In the simulator the finder trust learns from confirmation calls **and** family visits
(`MODEL_SPEC_v3.md` §5b). The prototype has no families.

**Recommendation:** learn from confirmations only for Round 2; seed counters with simulated history so bands differ.
Public "was it in stock?" feedback is deferred because it is easy to game without a verification step. Deviation from
simulator S-03.

## ADR-013 Demo clock (accepted 16 Oct 2026)

**Context.** Expiry, the 12-h margin and listing ages all depend on the time of day. A demo at 16:00 would see
different suggestions from one at 09:00 (units expiring tonight fail the margin), which would break the scripted demo.

**Options.** A. Real clock, seed relative to "now" in hours. B. Freeze time. C. **Anchor**: the seed stores an anchor
(today 09:00 IST, the simulator's decision time) and the real time of seeding; the app's "now" is anchor + elapsed
real time.

**Recommendation / implemented: C.** Time still moves (margins can be shown changing), but the demo starts at the
same simulated 09:00 whenever `make seed` is run. `/api/health` reports `demo_clock: true`; the UI must show
"demo clock (simulated)". Consequence: re-seed shortly before the demo (pre-demo checklist step 3).

## ADR-014 Received units in later stock posts (accepted 16 Oct 2026)

**Context.** A stock post replaces a centre's listed units. If it also replaced received units, a re-post would
drop the one-hop flag and a received unit could be offered again.

**Implemented:** posts supersede only units not received by transfer; received units stay listed (flagged, never
offered) until they expire. Cost: a centre cannot yet record that a received unit was issued to a patient.
**Alternative for later:** an "issued / discarded" action per received unit.

## ADR-015 Committing a parsed stock message (accepted 16 Oct 2026)

**Context.** A stock post replaces a centre's whole listing (snapshot semantics). Messages are often partial
("O+ 2 kal expire"); treating one as a full snapshot would silently delist everything else the centre listed.

**Implemented:** a reviewed draft commits as **add** (new units listed, nothing superseded, the centre's listing age
NOT refreshed, because a partial message does not vouch for the rest of the listing) unless the text reads like a
full update ("stock update", "total stock", "current stock"), in which case it defaults to **replace** (a normal
stock post that refreshes the listing age). The reviewer can switch either way before committing.
**Consequence:** listing age, and so the trust bucket, only improves when a centre sends a full update.

---

## Open questions

| # | Question | Why it matters | Owner | Blocking? |
|---|---|---|---|---|
| Q1 | **Round 2 dates.** The deck says "Round 2 (15–18 Oct)" (slide 6). That date came from our deck, not from the organisers. **UNVERIFIED.** What is the submission deadline and the presentation slot? | sets the cut line for every stage | Team (ask organisers) | yes, for scheduling |
| Q2 | **Round 2 format.** Live demo, recorded video, repo link, written report, or a mix? Time limit? Internet on stage? | demo script must work live and recorded; may need a video by a deadline | Team | yes, for Stage 5 |
| Q3 | Can a transfusion-medicine specialist review `MATCHING_POLICY.md` (7 questions in §8) before Round 2? | the jury will ask; "not clinically validated" stays until then | Team | no (label covers it) |
| Q4 | Do we have an Anthropic API key for the parser, and a spending cap? | LLM path and its eval; rules work without it | Team | no |
| Q5 | Which machine runs the demo, and does it have Python 3.11+, Node 18+, make? Windows? | setup risk on the day | Team | no |
| Q6 | Is the project in a git repository with a remote? (`E:\D\Hackathons\CodeApex\project` is not a git repo as of 15 Oct.) The deck/jury want a repo link. | repo link deliverable; history for the report | Team | soon |
| Q7 | Who writes the ≥ 60 hand-written parser test messages (English + Hinglish), and who labels / double-checks? | avoids a circular parser test | Team | blocks Stage 4 eval |
| Q8 | ~~Approve ADR-001…012~~ **Resolved 15 Oct 2026: all approved as recommended.** | — | Team | no |
| Q9 | Should the demo show `standard` / `relaxed` policies at all, or only strict? | more to explain, more clinical risk in the story | Team | no |
| Q10 | Real-world anchor: any medical officer or blood centre willing to look at the prototype or give an anonymised stock/discard log (jury weakness 1)? | strongest single improvement per the jury | Team | no |

## Deviations from deck

Each is flagged to the team at Checkpoint A. "Deck" = `out_v3/RaktSetu_TeamTrex_CodeApex3_v3.pdf`.

| ID | Deck says | Prototype does | Why | ADR |
|---|---|---|---|---|
| D-01 | PostgreSQL (slide 4) | SQLite by default; Postgres optional via `DATABASE_URL` | demo robustness, 3-day build | 001 |
| D-02 | WhatsApp Cloud API; WhatsApp/SMS/CSV input (slides 3, 4) | **mock channel** (paste + local webhook) and CSV | no business verification; offline demo | 002 |
| D-03 | e-RaktKosh public stock as a prior (slide 4) | not used | no access; out of scope | — |
| D-04 | Docker · India-region cloud · GitHub Actions CI (slide 4) | local laptop only; CI only if a repo exists and time allows | time | — |
| D-05 | React + Vite **PWA** (slide 4) | React + Vite SPA, no PWA features | time | 005 |
| D-06 | "maps ETA" / "ETA" on dispatch (slide 4 step 5) | fixed seeded transport estimate per centre pair (ASSUMPTION) | no maps integration | — |
| D-07 | "SBTC / FDA report" output (slide 4) and regulator view (slide 5, planned) | not built | planned in deck too | — |
| D-08 | Sending centre "confirms" (implicitly by phone, as in the simulator) | in-app confirm button, role-played | no telephony | — |
| D-09 | 20–24 °C box (slide 3 step 4, slide 4 step 5) | checkbox recorded at dispatch, not verified | no device | — |
| D-10 | "48 h units" (slides 3, 4) | r ≤ 2 days, which is ≤ 39 h at 09:00 | parity with the simulator | 010 |
| D-11 | Hindi and Marathi input (slide 5, feature 6, marked planned) | English + Hinglish only | time | 003 |
| D-12 | Medical officer signs off (slides 3, 4), centre unspecified | sending centre's MO | needs a choice | 009 |

## Deviations from the simulator (behaviour outside `core/`)

| ID | Simulator | Prototype | ADR |
|---|---|---|---|
| S-01 | needs = par − stock per group | explicit shortfall posts | 008 |
| S-02 | confirmation refreshes the donor's whole snapshot and resets listing age | corrects only the confirmed group | 011 |
| S-03 | finder trust learns from calls and family visits | from confirmations only; seeded history | 012 |
| S-04 | decisions at 09:00 on integer days | continuous time; r computed from `expires_at` | 010 |
| S-05 | matcher calls `attempt()` sequentially and re-plans after each call outcome | matcher run plans all suggestions at once (each `attempt` assumed to succeed); the coordinator re-runs it after failed or partial confirmations | 006 |
| S-06 | dispatch-reliability trust and adaptive arm D | not implemented (arm D underperformed, `RESULTS_v3.md` §3) | — |

Consequence: the prototype demonstrates the **mechanism**. It does not reproduce or re-measure the simulated outcome
numbers, and must not be presented as doing so.
