// ---------------- Slide 3: Solution & Innovation (Round 2: "Built" box replaces "not built yet") ----------------
{
  const s = pres.addSlide();
  s.background = { path: BG(3) };
  heading(s, "Proposed Solution & Innovation", 60, 115, 900);
  sub(s, "What makes it different", 60, 225);
  body(s, [t("None of the tools we found describes treating stock listings as possibly stale: they "), b("list stock"), t(" or "), b("move near-expiry units"),
           t(". RaktSetu treats every listing as possibly stale: it learns each centre's reliability, confirms before any courier leaves, and shows families a High / Medium / Low likelihood band.")],
       60, 259, 640, 80, 16.5);
  sub(s, "Core mechanism", 60, 354);
  body(s, [t("1  Centres post near-expiry units and shortfalls (form, or message via a mock channel).", { breakLine: true }),
           t("2  Trust: Beta(2,1) reliability per centre for listings 0, 1, 2+ days old.", { breakLine: true }),
           t("3  Greedy matcher: units expiring ≤2 days, strict ABO/RhD, one-hop rule, ≥12 h margin.", { breakLine: true }),
           t("4  Sending centre confirms; medical officer approves; 20–24 °C box recorded.")],
       60, 387, 660, 92, 15.5, { paraSpaceAfter: 1 });
  sub(s, "Built for Round 2", 60, 483);
  body(s, [b("A working prototype on simulated data: "),
           t("FastAPI backend, browser UI and a message parser with a human check. The trust and matcher code reproduce our simulator's decisions exactly (parity-tested). Mock channel · demo users · not clinically validated.")],
       60, 517, 640, 80, 16.5);

  s.addText("Closest existing solutions vs RaktSetu", { x: P(745), y: P(212), w: P(470), h: P(24), fontFace: BODY, bold: true, fontSize: 16, color: WHITE, margin: 0, isTextBox: true });
  const hdr = (x) => ({ text: x, options: { bold: true, color: GREEN, fontSize: 11.5, fill: { color: "0D2316" }, valign: "middle" } });
  const c = (x, col = WHITE, bold = false) => ({ text: x, options: { color: col, fontSize: 11.5, bold, valign: "middle" } });
  const Y = (x = "Yes") => c(x, GREEN, true), N = (x = "No") => c(x, "C98A82");
  const rows = [
    [hdr("Solution"), hdr("Matches near-expiry units across centres"), hdr("Handles stale or wrong stock data"), hdr("Public 'how likely in stock'")],
    [c("e-RaktKosh (India)"), N("Not found"), c("Public pages show 'last updated' only", "D9C27A"), c("Raw count", "D9C27A")],
    [c("Phone helplines (e.g. Sankalp, Karnataka)"), c("Patient → bank, not bank → bank", "D9C27A"), c("Not described", "D9C27A"), c("Via helpline", "D9C27A")],
    [c("BloodMove (Adelaide, as reported)"), Y(), N("Not described"), N()],
    [c("Zhang et al., Oper. Res. 2023"), Y("Yes (2 hospitals)"), N("Not described (abstract)"), N()],
    [c("RaktSetu", GREEN, true), Y(), Y("Yes: learned trust + confirm"), Y("Yes: likelihood band")],
  ];
  s.addTable(rows, { x: P(745), y: P(242), w: P(470), colW: [P(122), P(116), P(118), P(114)], fontFace: BODY,
    border: { type: "solid", color: "24402E", pt: 0.75 }, fill: { color: "07140C" }, margin: 0.05, rowH: P(34) });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: P(745), y: P(470), w: P(470), h: P(122), fill: { color: CARD2, transparency: 5 },
    line: { color: AMBER, width: 1 }, rectRadius: 0.08 });
  s.addText([b("Simulated, strict blood-group matching: ", { color: AMBER }),
             t("a naive matcher that trusts stale listings sent "), b(`${n("S1.C_raw.wasted")}–${n("S2.C_raw.wasted")} wasted courier trips`, { color: AMBER }),
             t(` per 150 days and, with poor data, left more patients unserved than no platform (${n("S2.C_raw.unserved_pct")}% vs ${n("S2.A_raw.unserved_pct")}%). Confirming first (~${n("S1.E_trust.calls_per_day")} calls a day) cut that to ${n("S2.E_raw.unserved_pct")}%; adding trust ranking cut failed family visits a further ${n("S1.finder_fvpf_cut_pct")}–${n("S2.finder_fvpf_cut_pct")}%.`)],
    { x: P(760), y: P(478), w: P(440), h: P(106), fontFace: BODY, fontSize: 14.5, color: WHITE, margin: 0, valign: "middle", isTextBox: true });
  footnote(s, "Sources: e-RaktKosh public pages; Sankalp India Foundation helpline; Nat. Blood Authority (AU) BloodMove case study (as reported; not re-opened); Zhang, Ayer, White, Bodeker & Roback, Oper. Res. 71(5), 2023; Team Trex simulator v3 (realistic / poor stock data, 300 paired runs each). 'Not found' = not found in our search.", 606, 60, 1150);
  s.addNotes("Round 2 change: the prototype is now built (raktsetu-app). It runs end to end on simulated data: list, match, confirm, approve, dispatch, deliver, plus a public finder and a message parser whose drafts a person checks. The trust and matcher code is ported from the simulator and golden parity tests show it reproduces the simulator's decisions exactly: 2,342 recorded cases and 17 complete 180-day runs, day by day. Input is a mock channel (typed or pasted messages), not WhatsApp; users are demo roles, not real authentication; the matching policy is not clinically validated. The trust estimate is a Beta(2,1) count per centre and listing-age bucket (0, 1, 2+ days); in the prototype it learns from confirmations; there is no decay curve. The matcher is greedy; an exact min-cost-flow matcher changed unserved patients by at most 0.04 percentage points in simulation. The ≥12 h on-arrival margin is our own safety choice, not a regulation.");
}

// ---------------- Slide 4: Architecture & Tech Stack (Round 2: built vs planned) ----------------
{
  const s = pres.addSlide();
  s.background = { path: BG(4) };
  heading(s, "System Architecture & Tech Stack", 70, 90, 900);
  s.addText("TECH STACK", { x: P(46), y: P(168), w: P(200), h: P(22), fontFace: HEAD, bold: true, fontSize: 14, color: "55C226", charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("built for Round 2 · runs locally on simulated data", { x: P(196), y: P(170), w: P(260), h: P(20), fontFace: BODY, italic: true, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  const built = (x) => ({ text: "Built: ", options: { bold: true, color: GREEN } });
  const planned = (x = "Planned: ") => ({ text: x, options: { bold: true, color: AMBER } });
  const boxes = [
    [214, "Frontend", [built(), t("React + Vite: board, transfer cards, message inbox, public finder")]],
    [292, "Backend", [built(), t("Python FastAPI · trust estimate · greedy matcher · workflow · audit log")]],
    [369, "Database", [built(), t("SQLite via SQLAlchemy. "), planned(), t("PostgreSQL (same models)")]],
    [451, "AI / APIs", [built(), t("Beta-Bernoulli trust · greedy matcher · parser with human check. "), planned(), t("WhatsApp Cloud API")]],
    [533, "Hosting / DevOps", [planned(), t("Docker · India-region cloud · CI. Today: one local process.")]],
  ];
  boxes.forEach(([y, lab, runs]) => {
    s.addText(lab.toUpperCase(), { x: P(62), y: P(y), w: P(350), h: P(18), fontFace: HEAD, bold: true, fontSize: 12, color: GREEN, charSpacing: 1, margin: 0, isTextBox: true });
    s.addText(runs, { x: P(62), y: P(y + 19), w: P(350), h: P(40), fontFace: BODY, fontSize: 13, color: WHITE, margin: 0, valign: "top", isTextBox: true });
  });
  const box = (x, y, w, h, title, text, col = LINE, fill = CARD, titleCol = GREEN) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: P(x), y: P(y), w: P(w), h: P(h), fill: { color: fill, transparency: 8 }, line: { color: col, width: 1.25, dashType: col === DIM ? "dash" : "solid" }, rectRadius: 0.06 });
    s.addText([{ text: title, options: { bold: true, color: titleCol, fontSize: 13.5, breakLine: true } }, { text, options: { color: titleCol === GREEN ? WHITE : MUTED, fontSize: 12 } }],
      { x: P(x + 8), y: P(y + 4), w: P(w - 16), h: P(h - 8), fontFace: BODY, margin: 0, valign: "middle", isTextBox: true });
  };
  const plannedBox = (x, y, w, h, title, text) => box(x, y, w, h, title, text, DIM, CARD, MUTED);
  const arrow = (x1, y1, x2, y2, col = GREEN) => s.addShape(pres.shapes.LINE, { x: P(Math.min(x1, x2)), y: P(Math.min(y1, y2)), w: P(Math.abs(x2 - x1)) || 0.001, h: P(Math.abs(y2 - y1)) || 0.001,
    flipH: x2 < x1, flipV: y2 < y1, line: { color: col, width: 1.75, endArrowType: "triangle" } });
  s.addText([{ text: "How a near-expiry platelet unit flows", options: { bold: true, color: WHITE } },
             { text: "   dashed grey = planned", options: { italic: true, color: MUTED, fontSize: 12 } }],
    { x: P(470), y: P(168), w: P(560), h: P(22), fontFace: BODY, fontSize: 15, margin: 0, isTextBox: true });
  box(470, 200, 200, 74, "Blood centres", "Near-expiry units + shortfalls by form or message (mock channel)");
  plannedBox(470, 290, 200, 60, "e-RaktKosh", "Public stock as a prior");
  box(470, 366, 200, 74, "Outcomes", "Confirmations update trust; every step logged", AMBER);
  const ex = 720, ew = 250;
  box(ex, 200, ew, 56, "1  Ingest & parse", "Rules or Claude API → draft → human check");
  box(ex, 270, ew, 56, "2  Trust estimate", "Beta(2,1) per centre × listing age 0/1/2+ days");
  box(ex, 340, ew, 66, "3  Matcher (greedy)", "Units expiring ≤2 days → requests; strict ABO/RhD, one-hop rule, ≥12 h margin");
  box(ex, 420, ew, 56, "4  Confirm & approve", "Sending centre confirms · only a medical officer approves");
  box(ex, 490, ew, 56, "5  Dispatch & audit", "20–24 °C box recorded · audit log · transport estimate");
  box(1015, 200, 195, 74, "Coordinator dashboard", "Board, trust bands, explainable matches");
  box(1015, 290, 195, 74, "Public platelet finder", "High / Medium / Low likelihood band");
  plannedBox(1015, 380, 195, 74, "SBTC / FDA report", "Wastage avoided, reporting reliability");
  arrow(670, 237, 720, 228); arrow(670, 320, 720, 298, DIM); arrow(670, 403, 720, 300, AMBER);
  [256, 326, 406, 476].forEach((y) => arrow(ex + ew / 2, y, ex + ew / 2, y + 14));
  arrow(970, 228, 1015, 237); arrow(970, 298, 1015, 327); arrow(970, 518, 1015, 417, DIM);
  s.addText("Medical officer approves every transfer · no patient data stored · unit IDs not linkable to donors", { x: P(470), y: P(560), w: P(740), h: P(22),
    fontFace: BODY, italic: true, fontSize: 13, color: MUTED, margin: 0, isTextBox: true });
  footnote(s, `Rules: D&C Rules 122P(xiv)–(xv) (transfer allowed; recipient may pass units only to a storage centre or patient); platelets 5 days at 20–24 °C (DGHS/NBTC Technical Manual 2023). The ≥12 h margin is our choice. Greedy matcher kept: an exact min-cost-flow matcher changed unserved % by ≤${n("matcher.max_unserved_diff_pp")} pp (simulated).`, 600, 470, 740, 36);
  s.addNotes("Round 2: the stack is built and runs as one local process on simulated data. Deviations from the Round 1 plan, chosen for a 3-day build and a reliable demo: SQLite instead of PostgreSQL (same SQLAlchemy models, a configuration change to switch); a mock message channel instead of the WhatsApp Cloud API (business verification could not be done in time); no Docker, cloud hosting or CI yet; e-RaktKosh and the SBTC/FDA report are planned. The parser uses rules, or the Claude API when a key is set; the LLM only extracts fields and our code resolves dates and raises every check; a person approves each draft. The LLM path has been tested only with a fake client so far. Trust: Beta(2,1) count per centre and listing-age bucket, p = alpha/(alpha+beta), no decay; the prototype learns from confirmations. Matcher: greedy, ported from the simulator and parity-tested.");
}

// ---------------- Slide 5: Key Features & UI/UX (Round 2: real app screenshot) ----------------
{
  const s = pres.addSlide();
  s.background = { path: BG(5) };
  heading(s, "Key Features & UI/UX", 68, 115, 700);
  s.addImage({ path: path.join(__dirname, "assets", "app_board.png"), x: P(60), y: P(190), w: P(720), h: P(405),
    altText: "RaktSetu working prototype on simulated data: coordinator board with centre stock and report-trust bands, two suggested transfers with their reasons, and the matcher panel." });
  s.addShape(pres.shapes.RECTANGLE, { x: P(60), y: P(190), w: P(720), h: P(405), fill: { type: "none" }, line: { color: LINE, width: 1 } });
  s.addText("Working prototype on simulated data · coordinator board after a strict match run · mock channel · not clinically validated", { x: P(60), y: P(598), w: P(720), h: P(18), fontFace: BODY, italic: true, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  const feats = [
    ["Near-expiry board", "built", "every unit expiring within 2 days, city-wide, with listing age"],
    ["Report-trust bands", "built", "learned from confirmations; stale listings stand out"],
    ["Explainable matches", "built", "why this unit; ABO/RhD, one-hop, 12-h checks computed"],
    ["Confirm before dispatch", "built", "staff confirm what is there; only a medical officer can approve"],
    ["Public platelet finder", "built", `bands, not %: raw estimate miscalibrated (ECE ${n("calib.S1.ece_trust")}); High/Med/Low in stock ${n("bands.S1.High")}/${n("bands.S1.Medium")}/${n("bands.S1.Low")}% (sim.)`],
    ["Low-effort input", "built, mock channel", "English + Hinglish; a person checks every draft"],
    ["Regulator view", "planned", "wastage avoided and reporting reliability per centre"],
  ];
  feats.forEach(([h, status, d], i) => {
    const y = 192 + i * 58;
    const done = status !== "planned";
    s.addShape(pres.shapes.OVAL, { x: P(812), y: P(y + 4), w: P(26), h: P(26), fill: { color: done ? GREEN : CARD }, line: { color: done ? GREEN : DIM } });
    s.addText(String(i + 1), { x: P(812), y: P(y + 4), w: P(26), h: P(26), fontFace: BODY, bold: true, fontSize: 13, color: done ? "06110B" : MUTED, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: h, options: { bold: true, color: done ? GREEN : MUTED } },
               { text: `  ${status}`, options: { italic: true, color: done ? MUTED : AMBER, fontSize: 12, breakLine: true } },
               { text: d, options: { color: WHITE, fontSize: 14 } }],
      { x: P(850), y: P(y), w: P(370), h: P(52), fontFace: BODY, fontSize: 15.5, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes("Round 2: this is the working app, not a mock-up: a real screenshot of the coordinator board on the seeded, fictional 8-centre city, after the strict matcher suggested two transfers. Every value on it is computed by the backend. We can show it live: confirm, the refused staff approval, medical-officer approval, the trust update after a partial confirmation, the message inbox and the public finder. The finder shows High/Medium/Low bands because the raw reliability estimate is not well calibrated (underconfident below about 0.6); on held-out simulated runs, High-band visits found stock 87% of the time, Medium 71%, Low 54%. Messages come through a mock channel (typed or pasted); Hindi and Marathi parsing and the regulator view are planned.");
}

// ---------------- Slide 6: Roadmap & Scope (Round 2: what was built) ----------------
{
  const s = pres.addSlide();
  s.background = { path: BG(6) };
  heading(s, "Implementation Roadmap & Scope", 61, 102, 900);
  s.addText("WHAT WE TESTED IN SIMULATION, WHAT WE BUILT FOR ROUND 2, AND WHAT COMES NEXT", { x: P(61), y: P(158), w: P(950), h: P(24), fontFace: HEAD, bold: true, fontSize: 12.5, color: WHITE, charSpacing: 1, margin: 0, isTextBox: true });
  const cols = [
    ["ROUND 1: SIMULATION", GREEN, [
      "Simulator: 8-centre city, platelets last 5 days, ABO/RhD groups (Mumbai donor mix), 300 paired runs per arm",
      "Pre-registered v3 rules: 2 of 4 passed; G1 and G2 FAILED (chart)",
      "Sensitivity grid, 4 unusual error patterns, calibration check"]],
    ["ROUND 2: BUILT", GREEN, [
      "Working prototype on simulated data: list → match → confirm → approve → dispatch → deliver",
      "Trust + matcher code reproduce the simulator exactly (17 whole runs; 200+ automated tests)",
      "Message parser with human check (mock channel); public finder with bands",
      "Still open: specialist review; parser accuracy test"]],
    ["BEYOND THE HACKATHON", "8FD3FF", [
      "Transfusion-specialist review of the matching policy",
      "3-month pilot with 5–8 Pune centres via SBTC; measure real outdates and report accuracy",
      "RhD-negative reserve; real WhatsApp channel",
      "e-RaktKosh / ABDM link; red cells and plasma"]],
  ];
  cols.forEach(([title, col, items], i) => {
    const x = 61 + i * 225, w = 212;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: P(x), y: P(198), w: P(w), h: P(400), fill: { color: CARD, transparency: 8 }, line: { color: col, width: 1.25 }, rectRadius: 0.07 });
    s.addText(title, { x: P(x + 12), y: P(208), w: P(w - 24), h: P(22), fontFace: BODY, bold: true, fontSize: 14, color: col, margin: 0, isTextBox: true });
    s.addText(items.map((it, k) => ({ text: it, options: { bullet: { indent: 12 }, breakLine: k < items.length - 1, color: it.startsWith("Still open") ? AMBER : WHITE } })),
      { x: P(x + 12), y: P(238), w: P(w - 22), h: P(352), fontFace: BODY, fontSize: 15, color: WHITE, margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true });
  });
  s.addText("Simulator (strict ABO/RhD): families sent to search", { x: P(745), y: P(198), w: P(470), h: P(22), fontFace: BODY, bold: true, fontSize: 16, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Per day, 8-centre city · realistic vs poor stock-data quality · 300 paired runs", { x: P(745), y: P(220), w: P(470), h: P(18), fontFace: BODY, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  const labs = ["No platform (today)", "Naive matcher on stale data", "RaktSetu"];
  s.addChart(pres.charts.BAR, [
      { name: "Realistic data", labels: labs, values: ["S1.A_raw", "S1.C_raw", "S1.E_trust"].map((k) => NUM[k + ".families_per_day"].value) },
      { name: "Poor data", labels: labs, values: ["S2.A_raw", "S2.C_raw", "S2.E_trust"].map((k) => NUM[k + ".families_per_day"].value) }],
    { x: P(745), y: P(240), w: P(470), h: P(222), barDir: "col", barGrouping: "clustered", chartColors: [GREEN, AMBER],
      catAxisLabelColor: "DDEEE1", catAxisLabelFontSize: 12, catAxisLabelFontFace: BODY, valAxisHidden: true,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 16.5,
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: WHITE, dataLabelFontSize: 13, dataLabelFontFace: BODY, dataLabelFormatCode: "0.00",
      barGapWidthPct: 55, showLegend: true, legendPos: "t", legendColor: "DDEEE1", legendFontSize: 12, legendFontFace: BODY,
      plotArea: { fill: { color: "000000", transparency: 100 } } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: P(745), y: P(470), w: P(470), h: P(128), fill: { color: CARD2, transparency: 5 }, line: { color: RED, width: 1 }, rectRadius: 0.08 });
  s.addText([b("Target missed: ", { color: RED }), t(`families −${n("S1.R_fam")}% / −${n("S2.R_fam")}% vs ≥40% (G1 FAIL); failed visits −${n("S1.R_fail")}% / −${n("S2.R_fail")}% vs ≥80% (G2 FAIL). Blood groups keep ${n("S1.surviving_pct")}–${n("S2.surviving_pct")}% of the single-group effect. `, { breakLine: true }),
             b("What drives it: "), t(`coordination plus confirmation alone (~${n("S1.E_trust.calls_per_day")} calls/day): unserved ${n("S1.A_raw.unserved_pct")}% → ${n("S1.E_raw.unserved_pct")}% (poor data ${n("S2.A_raw.unserved_pct")}% → ${n("S2.E_raw.unserved_pct")}%). Adding the trust finder gives ${n("S1.E_trust.unserved_pct")}% (${n("S2.E_trust.unserved_pct")}%) and cuts failed visits per family by ${n("S1.finder_fvpf_cut_pct")}–${n("S2.finder_fvpf_cut_pct")}%.`)],
    { x: P(760), y: P(476), w: P(440), h: P(116), fontFace: BODY, fontSize: 13.5, color: WHITE, margin: 0, valign: "middle", isTextBox: true });
  footnote(s, "One family per platelet request a hospital cannot fill. Simulated; data-error rates assumed (no published Indian figure). Pre-registration, 95% CIs and all v3 results: sim_v3/RESULTS_v3.md. Prototype test counts: raktsetu-app, 17 Oct 2026.", 606, 61, 1080);
  s.addNotes("Round 2 column, all built and runnable: the end-to-end workflow on simulated data; the trust and matcher code ported from the simulator, with golden parity tests reproducing 2,342 recorded cases and 17 complete 180-day simulated runs exactly; over 200 automated tests in total (core, parity, API, claims audit). Still open: a transfusion specialist has not yet reviewed the matching policy, and the parser's accuracy test (a frozen synthetic set, partly hand-written) has not been scored. The chart and the red box are unchanged simulator results: G1 (families sent to search cut by at least 40%) and G2 (failed visits cut by at least 80%) FAILED in both scenarios; G3 and G4 PASSED. About half of the gap to the single-group result comes from RhD-negative groups, which the par levels never request (RESULTS_v3.md).");
}

