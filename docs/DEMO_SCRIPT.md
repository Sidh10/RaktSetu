# Demo script (5 minutes)

Status: **draft, labels checked against the built UI on 16 Oct** (steps 1–6 and 8 walked through in the browser). Step 7 (mock-channel paste) was walked through on 16 Oct as well.
The exact suggestions below are **targets for the seed** and are enforced by `test_demo_seed_contract`; if the seed
changes, this script changes with it.

Works **live** (presenter clicks) and **recorded** (same clicks, voice-over; record at 1080p, 125% browser zoom).
Paths are relative to `RaktSetu_simulator_and_prototype/` unless they start with `raktsetu-app/`.

## 0. Setup (before the slot)
- `make build-web` (once), `make seed` (demo clock = today 09:00 IST, ADR-013), `make api`, browser at `http://localhost:8000/#/board`.
- Tab 1: app as **Coordinator**. Tab 2: **Public finder** (private window, no role).
- Parser mode `auto` if a key is set and the network is up, else `rules`. Both work.
- Pre-demo checklist done (`TESTING.md` §6).

## 1. Seeded demo city (all fictional, labelled simulated)

| Centre | Kind | Seeded for the demo | Band |
|---|---|---|---|
| Centre A · Medical college | hospital | open shortfall: 2 × B+ RDP | High |
| Centre C · Cancer hospital | hospital | open shortfall: 3 × O+ RDP | High |
| Centre F · Regional centre | collection | O+ RDP near expiry, posted today; target offer 2 × O+ | High |
| Centre G · Charitable centre | collection | B+ RDP near expiry, **posted 2 days ago**; target offer 2 × B+ | Low |
| Centre H · Camp-based centre | collection | 1 × O+ unit expiring tonight; transport to C seeded at 180 min → fails the 12-h margin | Medium |
| Centre B, D, E | hospitals | background stock; one unit at D marked "received by transfer" | mixed |

## 2. Script

| Time | Do (exact clicks) | Say |
|---|---|---|
| 0:00 | Show the board as **Coordinator**. Point at the banner. | "This is RaktSetu running end to end on **simulated data**. The backend, matcher, trust model and approval flow are real code; the centres, stock and people are fictional, the message channel is a **mock**, and the matching rules are **not clinically validated** yet." |
| 0:25 | Point at the centre table: *Listed*, *Expires ≤ 2 days*, *Last update*, *Report trust* bands. Hover Centre G's "2 days ago". | "Every listing may be stale. Centre G last updated two days ago, and its confirmations have often come up short, so its report-trust band is Low." |
| 0:45 | In the **Run matcher** panel keep **Strict: ABO/RhD-identical (default)** → **Run**. Two cards appear: *F → C, 2 × O+* and *G → A, 2 × B+*. Point at the "Not matched" note for Centre H. | "Greedy matcher, strict blood groups, one-hop rule, near-expiry surplus only. Centre H's unit is excluded: with a 3-hour trip it would arrive with under 12 hours left, our safety margin." |
| 1:15 | Open card **F → C**. Read the *Why* line. Click **Request confirmation**. | "No courier moves on a listing alone. We ask the sending centre first." |
| 1:30 | **Acting as** → **Staff, Centre F** → card shows *Units actually available 2 of 2* → **Confirm**. | "Centre F confirms both units." |
| 1:45 | Still as Staff F, click **Approve dispatch** → red toast "Approve: refused (403 forbidden_role)". | "The rule is enforced in the backend: staff cannot approve." |
| 1:55 | **Acting as** → **Medical officer, Centre F** → **Approve dispatch**. Tick *Validated 20–24 °C transport box used* → **Dispatch**. | "A medical officer approves every transfer. The 12-hour margin is checked again at approval and dispatch." |
| 2:15 | **Acting as** → **Staff, Centre C** → **Mark delivered**. The centre table shows Centre C · *2 received (never re-offered)*. | "Delivered units can't be offered again: the one-hop rule from Drugs & Cosmetics Rule 122P." |
| 2:35 | **Acting as** → **Coordinator** → card **Centre G → Centre A** → **Request confirmation**. Switch to **Staff, Centre G** → set *Units actually available* to **1** → **Confirm**. The toast shows the trust change. | "Centre G listed two, but only one is really there. That's the stale-data problem." |
| 2:55 | **Acting as** → **Coordinator** → **Report trust** tab → Centre G, *2+ days old · current*: α 6, β 7, 1 confirmation. Card shows *Confirmed 1 of 2*; Centre A's shortfall shows 1 still open. | "Every confirmation teaches the trust model: a Beta(2,1) estimate per centre and listing age. The remaining need reopens for the next run." |
| 3:15 | (Optional if time) MO G approves the 1 unit. | — |
| 3:25 | **Acting as** → **Staff, Centre H** → **Message inbox (mock channel)** tab → click the sample `C-H · Centre H: O+ RDP 2 unit kal expire, B+ 1` → **Parse into a draft**. | "Busy staff post by message. This is a **mock** WhatsApp channel; the text goes to the parser." |
| 3:45 | Draft #1 shows two rows: O+ 2 expiring 17 Oct with an amber "relative date resolved: please check", and B+ 1 with a red "expiry missing". Set B+ expiry to 18 Oct → **Save review** → **Commit**. Toast: "3 unit(s) added to the listing (listing age unchanged)". | "The LLM, or the offline rule parser, only drafts. A human checks every draft before stock changes." |
| 4:10 | Tab 2 (**Acting as: Public (no login)**, only the finder tab exists): **B+**, **Random donor (RDP)** → **Search**. Results show bands and "Call before travelling". | "Families see where B+ platelets are listed, ranked by trust, as High, Medium or Low. Never a percentage. In our simulation, High-band centres had stock on 87% of visits and Low ones on 54%, so we always say call first." |
| 4:35 | Back to Coordinator → **Audit log** tab (or **History** on a card). | "Every step is logged: who, which role, when." |
| 4:45 | Close on a slide or the terminal showing `make test` green. | "The trust and matcher code reproduces our simulator's decisions exactly, checked by golden parity tests. Next: specialist review of the matching policy and a pilot with real centres." |

Recorded version: same steps; cut the waiting; put the labels "simulated data · mock channel · not clinically
validated" on the title card and the end card.

Numbers spoken in the script and their sources: 87% / 54% band hit rates (S1, `sim_v3/results/finder_bands.json`,
`RESULTS_v3.md` §11). The parity sentence may be said only after the parity suite passes (`CLAIMS_AND_LIMITS.md` §2).

## 3. If something breaks on stage
| Failure | Do |
|---|---|
| LLM call slow / fails | The draft says "parsed by rules"; carry on. Say "it falls back to the offline parser." |
| UI error on a card | Show the same step in `/docs` (OpenAPI), then continue. |
| Laptop / projector failure | Play the recorded video from USB. |
| Data in a strange state | `make seed` takes ~2 s; restart from step 0:45. |

## 4. The five hardest jury questions

**Q1. "Isn't this still a simulation? What is actually real?"**
The software is real and runs end to end: database, API, matcher, trust updates, state machine with role checks,
audit, finder and parser. The **data** is simulated and the people are role-played; the channel is a mock. The
outcome numbers we quote still come from the simulator, and we label them that way (`RESULTS_v3.md`). What changed
since Round 1 is that the jury's "static UI" is now a working system, and its decision logic is tested against the
simulator so the demo and the results describe the same model. What we don't have yet is real data; that needs a pilot.

**Q2. "Your own ablation says the phone confirmation does most of the work. Why do you need the trust model?"**
Correct, and we say so: in simulation, coordination plus confirmation drives most of the gain; trust ranking adds a
smaller but consistent gain, cutting failed family visits per family by a further 17–18% (`RESULTS_v3.md` §1, §3).
The trust model's job is the **public** side. Families don't get a confirmation call, so the finder needs some estimate
of which listings to believe. It is also what lets us show a stale listing as Low instead of hiding it. We dropped the
idea of skipping calls based on trust because that arm did worse (`RESULTS_v3.md` §3).

**Q3. "Two of your four pre-registered targets failed. Why should we believe this works?"**
We pre-registered the targets before running, and G1 (families −40%) and G2 (failed visits −80%) failed once blood
groups were added: we got −37% and −66% in the realistic case (`RESULTS_v3.md` §1). We report that rather than retune.
G3 (trust beats raw listing) and G4 (still beats no platform at 3× error rates) passed, and unserved patients fell
from 4.2% to 2.2% in simulation. The honest claim is "a real but smaller effect than we hoped, in a model"; the pilot is
how to find out the real size.

**Q4. "How accurate is the parser on real WhatsApp messages? And why isn't WhatsApp connected?"**
We haven't measured it on real messages; we have no real messages. We measured it on a synthetic test set of 100
English and Hinglish messages, at least 60 of them hand-written by us, frozen before scoring: [quote item accuracy,
critical errors and human-check rate from the eval output, only once it exists]. That is why a human checks every
draft. WhatsApp's business API needs verification we could not complete in three days, so we built a mock channel
that feeds the same parser a real webhook would.

**Q5. "Is the blood-group matching clinically safe? Who is responsible if a wrong unit is sent?"**
It is not validated yet, and every screen says so. By default it matches ABO- and RhD-identical units only, which is
the DGHS/NBTC 2023 manual's default for platelets (§5.3). Looser policies need a medical officer's acknowledgement and
flag anti-D cases. The software never dispatches anything: a medical officer approves every transfer and the sending
centre confirms the actual units, so responsibility stays where it is today. We have seven specific questions ready for
a transfusion specialist (`MATCHING_POLICY.md` §8). The 12-hour margin is our own choice, not a regulation.

### Backup answers
- **"Won't centres game the trust score?"** Trust comes from confirmed outcomes, not from what centres claim. In
  simulation, a centre posting three phantom units daily did not break the result (`RESULTS_v3.md` §5, "gaming").
- **"RhD-negative patients?"** In the model they stay largely unserved under strict matching (`RESULTS_v3.md` §2);
  explicit shortfall posts in the prototype let centres request them, and a reserve for RhD-negative units is on the
  roadmap (deck slide 6).
- **"Why greedy and not an optimiser?"** An exact min-cost-flow matcher changed unserved % by at most 0.04 pp in
  simulation (`RESULTS_v3.md` §10).
