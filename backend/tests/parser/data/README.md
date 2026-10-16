# Parser test messages (synthetic, labelled)

Plan: `docs/PARSER_SPEC.md` §6. **Everything here is synthetic.** No real message, patient, donor, phone number
or centre name, ever.

| File | Written by | Status |
|---|---|---|
| `generated.jsonl` | Claude Code, from templates (`scripts/gen_parser_messages.py`) | 90 messages |
| `handwritten_<initials>.jsonl` | **team members, by hand** (task 4.1) | needed: ≥ 60 in total |
| `handwritten_TEMPLATE.jsonl` | format examples only; ids start with `example-` and are ignored | — |
| `split.json`, `../test_set.sha256` | `scripts/parser_split.py --freeze` | created once the hand-written set is in |
| `../targets.json` | approved at Checkpoint E | **frozen 16 Oct 2026**; its hash is recorded at split freeze |

## How to write the hand-written messages (task 4.1)

Write them the way blood-centre staff would type a quick WhatsApp or SMS message. Do not open the parser code or
the generated file first, so the test does not drift towards what the parser already handles. Mix in:

- English and **Hinglish** (Hindi in Latin script: "kal", "aaj", "parso", "bacha hai", "chahiye", "ek/do/teen")
- stock reports (about 70%), shortfall requests (about 20%), and "other" messages such as greetings (about 10%)
- different ways of writing groups (O+, O pos, O positive, O+ve, B neg, AB-ve), counts (2, x2, two, do) and
  dates (17/10, 17 Oct, tomorrow, kal, Friday), plus typos and abbreviations people really use
- a few hard cases: a group without an RhD sign, a missing count or expiry, two centres mentioned, a nil row

One JSON object per line. `gold` is what a correct reading **must** record:

```json
{"id": "h-sr-001", "author": "human:SR", "lang": "hinglish", "as_of": "2026-10-16T08:10:00+05:30", "sender_centre": "C-H", "text": "O+ ke 2 unit kal expire, B pos 1 parso tak", "gold": {"message_type": "stock_post", "items": [{"abo_rh": "O+", "component": "RDP", "count": 2, "expiry_date": "2026-10-17"}, {"abo_rh": "B+", "component": "RDP", "count": 1, "expiry_date": "2026-10-18"}]}}
```

Label rules:
- `id`: `h-<initials>-NNN`, unique. `author`: `human:<initials>`. `lang`: `en` or `hinglish`.
- `as_of`: when the message was "sent" (keep `2026-10-16T08:10:00+05:30` unless the message needs another day).
  Relative dates are resolved against this: tomorrow / kal = as_of + 1 day; a weekday = the next such day, today
  included.
- `sender_centre`: one of `C-A` … `C-H`.
- `message_type`: `stock_post`, `shortfall` or `other`. `other` has `"items": []`.
- Each item: `abo_rh` in O+ O- A+ A- B+ B- AB+ AB-, or `null` if the message does not make the group clear;
  `component` `SDP` only if the message says SDP / apheresis / single donor, otherwise `RDP`; `count` an integer or
  `null` if not stated; `expiry_date` `YYYY-MM-DD`, or `null` if not stated (always `null` for shortfalls).
- Rows reported as nil / none / zero are **not** items.
- A second team member checks each label before the set is frozen (put their initials in a `checked_by` field).

When done: save as `handwritten_<initials>.jsonl` here and tell Claude Code. It then runs
`python scripts/parser_split.py --freeze`, and the test split is frozen before any score is computed on it.
