# 10-minute presentation runbook (Round 2)

The slot is **10 minutes, and the jury may ask for a demo**. This page is what to do and say, minute by minute.
The full 5-minute demo with every click is `docs/DEMO_SCRIPT.md`; this page has a **3-minute** version that fits
inside 10 minutes. Paths starting `sim_v3/` or `out_v3/` are in `RaktSetu_simulator_and_prototype/`.

> Say these words early and keep them on screen: **simulated data · mock channel · not clinically validated.**

## 0. One hour before

1. Close heavy apps (browsers you are not using, IDEs, chat apps, MySQL). On 16–17 Oct the laptop ran low on Windows
   commit memory and Python crashed silently twice.
2. From `raktsetu-app/` run **`.venv\Scripts\python.exe scripts\demo_start.py --check`**. You want `0 FAIL`.
   A memory WARN means: close more apps.
3. Then **`.venv\Scripts\python.exe scripts\demo_start.py`**. It re-seeds the city (demo clock 09:00 IST), starts the
   server and opens `http://localhost:8000/#/board`. Leave that window open.
4. Browser zoom 125% for the projector. Open a second tab at `http://localhost:8000/#/finder`.
5. Have the backup ready: `docs/demo_screens/` (screenshots of every step), and your recorded video if you made one.
6. **After any rehearsal, run `demo_start.py` again**: the demo changes the data, and re-seeding resets it.

## 1. Timing

**Plan A: the jury wants the demo inside the 10 minutes**

| Time | What |
|---|---|
| 0:00–0:45 | Problem (deck slide 2): platelets last 5 days; 8–48% discarded in three Indian hospital studies |
| 0:45–2:15 | Solution and mechanism (slide 3): confirm first, learned trust, bands for families |
| 2:15–3:30 | **What we built for Round 2** (§3 below) and how we know it matches our model |
| 3:30–4:30 | Results (slides 6–7): honest, including G1 and G2 failed |
| 4:30–7:45 | **Live demo, 3-minute path (§2)** |
| 7:45–9:00 | Limits and next steps (§4) |
| 9:00–10:00 | Buffer for one question |

**Plan B: no demo asked inside the slot.** Same order, about 1.5 minutes per section, and end with: "We can show the
working system now if you would like." Keep the demo window open for questions.

## 2. The 3-minute demo (exact clicks)

Start: `http://localhost:8000/#/board`, **Acting as: Coordinator**, freshly seeded.

| # | Click | Say |
|---|---|---|
| 1 | Point at the banner and the **Report trust** column. | "This runs end to end on simulated data. Centre G last updated two days ago and its confirmations often fell short, so its trust is Low." |
| 2 | **Run matcher** panel → keep **Strict** → **Run**. | "Strict blood groups, near-expiry surplus only. Two transfers suggested. Centre H's unit is excluded: on a 3-hour trip it would arrive with under 12 hours left, which is our safety margin." |
| 3 | Card **Centre F → Centre C** → **Request confirmation**. | "No courier moves on a listing alone; the sending centre confirms first." |
| 4 | **Acting as → Staff, Centre F** → **Confirm** (2 of 2). Then click **Approve dispatch**. | Red toast "refused (403)": "Staff cannot approve; the backend enforces it." |
| 5 | **Acting as → Medical officer, Centre F** → **Approve dispatch**. | "A medical officer approves every transfer, and the 12-hour margin is checked again." |
| 6 | **Acting as → Coordinator** → card **Centre G → Centre A** → **Request confirmation**. **Acting as → Staff, Centre G** → set *Units actually available* to **1** → **Confirm**. | "The stale listing said 2; only 1 is really there. Every confirmation updates that centre's trust." (Toast shows α and β.) |
| 7 | Second tab, **Public platelet finder**, **B+** → **Search**. | "Families see High, Medium or Low, never a percentage, and always 'call before travelling'." |

If there is more time, continue from `DEMO_SCRIPT.md` (dispatch and deliver, one-hop rule, message inbox, audit).

**If something breaks:** say "let me show the recorded run", then open `docs/demo_screens/` or the video. If the data
looks wrong, run `demo_start.py` again (about 5 seconds) and reload.

## 3. What to say about Round 2 (the deck predates the prototype)

**Present from the Round 2 deck: `deck_r2/out/RaktSetu_TeamTrex_CodeApex3_Round2.pptx`.** It is the v3 deck with slides
3–6 replaced to show what is built (slides 1, 2, 7, 8 are byte-identical to v3). If you must use the old v3 deck,
say the corrections below out loud when you reach those slides. The jury penalised the static UI in Round 1.

| Deck (`out_v3/RaktSetu_TeamTrex_CodeApex3_v3.pdf`) | Now true; say this |
|---|---|
| Slide 3: "Built so far: a simulator … and a UI mock-up on simulated data. The backend is not built yet." | "Since the last round we built the backend and a working UI: list, match, confirm, approve, dispatch and deliver run end to end on simulated data." |
| Slide 4: stack labelled "planned · only the simulator and UI mock-up exist" | "FastAPI, the database and the parser are now built. We used SQLite instead of PostgreSQL for the prototype, and a mock channel instead of the WhatsApp Cloud API." |
| Slide 5: "UI mock-up on simulated data" screenshot | "This is now the working app, which we will show you live." |
| Slide 6: "Round 2 (15–18 Oct)" column (FastAPI backend, parser, finder, end-to-end demo) | "All of this column is built, except the specialist review of the matching policy." |

How we know the prototype is the same model as our results (one sentence):
"The matching and trust code is ported from the simulator and checked by golden parity tests. It reproduces 2,342
recorded cases and 17 complete 180-day simulated runs exactly, day by day. There are over 200 automated tests."
(`backend/tests/golden/`, `docs/TESTING.md` §2.)

**Parser accuracy.** Say only one of these:
- If the hand-written test set has been frozen and scored: quote the line from `scripts/out/parser_eval_test_*.md`
  as filled into `docs/REPORT_INSERTS.md` §6.
- Otherwise: "The parser is built, with a person checking every draft before stock changes. Its accuracy test set and
  target are fixed in advance, and the evaluation is the next step." **Do not quote the preview numbers.**

## 4. Limits and next steps (closing, about 1 minute)

- Simulated data, mock channel, not clinically validated; demo users, not real authentication.
- The outcome numbers come from the simulator, not from the field. The −37% cut in families searching is simulated,
  and it missed our own −40% target (G1 failed; `sim_v3/RESULTS_v3.md` §1).
- Next: a transfusion-specialist review (seven questions ready), parser evaluation, then a 5–8 centre pilot via SBTC.

## 5. Likely questions

The five hardest, with answers, are in `docs/DEMO_SCRIPT.md` §4. Short answers for the questions this round adds:

- **"What did you build since Round 1?"** "The whole working system you just saw. Round 1 was a simulator and a static
  mock-up."
- **"Is it deployed?"** "No. It runs locally on simulated data. Deployment comes after the pilot agreement."
- **"How do you know the code matches your simulation?"** The parity sentence in §3.
- **"Can it take real WhatsApp messages?"** "Not yet. Business verification takes longer than this round, so a mock
  channel feeds the same parser a real webhook would."
- **"What does the LLM do?"** "It only extracts fields from a message. Our code resolves dates and raises every check,
  and a person approves each draft. Without a key it falls back to rules, which is what you saw."
