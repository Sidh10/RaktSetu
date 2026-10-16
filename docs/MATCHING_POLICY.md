# Matching policy

> ⚠️ **Needs transfusion-specialist validation.** This policy encodes what the cited sources say and what the
> simulator assumed. **No transfusion-medicine specialist has reviewed it.** It is a prototype rule set on simulated
> data, **not clinical guidance**, and must not be used for real transfers until a specialist signs it off
> (`sim_v3/MODEL_SPEC_v3.md` §2; `sim_v3/STAGE2_NOTES.md`, "Matching policies and their sources").

Paths below are relative to `RaktSetu_simulator_and_prototype/`.

## 1. Sources (all opened and read during the simulator work)

| # | Source | Local copy | What we use from it |
|---|---|---|---|
| S1 | DGHS / NBTC, *Transfusion Medicine Technical Manual*, 3rd ed., 2023, ch. "Selection of component and testing", §5.3, p. 160 (Government of India) | `sim_v3/sources/DGHS_TMTM_2023_p160_sec5.3_excerpt.txt` | Platelets ABO and RhD type-specific "as far as possible"; in shortage any ABO/Rh group may be used if there is no visible red-cell contamination; SDP across the group barrier: reduce plasma or use additive solution; infants under one year get ABO-identical platelets. Does not address anti-D for platelets. |
| S2 | SNBTS, *Policy for Platelet Selection*, NATP CLIN 10 003 04 (2014), extracting BCSH 2003 | `sim_v3/sources/SNBTS_NATP_CLIN_10_003_04_platelet_selection.pdf` | ABO choice order (Table 1); group O platelets to non-O patients only as a last resort; RhD− platelets to RhD− patients where possible; anti-D for RhD− women of childbearing potential given RhD+ platelets. |
| S3 | Drugs & Cosmetics Rules 122P(xiv)–(xv), condition (xiv) inserted by G.S.R. 328(E), 3 Apr 2017 (read on Indian Kanoon) | not saved locally | Transfer between blood centres allowed; a recipient may not transfer further except to another blood storage centre or a patient (one-hop rule). Cited in `sim_v3/MODEL_SPEC_v3.md` §1 and the deck, slide 4. |
| S4 | Agrawal A et al., *Asian J Transfus Sci* 2014;8(2):121–125, Table 5 | `sim_v3/sources/agrawal2014_table5_regionwise.jpg` | West-region (Mumbai) ABO/RhD distribution, used only for seeded demand shares. |

Summary of S1 and S2 as recorded in `sim_v3/STAGE2_NOTES.md`. We did not re-read S2 for this document.

## 2. ABO/RhD policies

Groups are indexed as in the simulator: `O+, O-, A+, A-, B+, B-, AB+, AB-` (`raktsetu_sim_v3.py`, `GROUPS`).
The donor list for each recipient group is ordered; the position is the **tier** (0 = identical).

| Policy | Rule (from `pref_list()` in `raktsetu_sim_v3.py`) | Support | In the prototype |
|---|---|---|---|
| **strict** | ABO- and RhD-identical only | S1 default, "type-specific as far as possible" | **Default** for every match run and for the public finder |
| **standard** | identical, then plasma-compatible ABO; RhD− recipients get RhD− only; RhD− units go to RhD+ recipients last | Plasma-compatibility principle (S1 §5.2 for FFP; S2 Table 1 for O recipients). **This tier is not stated for platelets in the Indian manual; it is our construction** (`STAGE2_NOTES.md`) | Opt-in per run; requires a medical officer's acknowledgement; every card shows "non-identical: standard policy" |
| **relaxed** | standard, then any ABO (O last), then RhD+ to RhD− with an **anti-D flag** | S1 shortage clause; S2 O-last order and anti-D rule | Opt-in per run, MO acknowledgement, cards show "shortage policy" and, where applicable, "anti-D consideration" |

Exact preference lists (copied from `sim_v3/STAGE2_NOTES.md`; the parity test `P-01` checks them against the code):

- **standard**: O+ ← O+, A+, B+, AB+, O−, A−, B−, AB−; O− ← O−, A−, B−, AB−; A+ ← A+, AB+, A−, AB−; A− ← A−, AB−;
  B+ ← B+, AB+, B−, AB−; B− ← B−, AB−; AB+ ← AB+, AB−; AB− ← AB−.
- **relaxed**: each standard list, then the incompatible ABO groups (A ← B, O; B ← A, O; AB ← A, B, O), RhD+ before
  RhD− for RhD+ recipients. For RhD− recipients, all RhD+ units come last (anti-D flag).

Known divergence from S2, kept from the simulator: S2's order for group-A recipients is A, B, O and omits AB; our
standard tier puts AB second because AB plasma is compatible with all (`STAGE2_NOTES.md`).

What the simulator found about these policies (simulated, not clinical evidence; `sim_v3/RESULTS_v3.md` §7):
standard and relaxed served more patients in the model, but standard left restrictive groups worse off on dev seeds
(`STAGE2_NOTES.md`, "Observation for the record"), and relaxed produced anti-D flags (an upper bound, no sex/age in the
model). This is why strict is the default.

### Prototype-only additions
- **Identical-only flag on a shortfall (P1).** A requesting centre can mark a shortfall "ABO-identical only" (e.g.
  infant under one year, S1). The flag carries no patient detail; the matcher then uses strict for that need.
- **SDP reminder.** When a non-identical SDP is suggested, the card shows "SDP across group barrier: plasma reduction
  or additive solution (DGHS 2023 §5.3)". The software cannot check this; the medical officer does.

## 3. Near-expiry units ("≤ 48 h") and surplus

**Simulator rule.** A unit has remaining life r days (5 at production; usable days t … t+4). It is near-expiry if
r ≤ 2 (`NEAR = 2`). A centre offers only its surplus: among its units of group g sorted oldest-first, the unit at
position k (0-based) with r ≤ 2 is surplus if k ≥ d̄·w_g·r, where d̄ is the centre's mean daily demand and w_g the
group's demand share. Offered units are the oldest near-expiry **non-received** units, up to the surplus count
(`surplus_near`, `Centre.own_offerable`; `MODEL_SPEC_v3.md` §4).

**Prototype mapping.** Units carry a real `expires_at` (end of the last usable day, local time). The prototype computes
`r = (expiry_date_local − today_local).days + 1` and applies the simulator rule unchanged, so `core/` stays
parity-testable. The UI shows the actual hours left.

**Deviation flag (D-10).** The deck says "48 h units" (slide 3, slide 4). With r ≤ 2, a unit evaluated at 09:00 has at
most 15 + 24 = 39 h left (`PREREGISTRATION_v3.md` §3.4 clock). We keep the simulator's r ≤ 2 rule for parity and label
the board column "expires within 2 days". Pending approval (ADR-010).

**Parameters d̄ and w_g** are seeded per centre from the simulator's means and `DIST_WEST`. They are **simulated
parameters**; a real centre would supply its own.

## 4. One-hop rule

A unit received by transfer is flagged `received_via_transfer` and is never offered again (`MODEL_SPEC_v3.md` §1,
mirroring D&C Rules 122P(xv), S3). The recipient can still issue it to its own patients; that is outside the platform.

## 5. 12-hour margin on arrival (team-chosen)

**This is a safety margin the team chose, not a cited regulation** (`PREREGISTRATION_v3.md`, Amendment 2). The source
for "12 h" was never found in the delivered files (`STAGE2_NOTES.md`, "Rules fixed as in v2").

- **Simulator form.** At the 09:00 decision a unit with remaining life r has 15 + 24(r − 1) hours left. It may be
  dispatched only if 15 + 24(r − 1) − (T_c + T_t)/60 ≥ 12, with T_c the confirmation time and T_t = 90 min transport
  (both **assumed**; `PREREGISTRATION_v3.md` §3.4).
- **Prototype form.** `hours_left_on_arrival = (expires_at − (now + T_c + T_t)) / 1 h ≥ RAKTSETU_MARGIN_HOURS (12)`.
  - At suggestion time, T_c = 15 min (the simulator's assumed mean confirmation delay) and T_t = the seeded transport
    estimate (default 90 min). **ASSUMPTION.**
  - At approve and dispatch, T_c = 0 (confirmation already happened) and `now` is the real current time.
- The simulator form is a special case of the prototype form with `now` = 09:00; parity test `P-07` checks both agree
  on that case.
- Simulated context: with 180-min transport no unit with one day left can meet the margin, and about 20% of the cut in
  families sent to search is lost (`RESULTS_v3.md` §6). The prototype shows the margin result on every card.

## 6. Which units are sent

Within a confirmed transfer, the units with the **most life left** are reserved first, as in the simulator's dispatch
step (`MODEL_SPEC_v3.md` §4, step 4). Within a tier at the recipient, issuing is oldest-first; that is the centre's
own practice and outside the platform.

## 7. Storage and shelf life

- Platelet shelf life 5 days (`MODEL_SPEC_v3.md` §1). The deck cites 20–24 °C storage to the DGHS/NBTC Technical
  Manual 2023 (slide 4). **UNVERIFIED here:** the local excerpt (S1) covers §5.3 only, not the storage section.
- Agitation and transport containers were raised by the jury (`inputs/Strict_Jury_Evaluation.docx`, red flags). The
  prototype records a "validated 20–24 °C box used" checkbox at dispatch; it does not verify it.
- RDP vs SDP is recorded but not modelled differently (`MODEL_SPEC_v3.md` §7).

## 8. Questions for the transfusion specialist

1. Is strict (ABO/RhD-identical) the right default for inter-centre platelet transfers in India?
2. Is our "standard" tier (plasma-compatible ABO, RhD− to RhD− only) acceptable, and is AB-second for A recipients
   right, given S2 omits AB?
3. Under what documented shortage condition may "relaxed" be used, and who declares it?
4. Is a 12-hour on-arrival margin reasonable? What margin would you set?
5. Which medical officer should approve: the sending centre's, the receiving centre's, or both? (ADR-009)
6. What transport and agitation conditions must be recorded for a transfer?
7. Is r ≤ 2 days (≈ ≤ 39 h at 09:00) the right "near-expiry" cut-off for offering units?

Until these are answered, every screen carries "not clinically validated".
