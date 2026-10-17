# Backup screenshots of the demo (17 Oct 2026)

Use these if the live demo fails: say "let me show the recorded run" and step through them in order.
All screens show **simulated data · mock channel · not clinically validated** in the banner. Captured from the real
running app, seeded with `scripts/demo_start.py` (demo clock 09:00 IST). Files 01–05 and 09 come from the in-app browser
(800 px wide); files 06–08 from headless Microsoft Edge (1280 px wide).

| # | File | Shows | Say |
|---|---|---|---|
| 1 | `01_board.jpg` | Coordinator board: KPI tiles, centre table with listing age and report-trust bands | "Every listing may be stale; Centre G updated 2 days ago and its trust is Low." |
| 2 | `02_matcher_suggestions.jpg` | Strict match: F → C 2 × O+ (High) and G → A 2 × B+ (Low); Centre H's unit excluded by the 12-h margin | "Near-expiry surplus only, strict blood groups; H's unit would arrive with under 12 h left." |
| 3 | `03_staff_confirms.jpg` | Staff, Centre F sees only its own transfer and confirms the units really there | "No courier moves on a listing alone." |
| 4 | `04_staff_approval_refused.jpg` | Staff clicks Approve: red toast "refused (403 forbidden_role)" | "Only a medical officer can approve; the backend enforces it." |
| 5 | `05_officer_approved.jpg` | Medical officer approves; chip "≥ 12 h on arrival (min 13.5 h)"; dispatch next | "The 12-hour margin is checked again at approval and dispatch." |
| 6 | `06_report_trust.png` | Report trust table: Centre G's "2+ days old" row moved to α 6, β 7 after confirming only 1 of 2 | "Every confirmation updates that centre's trust. No decay, every outcome counts." |
| 7 | `07_inbox_draft_flags.png` | Mock-channel message parsed into a draft: "kal" resolved and flagged, B+ "expiry missing", Commit disabled | "The parser only drafts; a person checks every draft before stock changes." |
| 8 | `08_audit_log.png` | Append-only audit log of the whole run: who, role, change, when | "Every step is logged." |
| 9 | `09_public_finder.jpg` | Public finder, B+ search, no login: High / Medium / Low bands, "Call before travelling", fictional phones | "Families see a band, never a percentage, and always call first." |
