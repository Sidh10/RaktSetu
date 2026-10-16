# Specification

Status: **draft for approval** (Checkpoint A). Priorities: **P0** = needed for the end-to-end demo; **P1** = should
have; **P2** = stretch, first to cut. Each requirement maps to a test in `TESTING.md` or a step in `DEMO_SCRIPT.md`.

## 1. Purpose

Show, as running software on simulated data, the flow the deck promises for Round 2
(`out_v3/RaktSetu_TeamTrex_CodeApex3_v3.pdf`, slide 6, column "Round 2"): a backend with the trust estimate and an
ABO/RhD-aware matcher on a live data model; a stock-message parser and a public finder page; and an end-to-end demo of
list → match → confirm → approve. This answers the jury's main criticism that the system was "mostly a simulation"
with a static UI (`inputs/Strict_Jury_Evaluation.docx`, verdict B).

## 2. User roles

| Role | Who (in the demo: role-played) | Can |
|---|---|---|
| `coordinator` | City-level coordinator (e.g. at an SBTC-linked hub) | see all centres, run the matcher, request confirmations, cancel, see trust counters and audit |
| `centre_staff` | Blood-centre technician at one centre | post stock and shortfalls for **own** centre, answer confirmation requests, mark dispatched / delivered for own centre, review parser drafts for own centre |
| `medical_officer` | Medical officer at a centre | everything `centre_staff` can see for own centre, plus **approve / reject** transfers sent from own centre (ADR-009, pending) |
| `public` | Family member or patient attendant; no login | use the public finder only |

Demo users are seeded and selected from a role switcher. **This is not real authentication** (ADR-004).

## 3. Functional requirements

### 3.1 Stock listing (FR-L)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-L1 | P0 | Staff can post a stock snapshot for their centre: list of units with component (RDP/SDP), ABO/RhD group and expiry date-time. A post replaces the centre's listed units. | API test `test_stock_post_replaces_listing` |
| FR-L2 | P0 | Each listed unit gets an opaque platform ID; no donor, bag or patient field exists. | `test_unit_schema_has_no_identifying_fields` |
| FR-L3 | P0 | The board shows, per centre: listed units, near-expiry units (`MATCHING_POLICY.md` §3), time since last post, and the trust band. | UI check, `DEMO_SCRIPT.md` step 1 |
| FR-L4 | P0 | Staff can post a shortfall request (group, component, count) for own centre. No patient data. | `test_shortfall_has_no_patient_fields` |
| FR-L5 | P1 | Staff can upload the same snapshot as CSV (template provided). | `test_csv_upload_equals_form_post` |
| FR-L6 | P0 | Units received by transfer are listed with `received_via_transfer = true` and are never offered by the matcher (one-hop). | `test_one_hop_received_units_never_offered` |
| FR-L7 | P0 | Expired units drop out of the listing automatically at read time. | `test_expired_units_not_listed` |

### 3.2 Matching (FR-M)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-M1 | P0 | Coordinator runs the matcher; it creates `suggested` transfers from offerable near-expiry surplus to open shortfalls. | `test_match_run_creates_suggestions` |
| FR-M2 | P0 | Default policy `strict` (ABO- and RhD-identical). `standard` / `relaxed` are selectable per run and flagged on every resulting card (`MATCHING_POLICY.md`). | `test_strict_never_crosses_groups`, `test_relaxed_sets_anti_d_flag` |
| FR-M3 | P0 | Offerable surplus per (centre, group) equals the simulator's `own_offerable` on the listed units. | parity `P-04` |
| FR-M4 | P0 | Matcher order equals the simulator's greedy: needs largest-first, candidates by tier then offered count descending, stable by centre index; a centre never supplies itself. | parity `P-06`, `P-08` |
| FR-M5 | P0 | Each suggestion carries a "why" text: the shortfall, the donor's near-expiry surplus beyond its own expected use, the tier, the trust band. | `test_suggestion_has_reason` |
| FR-M6 | P0 | Units that cannot meet the 12-h margin on arrival are not suggested. | `test_margin_blocks_unit`, parity `P-07` |

### 3.3 Confirm, approve, dispatch (FR-T)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-T1 | P0 | Transfer state machine exactly as in `DATA_MODEL.md` §3; illegal transitions return 409. | `test_state_machine_table` |
| FR-T2 | P0 | Sending-centre staff confirm with the number of units actually available (0…requested). 0 → `failed`; partial → `confirmed` with reduced quantity. | `test_confirm_partial`, `test_confirm_zero_fails` |
| FR-T3 | P0 | Each confirmation updates the finder trust counters of the sending centre for the listing-age bucket recorded at suggestion time: α += found, β += requested − found. | parity `P-09`, `test_confirm_updates_trust` |
| FR-T4 | P0 | Only `medical_officer` (ADR-009) can approve or reject. Nothing reaches `dispatched` without an approval event. | `test_only_mo_can_approve`, `test_no_dispatch_without_approval` |
| FR-T5 | P0 | The 12-h margin is re-checked at approve and dispatch with the current time and the transport estimate. | `test_margin_rechecked_at_dispatch` |
| FR-T6 | P0 | Every transition writes an audit row: actor, role, from, to, timestamp, note. | `test_every_transition_audited` |
| FR-T7 | P1 | Coordinator can cancel any non-terminal transfer with a reason. | `test_cancel` |
| FR-T8 | P1 | A failed or partial confirmation reopens the remaining shortfall so the next matcher run can try another donor. | `test_partial_reopens_need` |

### 3.4 Public finder (FR-F)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-F1 | P0 | Public page: choose group and component; see centres with listed compatible units, ranked by listed × p (trust ranking, `MODEL_SPEC_v3.md` §5b). | `test_finder_ranking`, parity `P-10` |
| FR-F2 | P0 | Each result shows a **band** (High ≥ 0.8, Medium 0.5–0.8, Low < 0.5; `sim_v3/bands_v3.py`), never a percentage. | `test_finder_response_has_no_probability` |
| FR-F3 | P0 | Every result shows "Call before travelling", the time since last update and a phone number (fictional in the demo). | UI check |
| FR-F4 | P1 | An info box explains what bands meant in simulation, citing `sim_v3/results/finder_bands.json` and labelled simulated. | UI check |
| FR-F5 | P0 | The finder needs no login and stores nothing about the searcher. | `test_finder_writes_nothing` |

### 3.5 Parser and mock channel (FR-P)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-P1 | P0 | Mock channel: paste box in the UI and `POST /api/channel/mock/inbound`. Labelled "mock channel" everywhere. | `test_mock_inbound_creates_draft` |
| FR-P2 | P0 | Rule-based parser handles the English and Hinglish formats in `PARSER_SPEC.md` §3 with no network. | parser unit tests |
| FR-P3 | P1 | LLM parser (Claude API) used when a key is set; on error or timeout it falls back to rules. | `test_llm_failure_falls_back` (mocked client) |
| FR-P4 | P0 | Parsed output is a **draft**. A human must review and commit it before stock changes. | `test_draft_does_not_change_stock` |
| FR-P5 | P1 | Accuracy measured on the frozen synthetic test split and reported with the human-check rate (`PARSER_SPEC.md` §6). | `make parser-eval` output saved |
| FR-P6 | P2 | Hindi (Devanagari) and Marathi messages. | **planned**, not in Round 2 |

### 3.6 Platform (FR-X)

| ID | Pri | Requirement | Acceptance test |
|---|---|---|---|
| FR-X1 | P0 | Role switcher with seeded demo users; every UI page shows the banner "Simulated data · mock channel · not clinically validated". | UI check |
| FR-X2 | P0 | `make seed` rebuilds the demo city deterministically. | `test_demo_seed_contract` |
| FR-X3 | P1 | Audit view (coordinator): filterable list of audit rows. | UI check |
| FR-X4 | P0 | Runs offline on Windows with no API key. | pre-demo checklist |

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | `core/` reproduces the simulator's decisions on fixed inputs exactly (golden parity, `TESTING.md` §2). |
| NFR-2 | Demo flow completes in ≤ 5 minutes with no page taking > 2 s on a laptop. |
| NFR-3 | No secret in the repo; key only from the environment. |
| NFR-4 | No patient data; no donor-linkable unit identifiers. |
| NFR-5 | All UI copy passes the claims audit (`CLAIMS_AND_LIMITS.md` §4). |

## 5. Non-goals (explicitly out of scope for Round 2)

- Real WhatsApp Cloud API or SMS gateway integration (mock channel only; ADR-002).
- Real authentication, authorisation hardening, multi-tenant security.
- Clinical decision support beyond encoding the cited matching rules; no dosing, no patient selection.
- Patient records, cross-match, or any patient identifier.
- Courier booking, routing, maps, live ETA, cold-chain monitoring.
- e-RaktKosh integration or any external data pull.
- Regulator (SBTC / FDA) reporting view.
- Hindi / Marathi parsing.
- Adaptive "dispatch without confirmation" (simulator arm D; it underperformed: `RESULTS_v3.md` §3).
- Exact / LP matcher (the gain over greedy was ≤ 0.04 pp unserved: `RESULTS_v3.md` §10).
- New simulation results or any claim of measured real-world impact.
- Deployment to a cloud host, Docker images, CI pipelines (deferred; deviation D-04).
- Red cells and plasma.
