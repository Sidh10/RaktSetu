# Round 2 deck

`out/RaktSetu_TeamTrex_CodeApex3_Round2.pptx` is the v3 deck with **slides 3–6 replaced** to show the built
prototype. Slides 1, 2, 7 and 8 are byte-identical to `out_v3/RaktSetu_TeamTrex_CodeApex3_v3.pptx` (checked on
17 Oct 2026). Every simulated number still comes from `deck_v3/deck_numbers.json`, read from the simulator folder,
which this build never modifies.

| Slide | What changed |
|---|---|
| 3 Solution | "The backend is not built yet" → **Built for Round 2**: working prototype on simulated data, parity-tested trust and matcher; mock channel · demo users · not clinically validated. Input wording: form or message via a mock channel; "≤2 days" units |
| 4 Architecture | Stack marked **Built** / **Planned** (SQLite now, PostgreSQL planned; WhatsApp Cloud API, Docker, cloud and CI planned). Planned flow boxes (e-RaktKosh, SBTC/FDA report) drawn dashed grey |
| 5 Features | v3 UI mock-up replaced by a **real screenshot** of the running app (`assets/app_board.png`, captured 17 Oct from the seeded demo); each feature labelled built or planned |
| 6 Roadmap | Columns: Round 1 simulation · **Round 2 built** (with "still open: specialist review; parser accuracy test") · beyond. The chart and the "Target missed" box are unchanged |

Rebuild (needs Node and the read-only `RaktSetu_simulator_and_prototype/` next to `raktsetu-app/`):

```bash
cd deck_r2
npm install                      # pptxgenjs 4.0.1, the v3 version
python splice.py                 # v3 builder + slides_3_to_6.js -> build_deck_r2.js (generated; don't edit it)
node build_deck_r2.js
python postprocess.py out/RaktSetu_TeamTrex_CodeApex3_Round2.pptx   # Orbitron small caps, as in v3
```

Edit slide text in `slides_3_to_6.js`; the claims audit test scans it. `out/*.pdf` and `out/render/` (PowerPoint
exports used for checking) are not committed.

**Font:** neither this deck nor the v3 deck embeds Orbitron, and this laptop does not have it installed, so headings
show a substitute font. To present with the intended look, install `deck_v3/fonts/Orbitron-Bold.ttf` (OFL licence)
on the presenting machine before opening the deck.
