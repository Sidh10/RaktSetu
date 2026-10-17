# Report and slide inserts (Round 2)

Paste-ready text for the Round 2 report, slides and video narration. Every number cites the file it comes from.
Paths starting `sim_v3/`, `deck_v3/` or `inputs/` are in `RaktSetu_simulator_and_prototype/`; other paths are in
`raktsetu-app/`. State as of **16 Oct 2026**. Re-check the counts with `make test` before copying them.

> Required wherever this text is used: **simulated data · mock channel · not clinically validated**.

---

## 1. One-paragraph summary

In Round 1 RaktSetu was a simulator and a static UI mock-up. For Round 2 we built the system the deck described:
a working prototype where centres list near-expiry platelets, a greedy matcher suggests transfers under strict
ABO/RhD matching, the sending centre confirms what is really there, and a medical officer approves before anything
is dispatched. A public finder shows likelihood bands, and a stock-message parser turns typed messages into drafts
that a person checks. The matching and trust code is a port of the simulator. Golden parity tests show it makes
exactly the same decisions, including over 17 complete simulated 180-day runs, so the demo and our simulated
results describe the same model. All data in the prototype is simulated, the WhatsApp/SMS input is a mock channel,
and the matching rules have not yet been reviewed by a transfusion specialist.

## 2. What is built (status table)

| Part | Status | Evidence |
|---|---|---|
| Trust model, greedy matcher, ABO/RhD tiers, 12-h margin, finder bands | **Built**, ported from the simulator | 23 parity tests pass (`backend/tests/parity/`) |
| Backend: database, API, roles, transfer workflow, audit log | **Built** | 42 API tests incl. workflow, roles, privacy, parser inbox (`backend/tests/api/`) |
| Browser UI: coordinator board, transfer cards, inbox, report trust, audit, public finder | **Built** | Demo steps 1–8 walked through in the browser (`docs/DEMO_SCRIPT.md`) |
| Message parser: rule-based plus Claude API, with human check | **Built**; LLM path tested only with a fake client | Parser unit and inbox tests (`backend/tests/core/test_parser_rules.py`, `backend/tests/api/test_inbox.py`) |
| Parser accuracy on a test set | **Pending**: needs ≥ 60 hand-written messages | Targets frozen in advance (`backend/tests/parser/targets.json`) |
| Not built: WhatsApp Cloud API, SMS gateway | **Mock only** | Mock channel instead (`docs/DECISIONS.md` ADR-002) |
| Hindi/Marathi parsing, regulator view, e-RaktKosh link | **Planned** | Marked planned in the deck too (`out_v3/…v3.pdf`, slide 5) |

## 3. How it works (architecture, short)

One FastAPI backend with a SQLite database and a React UI, run as a single process on a laptop
(`docs/ARCHITECTURE.md`). Decision logic lives in a pure library (`backend/app/core/`) with no database or clock
access; this is what the parity tests check against the simulator. Every change to a transfer goes through one state
machine: suggested → confirmation requested → confirmed or failed → approved → dispatched → delivered, or cancelled.
Each step checks the user's role and writes an audit row (`docs/DATA_MODEL.md` §3).

Rules enforced in code, each with a test:
- **Medical-officer approval.** Only a medical officer of the sending centre can approve, and nothing is dispatched
  without approval (ADR-009).
- **One-hop rule.** Units received by transfer are never offered again (D&C Rules 122P(xv), as in
  `sim_v3/MODEL_SPEC_v3.md` §1).
- **12-hour margin.** Units must arrive with at least 12 hours left. This is a team-chosen margin, not a regulation
  (`sim_v3/PREREGISTRATION_v3.md`, Amendment 2). It is checked at suggestion, approval and dispatch.
- **Strict ABO/RhD by default.** This is the DGHS/NBTC 2023 manual's default for platelets
  (`sim_v3/sources/DGHS_TMTM_2023_p160_sec5.3_excerpt.txt`).
- **No patient data.** Requests carry group, type and count only; any extra field is rejected. Unit IDs are random
  and not linkable to donors.
- **Bands only in the public finder.** The finder never shows a percentage.

## 4. Evidence 1: the prototype runs the same model as our results

- **Function level.** Six parity tests compare the ported functions with the simulator on **2,342** recorded cases:
  preference lists, group shares (bit-identical), par levels, near-expiry surplus, listing ageing and bands
  (`backend/tests/golden/p01–p05, p10`).
- **Whole runs.** **17** complete 180-day simulator runs are replayed through the ported code (`p08_whole_runs.json`).
  Every day's stock, listing age, trust value, confirmation call and family visit must be identical. They are.
  - The 17 runs cover both data-quality scenarios, all three matching policies, the raw and trust finders, the naive
    matcher, no platform, and a 30% no-answer / 3-hour transport stress case.
  - All runs use development seeds that are never reported (`sim_v3/PREREGISTRATION_v3.md` §1).
- **The tests can fail.** We injected bugs into the ported code: halving the trust update, reversing the finder
  tie-break, reversing the matcher order, widening "near-expiry" to 3 days, and moving the margin to 11 h or 13 h.
  The replay caught every one (`docs/TESTING.md` §2).

## 5. Evidence 2: the workflow does what the deck promises

From the demo run (`docs/DEMO_SCRIPT.md`; simulated city in `data/seed/demo_city.json`):
- **Matching.** The strict match suggests Centre F → C (2 × O+) and Centre G → A (2 × B+).
- **Margin.** Centre H's unit is excluded: over a 3-hour trip it would arrive with under 12 h left.
- **Approval rule.** A centre staff member trying to approve is refused (403). The medical officer approves.
- **One-hop.** Units delivered to Centre C are listed there but never offered again.
- **Stale listing.** Centre G listed 2 units but confirmed only 1. Its trust counters for 2-day-old listings move
  from α 5, β 6 to α 6, β 7, and Centre A's remaining need reopens automatically.

Automated: **225** backend tests pass. That is 106 core, 23 parity, 42 API and 54 claims-audit checks, run per
folder on 17 Oct (`make test`). The claims audit fails the build if a forbidden claim, such as "clinically
validated" or a percentage in the finder, appears anywhere a user or judge would see it.

## 6. Evidence 3: the parser (placeholder: fill only from the frozen test run)

> **[TO FILL after `python scripts/parser_split.py --freeze` and `python scripts/parser_eval.py --split test`]**
> "On [N] synthetic test messages ([n_h] hand-written by the team, [n_g] template-generated; English and Hinglish),
> the rule-based parser read [X%] of items exactly [95% CI a–b]. Critical errors (a wrong group or count that could
> be committed without a flag): [Y]; frozen target 0: [PASS/FAIL]. [Z%] of drafts needed a human check. Hand-written
> messages: [X_h%]; generated: [X_g%]."
> Source: `scripts/out/parser_eval_test_<time>.md`. Do not quote the pipeline preview: it is not reportable.

Already true, and safe to say:
- Every parsed message becomes a draft; nothing changes until a person checks and commits it.
- The model, if used, only extracts fields. Our code resolves dates and raises the checks, the same way for both
  parser paths.
- Commit is blocked while a group, count or expiry is missing, or the text may contain patient data.
- The accuracy target was fixed before any test score existed (`backend/tests/parser/targets.json`).

## 7. Simulated results we may quote (always "in simulation", with the source)

| Claim | Value | Source |
|---|---|---|
| Families sent to search | −37% (13.52 → 8.55/day, realistic data); target −40% **failed (G1)** | `sim_v3/RESULTS_v3.md` §1–2 |
| Failed visits to empty centres | −66% (4.89 → 1.68/day); target −80% **failed (G2)** | `sim_v3/RESULTS_v3.md` §1; deck slide 7 |
| Patients left unserved | 4.16% → 2.20% (realistic); 7.70% → 2.49% (poor data) | `sim_v3/RESULTS_v3.md` §2 |
| Confirmation calls | about 3.7 a day (3.66 / 3.80) | `sim_v3/RESULTS_v3.md` §2, §6 |
| Wasted courier trips | 0 by design (every transfer is confirmed); naive matcher 130–201 per 150 days | `sim_v3/RESULTS_v3.md` §2 |
| Finder bands | High / Medium / Low centres had stock on 87% / 71% / 54% of visits | `sim_v3/results/finder_bands.json` (S1) |
| Exact vs greedy matcher | an exact matcher changed unserved % by at most 0.04 pp | `sim_v3/RESULTS_v3.md` §10 |

All rest on assumed data-error rates in a synthetic 8-centre city (`sim_v3/RESULTS_v3.md`, header).

## 8. How Round 2 answers the Round 1 jury

The jury evaluated the v2 deck (`inputs/Strict_Jury_Evaluation.docx`). Mapping its points to what changed:

| Jury point (v2 deck) | Round 2 answer |
|---|---|
| "Mostly a simulation with a static UI" (verdict); implementation 3/5 | Working end-to-end prototype (§2, §5) |
| "Working prototype" overstated (weakness 3) | Every screen labelled; automated claims audit (§5) |
| Trust model and matcher not specified (weakness 5) | Specified in `sim_v3/MODEL_SPEC_v3.md`, ported, parity-tested (§4) |
| No parser accuracy evidence (weakness 8) | Labelled test set with a hand-written part, frozen split and targets; result pending (§6) |
| "0 wasted trips" is by construction (weakness 6) | Stated as "by design", next to the call cost of ~3.7 calls a day (§7) |
| Public in-stock estimate shown to families was unvalidated (weakness 7) | Bands only, with the calibration-based band hit rates (§7) |
| "What exists today, and what will you demo?" (Q11) | Status table (§2) and the 5-minute demo script |

## 9. Limits (put on the slide)

- **Simulated data:** fictional centres, stock, people and trust history.
- **Mock channel:** messages are typed or pasted; no WhatsApp or SMS integration.
- **Not clinically validated:** strict ABO/RhD by default, from cited sources; specialist review pending
  (`docs/MATCHING_POLICY.md` §8).
- **Demo users:** a role switcher, not real authentication. It runs locally on one laptop.
- **Outcome numbers are simulated:** the prototype measures nothing real yet. That needs a pilot.

## 10. Slide-sized inserts

**"Built for Round 2"**: Working prototype on simulated data: list → match → confirm → approve → dispatch → deliver ·
medical-officer approval enforced · one-hop rule · 12-h margin (our choice) · audit log · public finder with
likelihood bands · message parser with human check (mock channel).

**"Same model as our results"**: Ported trust and matcher code reproduces the simulator exactly: 2,342 function cases
and 17 whole 180-day runs, identical day by day; injected bugs are caught. 200+ automated tests.

**"What we do not claim"**: Simulated data · mock channel · not clinically validated · no real-world outcome measured
yet · parser accuracy: [fill from frozen test run].

## 11. Next steps (from `docs/TASKLIST.md` and the deck's roadmap)

1. Transfusion-specialist review of the matching policy (7 questions ready: `docs/MATCHING_POLICY.md` §8).
2. Parser accuracy on the frozen test set; then real (consented, de-identified) messages in a pilot.
3. A pilot with 5–8 centres to measure real outdates, transfers, families and report accuracy (deck slide 6).
4. Real WhatsApp Business integration once verification is possible (ADR-002).

Repo / demo link: **[add once the repository exists: open question Q6]**.
