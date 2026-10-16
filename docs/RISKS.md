# Risks

Likelihood (L) and impact (I): H / M / L. Reviewed at every checkpoint.

| # | Risk | L | I | Mitigation | Fallback |
|---|---|---|---|---|---|
| R1 | **Time.** ~3 working days (deck's Round 2 dates, UNVERIFIED) for backend, UI, parser, eval and demo | H | H | Staged plan with checkpoints; P0 list fixed now; cut order in `TASKLIST.md` §3; verification never cut | Ship the API + minimal UI for list → match → confirm → approve; parser rules-only; drop CSV, audit view, LLM eval |
| R2 | **WhatsApp Business verification** cannot complete in time | H | M | Not attempted for Round 2; mock channel (ADR-002) | Same; label "mock channel" |
| R3 | **LLM key / cost / network** missing or failing on stage | M | M | Rule-based parser always on; `auto` mode; 15 s timeout; spending cap on the key; no key in repo | Demo in `rules` mode; show a pre-recorded LLM draft screenshot if asked |
| R4 | **Round 2 format unknown** (live, video, repo, report) | H | M | Demo script works live and recorded; record a video by end of Day 3; README run steps; report-ready parity and parser results | Whichever format is announced, assets already exist |
| R5 | **Parity test fails** (port bug, float edge, ordering) | M | H | Port function by function with its fixture; P-08 replay last | Stop at the checkpoint and fix; never relax a fixture. If P-08 cannot pass in time, report P-01…P-07, P-09, P-10 and say P-08 is pending |
| R6 | **Frontend slips** | M | H | Reuse mock-up CSS; build the transfer card first; API usable via `/docs` | Switch remaining screens to plain HTML (ADR-005 fallback); worst case demo the flow in `/docs` + board |
| R7 | **Overclaiming** in UI, voice-over or report (the jury already penalised this) | M | H | `CLAIMS_AND_LIMITS.md`; claims-audit test; banner on every page | Pre-demo read-through of every screen |
| R8 | **Clinical policy challenged** by a jury member | M | M | Strict default; sources cited; "not clinically validated"; specialist questions ready (`MATCHING_POLICY.md` §8) | Answer: prototype rules, specialist review is the next step |
| R9 | **Demo machine problems** (Windows paths, no make, Node/Python versions, Docker) | M | H | SQLite default; commands copyable without make; pre-demo checklist on the actual machine | Recorded video + screenshots on USB |
| R10 | **Circular parser evaluation** (same model writes and parses the tests) | M | M | ≥ 60 hand-written messages; no LLM paraphrases; frozen split | Report rules and LLM separately; say the set is synthetic |
| R11 | **Seed drift breaks the scripted demo** | M | M | `test_demo_seed_contract` | Re-seed; script has fallback lines |
| R12 | **Real personal data slips into the demo** (a real phone number typed in the paste box) | L | H | Fictional sender list only; `possible_patient_data` flag; demo uses prepared messages | Discard the draft; reset DB |
| R13 | **Secret leak** (key committed or shown on screen) | L | H | `.env` git-ignored; key never logged or displayed; set the key in the shell before the demo, not on screen | Revoke and rotate the key immediately |
| R14 | **No git repo / no repo link** (folder is not a repo on 15 Oct) | H | M | `git init` and a private remote on Day 1 (human decision) | Zip the folder as the submission |
| R15 | **Bus factor**: one person + Claude Code builds everything | M | M | `CLAUDE.md` + docs let another session or teammate continue; small commits | Teammate runs the demo from the README |
