# Parser specification

Status: **planned** (Stage 4). Input arrives through the **mock channel** only (ADR-002). The parser turns a free-text
stock or shortfall message into a structured **draft**. A human always checks the draft before anything changes
(deck slide 4: "LLM parser + human check").

Why it matters: the jury flagged "no evidence for the LLM parser" and asked for extraction accuracy on a test set with
the human-check rate (`inputs/Strict_Jury_Evaluation.docx`, weakness 8). §6 is the plan for that evidence.

## 1. Scope

| Language / script | Round 2 status |
|---|---|
| English | **supported** |
| Hinglish (Hindi in Latin script, mixed with English: "kal", "aaj", "unit", "bacha hai") | **supported** |
| Hindi (Devanagari) | **planned** (deck slide 5 lists Hindi as planned) |
| Marathi | **planned** (deck slide 5) |

Message types: `stock_post` (units on hand / near expiry), `shortfall` (units needed), `other` (anything else, e.g.
greetings, questions; never committed).

## 2. Output schema (draft payload)

```json
{
  "message_type": "stock_post",
  "centre_id": "C-H",
  "as_of": "2026-10-16T08:10:00+05:30",
  "items": [
    {
      "component": "RDP",
      "abo_rh": "O+",
      "count": 2,
      "expiry": {"kind": "relative_day", "value": "tomorrow", "resolved_date": "2026-10-17"},
      "source_span": "O+ RDP 2 unit kal expire",
      "confidence": "high"
    }
  ],
  "needs_review": ["expiry_relative"],
  "parser": "rules",
  "model": null
}
```

Field rules:
- `abo_rh` ∈ `O+ O- A+ A- B+ B- AB+ AB-`. Accept "O pos", "O positive", "B neg", "Bve-", "AB-ve", "o+ve". Anything
  else → item flagged `unknown_group`, never guessed.
- `component` ∈ `RDP` / `SDP`. "random donor", "PC", "platelet concentrate" → RDP; "apheresis", "SDP", "single donor"
  → SDP. If absent → `RDP` **with** flag `component_assumed`.
- `count`: positive integer; words "one/two/do/teen/ek" accepted. Missing → flag `count_missing`, item not committable.
- `expiry`: absolute date ("17/10", "17 Oct"), weekday, or relative ("today/aaj", "tomorrow/kal", "parso" = day after
  tomorrow). Relative values are resolved against `as_of` in Asia/Kolkata and always flagged `expiry_relative` so the
  reviewer sees the resolved date. "kal" is ambiguous in Hindi (yesterday / tomorrow); in a stock message we resolve it
  to tomorrow and flag it.
- `centre_id` comes from the mock sender mapping, not from the text. Text that names another centre → flag
  `centre_mismatch`.
- No patient data is extracted. If text looks like it contains a name or bed number, the draft is flagged
  `possible_patient_data` and the raw text is shown for redaction before commit.

## 3. Supported formats (examples are synthetic)

| # | Example | Type |
|---|---|---|
| 1 | `O+ RDP x4 exp 17/10` | stock_post |
| 2 | `Platelets available: B+ 3 (expire tomorrow), O+ 2 (expire 18 Oct)` | stock_post |
| 3 | `Centre H: O+ RDP 2 unit kal expire, B+ 1` | stock_post (Hinglish) |
| 4 | `aaj 2 O pos platelet bacha hai, kal tak` | stock_post (Hinglish) |
| 5 | `Need 3 O+ platelets urgently` | shortfall |
| 6 | `humko 2 B neg SDP chahiye` | shortfall (Hinglish) |
| 7 | `Stock update — A+ 1, AB+ 1, O- nil` | stock_post (zero rows dropped) |
| 8 | `Good morning sir` | other |

## 4. Pipeline

```
text ──► normalise (lowercase copy, unicode dashes, "+ve"/"-ve") ──► mode?
          │
          ├─ rules  ─► regex + token grammar ─► draft(parser="rules")
          │
          └─ llm    ─► Claude structured extraction (schema §2) ─► validate against schema
                         │ error / timeout / refusal / schema-invalid
                         └──────────────────────────────────────► rules (draft says "fell back to rules")
          ▼
     post-checks (same for both paths): group whitelist, count > 0, expiry not in past,
     relative-date flag, centre mapping, possible-patient-data scan
          ▼
     draft (status=pending) ──► human review in Parser inbox ──► commit ──► stock post / shortfall
```

- **Rule-based path** (always available, no network): a small grammar of group tokens, component tokens, counts and
  date expressions; segments split on commas, semicolons, "and/aur", newlines.
- **LLM path** (ADR-003): one Messages API call with structured output constrained to the §2 schema, using the
  official `anthropic` Python SDK (`client.messages.parse(...)` with `output_config` format, per the Claude API
  reference). Model from `RAKTSETU_LLM_MODEL`; key from `ANTHROPIC_API_KEY` only. Timeout
  `RAKTSETU_LLM_TIMEOUT_S` (15 s). The system prompt contains the schema, the group/component vocabulary, the
  relative-date rule and the instruction to leave unknowns null rather than guess. `stop_reason` is checked
  before reading content; a refusal or `max_tokens` stop falls back to rules.
- **Modes** (`RAKTSETU_PARSER_MODE`): `rules`; `llm` (error if no key); `auto` (LLM if a key is set, else rules).
  The demo runs in `auto` and works with the network unplugged.
- **Logging.** Raw LLM responses are kept only in the draft row; nothing is sent anywhere except the Claude API call.
  Messages are synthetic, so no real data reaches the API.

## 5. Human check

- Every draft is `pending` until a coordinator or the centre's own staff commits it.
- The inbox shows the raw text, highlighted `source_span`s, each field editable, and the `needs_review` flags in red.
- Commit is disabled while any item has `unknown_group`, `count_missing` or `possible_patient_data`.
- **Human-check rate** = share of drafts that had at least one `needs_review` flag or were edited before commit.
  It is reported next to accuracy (§6).

## 6. Accuracy evaluation plan

### 6.1 Test set (synthetic, labelled)
- **Size:** 150 messages: 90 English, 60 Hinglish; about 70% stock posts, 20% shortfalls, 10% other.
- **Authorship, to avoid a circular test:** at least **60 messages written by team members by hand** (human task,
  `TASKLIST.md` 4.1), the rest generated from templates with random groups, counts and dates. Claude Code may write
  the template generator but not the hand-written set. LLM-generated paraphrases are **not** used, because the same
  model family would then parse its own phrasing.
- **Labels:** gold JSON per message in the §2 schema, written by the author and checked by a second team member.
- **Split:** 50 dev / 100 test, stratified by language and type. The test split is **frozen** (file hash recorded in
  `backend/tests/parser/test_set.sha256`) before any accuracy number is computed, mirroring the simulator's
  pre-registration practice (`sim_v3/PREREGISTRATION_v3.md`). Prompt and rule changes use dev only.
- Stored in `backend/tests/parser/data/` as JSONL; all text synthetic, centre names fictional.

### 6.2 Metrics (computed per parser path: rules, llm)
| Metric | Definition |
|---|---|
| Item exact match | share of gold items where group, component, count and resolved expiry date all match |
| Field accuracy | per field (group, component, count, expiry) over matched items |
| Message exact match | share of messages where the full item set matches |
| Type accuracy | `message_type` correct |
| **Critical error rate** | share of messages where a wrong group or wrong count would be committable **without** a `needs_review` flag. This is the safety metric. |
| Human-check rate | share of messages whose draft carries ≥ 1 flag |
| Fallback rate (llm) | share of messages where the LLM path fell back to rules |
| Latency (llm) | median and max seconds per message |
| Cost (llm) | input/output tokens and US$ from the API's `usage` |

Report 95% bootstrap CIs over messages (B = 10,000), like the simulator results.

### 6.3 Pre-stated targets (to be frozen at Checkpoint E, before running the test split)
Proposed, pending approval: critical error rate **0** on the test split for both paths; item exact match reported as
found, no target. If the critical error rate is > 0 the demo says so and shows the cases.

### 6.4 What the result may and may not claim
- May claim: "On 100 synthetic test messages (English and Hinglish), the parser's item exact match was X [CI];
  critical errors Y; Z% of drafts needed a human check."
- May **not** claim accuracy on real WhatsApp messages, on Hindi/Marathi, or that the human check can be skipped.

## 7. Cost estimate (LLM path)

Prices from the Claude API reference bundled with Claude Code (cached 2026-10-06; **re-check before quoting**):
`claude-opus-5-5` $4 / $20 per million input / output tokens; `claude-sonnet-5-5` $2 / $10; `claude-haiku-5-5`
$0.10 / $0.50.

Assumed size per message (**ASSUMPTION**, to be replaced by measured `usage`): ~1,000 input tokens (system prompt +
schema + message) and ~200 output tokens.

| Model | Per message | 150-message eval | 1,000 demo/rehearsal messages |
|---|---|---|---|
| claude-opus-5-5 | ≈ $0.008 | ≈ $1.20 | ≈ $8 |
| claude-sonnet-5-5 | ≈ $0.004 | ≈ $0.60 | ≈ $4 |
| claude-haiku-5-5 | ≈ $0.0002 | ≈ $0.03 | ≈ $0.20 |

At prototype volume every option is small; the choice is about accuracy and latency, decided in ADR-003.

## 8. Implementation status (Checkpoint E, 16 Oct 2026)

**Built:** rule-based parser and shared post-checks (`backend/app/core/parser_rules.py`, pure); LLM extraction
(`backend/app/services/llm_extract.py`); draft building and review (`services/parser.py`); mock channel and inbox
(`services/inbox.py`, `POST /api/channel/mock/inbound`, `/api/parser/*`); Inbox page in the UI; evaluation tooling
(`scripts/gen_parser_messages.py`, `scripts/parser_split.py`, `scripts/parser_eval.py`).

**Design points**
- The LLM returns fields **as written** (expiry kind + value, e.g. `relative_day` / `tomorrow`). Dates are
  resolved and every flag is raised by the same deterministic code for both parser paths, so the LLM can never
  invent a date or skip a check.
- LLM call: `client.messages.create` with `output_config = {format: json_schema, effort: "low"}`, model from
  `RAKTSETU_LLM_MODEL` (default `claude-opus-5-5`), 15 s timeout, 1 retry. A `stop_reason` other than `end_turn`,
  any API or network error, or schema-invalid JSON makes `auto` mode fall back to rules and say so in the draft;
  `llm` mode returns 502. Server-side refusal fallbacks are not used: the rule parser is the fallback.
- Blocking flags (commit disabled): unknown group, count missing, expiry missing, expiry in the past, possible
  patient data (until the reviewer removes the raw text), no items, unknown sender. Informational: component
  assumed, relative date resolved, another centre mentioned.
- Commit of a stock post either **adds** units (default) or **replaces** the whole listing (default when the text
  says "stock update" / "total stock"); the reviewer can switch. See ADR-015.

**Not verified:** the LLM path has run only against a fake client in tests. No `ANTHROPIC_API_KEY` was available on
16 Oct (Q4), so the request shape has not been checked against the live API.

**Evidence status.** No reportable accuracy number exists yet.
- The hand-written set (task 4.1, at least 60 messages) is pending; `parser_split.py --freeze` refuses to freeze
  without it.
- A **preview** on the 90 generated messages was run only to check the pipeline (`scripts/out/`, git-ignored). It is
  not reportable: Claude Code wrote both the templates and the rules.
- The preview found one real bug, fixed on 16 Oct with a regression test: "Wednesday" and "Saturday" were not
  recognised as weekdays.
- The remaining preview misreads are the phrasings planted to test generalisation ("please arrange ...",
  "... ki zarurat hai" read as stock posts instead of shortfalls). They were **not** added to the rules, to avoid
  tuning on our own templates. Each was caught by a blocking flag (expiry missing), so none could be committed
  unreviewed.

**Targets, FROZEN 16 Oct 2026 (approved at Checkpoint E, before any test-split score):** critical error rate 0 on the test split for each
parser path; item exact match and human-check rate reported as found, with CIs, separately for hand-written and
generated messages. Stored in `backend/tests/parser/targets.json`. `parser_split.py --freeze` records its SHA-256 in
`split.json`; `parser_eval.py --split test` refuses to score if the test split or the targets changed, and prints
PASS/FAIL for the critical-error target. The freeze-and-score path was dry-run on throwaway data (results discarded).
