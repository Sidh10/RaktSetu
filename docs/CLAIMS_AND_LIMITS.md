# Claims and limits

What the Round 2 demo, report and UI may say, and what they may not. When in doubt, say less. Paths are relative to
`RaktSetu_simulator_and_prototype/`.

## 1. Required labels

| Label | Where it must appear |
|---|---|
| **"Simulated data"** | banner on every page; any screen showing centres, stock, trust; every simulator number (with its source file) |
| **"Mock channel"** | the parser inbox, the paste box, the webhook response, any slide or voice-over mentioning WhatsApp/SMS |
| **"Not clinically validated"** | banner; matching-policy panel; transfer cards using standard/relaxed; README; report |
| "Demo users · not real authentication" | header bar next to the role switcher |
| "Call before travelling" | every public finder result |
| "Parsed by LLM / rules · human check required" | every parser draft |

## 2. The prototype may claim

- It runs **end to end** on simulated data: list stock → match → confirm → approve → dispatch → deliver, with an audit
  trail, a public finder and a message parser with human check.
- Its matching and trust code **reproduces the simulator's decisions exactly** on fixed inputs and on whole dev-seed
  runs (only once the parity suite passes; quote the test count).
- It enforces, in code: medical-officer approval before dispatch; the one-hop rule; the team-chosen 12-h margin; strict
  ABO/RhD by default; no patient fields; opaque unit IDs.
- The parser's accuracy **on the synthetic test set**, with CI, critical error rate and human-check rate (only once
  measured on the frozen split).
- The finder shows likelihood **bands**; in simulation, High / Medium / Low centres had stock on 87% / 71% / 54% of
  visits (S1, held-out seeds; `sim_v3/results/finder_bands.json`). Always say "in simulation".

## 3. Simulator numbers that may be quoted (always "simulated", always with the source)

| Claim | Value | Source |
|---|---|---|
| Families sent to search, RaktSetu vs no platform | −37% (13.52 → 8.55/day), S1; target −40% **FAILED (G1)** | `sim_v3/RESULTS_v3.md` §1–2 |
| Failed visits to empty centres | −66% (4.89 → 1.68/day); target −80% **FAILED (G2)** | `RESULTS_v3.md` §1; deck slide 7 |
| Patients left unserved | 4.16% → 2.20% (S1); 7.70% → 2.49% (S2) | `RESULTS_v3.md` §2 |
| Confirmation calls | ~3.7 per day (3.66 S1, 3.80 S2) | `RESULTS_v3.md` §2, §6 |
| Calls that find less stock than listed | 11.5% (S1), 17.3% (S2) | `RESULTS_v3.md` §6 |
| Wasted courier trips | 0 **by design** (every transfer confirmed); naive matcher 130–201 per 150 days | `RESULTS_v3.md` §2 |
| What drives the gain | coordination + confirmation; trust ranking adds a smaller gain (failed visits per family −17 to −18%) | `RESULTS_v3.md` §1, §3 |
| Greedy vs exact matcher | exact changed unserved % by ≤ 0.04 pp | `RESULTS_v3.md` §10 |
| RhD-negative patients | largely unserved under strict matching in the model | `RESULTS_v3.md` §2 |

Every one of these rests on **assumed** data-error rates in a synthetic 8-centre city (`RESULTS_v3.md`, header).

## 4. Never claim

| Do not say | Say instead / why |
|---|---|
| "clinically validated", "safe", "approved by a specialist / NBTC / FDA" | "encodes DGHS/NBTC 2023 §5.3 and SNBTS guidance; not yet reviewed by a specialist" |
| "integrated with WhatsApp", "live WhatsApp", "SMS gateway", "real-time messaging" | "mock channel; the same parser would sit behind a WhatsApp webhook" |
| any percentage or probability for a centre in the public finder | band + "call before travelling"; the raw estimate is underconfident below ~0.6 (`RESULTS_v3.md` §8) |
| "reduces wastage by X%", "saves N units", any outcome as measured | "in simulation …" + source; the prototype measures nothing real |
| "optimal matching", "OR-Tools" | "greedy matcher; an exact matcher changed unserved % by ≤ 0.04 pp in simulation" |
| "trust decays over time", "half-life" | "Beta(2,1) per centre for listings 0, 1, 2+ days old; no decay" (`MODEL_SPEC_v3.md` §5) |
| "the parser is X% accurate" without "on our synthetic test set" | scope it, give the CI and the human-check rate |
| "secure", "authenticated", "HIPAA/DPDP compliant", "production-ready", "deployed" | "demo users; no real authentication; runs locally" |
| "the trust engine is what makes it work" | most of the simulated gain comes from coordination + confirmation (`RESULTS_v3.md` §3) |
| "G1/G2 passed", "met our targets" | "G1 and G2 failed; G3 and G4 passed" (`RESULTS_v3.md` §1) |
| "nearby centres run short" as fact | "our premise, not yet measured" (deck slide 2) |
| "real centres in Pune", any real hospital name | all centres are fictional |
| "the 12-hour rule is required by regulation" | "a margin we chose" (`PREREGISTRATION_v3.md`, Amendment 2) |
| "48 h" as the exact cut-off in the prototype | "expires within 2 days" (deviation D-10) |

## 5. Finder rule (non-negotiable)

The public finder shows **High / Medium / Low** only. No number in [0, 1], no `%`, no "chance". The simulator's
calibration check found the trust estimate underconfident below about 0.6 and beaten by a simple count-binned table on
Brier score, so it must not be shown as a probability without recalibration (`RESULTS_v3.md` §8). "Low" still meant
stock on about half of visits in simulation (`RESULTS_v3.md` §11), so the advice is always "call before travelling".
Enforced by `test_finder_response_has_no_probability`.
