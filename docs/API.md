# API

Status: **planned** (Checkpoint A). FastAPI, JSON over HTTP, base path `/api`. OpenAPI docs at `/docs` once built.

## 1. Conventions

- **Demo identity (ADR-004).** Requests carry `X-Demo-User: <user id>` (set by the role switcher). The server looks up
  the seeded user and its role and centre. Missing header = `public`. **This is not authentication**; anyone can send
  any header. It exists only so the demo can show role rules.
- Groups are strings `"O+" "O-" "A+" "A-" "B+" "B-" "AB+" "AB-"` (URL-encode `+` as `%2B`).
- Times are ISO 8601 with offset. Responses use UTC; the UI converts to Asia/Kolkata.
- Errors use one shape:

```json
{ "error": { "code": "illegal_transition", "message": "confirmed → dispatched requires an approval", "details": {} } }
```

| HTTP | `code` values |
|---|---|
| 400 | `validation_error` (all body/parameter validation, incl. unknown fields), `unknown_group`, `unknown_user`, `acknowledgement_required`, `bad_csv` |
| 403 | `forbidden_role`, `not_your_centre` |
| 404 | `not_found` (also for a transfer that does not involve the caller's centre: other centres' transfers are hidden) |
| 409 | `illegal_transition`, `margin_failed`, `self_transfer`, `stale_version` |
| 502 | `llm_unavailable` (only on explicit `mode=llm`; `auto` falls back silently and says so in the draft) |

## 2. Role matrix

C = coordinator, S = centre_staff, M = medical_officer, P = public. "own" = only for the user's centre.
"sender" / "receiver" = staff or MO of that side of the transfer.

| Endpoint | C | S | M | P |
|---|---|---|---|---|
| `GET /api/health` | ✓ | ✓ | ✓ | ✓ |
| `GET /api/demo/users`, `GET /api/me` | ✓ | ✓ | ✓ | ✓ |
| `GET /api/centres`, `GET /api/board` | ✓ | ✓ | ✓ | — |
| `POST /api/centres/{id}/stock-posts` (+ `/csv`) | — | own | own | — |
| `POST /api/shortfalls`, `GET /api/shortfalls` | read | own | own | — |
| `POST /api/match/run` | ✓ | — | — | — |
| `GET /api/transfers`, `GET /api/transfers/{id}` | all | own side | own side | — |
| `POST …/request-confirmation` | ✓ | — | — | — |
| `POST …/confirm` | — | sender | sender | — |
| `POST …/approve`, `POST …/reject` | — | — | sender (ADR-009) | — |
| `POST …/dispatch` | — | sender | sender | — |
| `POST …/deliver` | — | receiver | receiver | — |
| `POST …/cancel` | ✓ | — | — | — |
| `GET /api/trust` | ✓ | — | own | — |
| `GET /api/public/finder` | ✓ | ✓ | ✓ | ✓ |
| `POST /api/channel/mock/inbound` | ✓ | ✓ | ✓ | — |
| `GET /api/parser/drafts`, `PATCH`/`commit`/`discard` | ✓ | own | own | — |
| `POST /api/parser/parse` (dry run) | ✓ | ✓ | ✓ | — |
| `GET /api/audit` | ✓ | — | own | — |

## 3. Endpoints

### Health and demo
- `GET /api/health` → `{"status":"ok","demo_mode":true,"parser_mode":"rules|llm","labels":["simulated data","mock channel","not clinically validated"]}`
- `GET /api/demo/users` → `[{"id":"u-mo-F","display_name":"Dr. Demo (Centre F)","role":"medical_officer","centre_id":"C-F"}]`
- `GET /api/me` → the resolved demo user or `{"role":"public"}`.

### Centres and board
- `GET /api/centres` → `[{"id","name","kind","area","last_post_at","listing_age_bucket"}]`
- `GET /api/board?now=<optional ISO, demo only>` →
```json
{
  "as_of": "2026-10-16T02:30:00Z",
  "centres": [{
    "id": "C-F", "name": "Centre F · Regional centre",
    "listed": 9, "near_expiry": 4, "last_post_at": "…", "listing_age_bucket": 0,
    "trust_band": "High", "offerable": {"O+": 2, "B+": 1}
  }],
  "kpis": {"near_expiry_listed": 17, "suggested_open": 2, "centres_fresh_24h": 5, "delivered_7d": 3},
  "labels": ["simulated data"]
}
```
The board exposes the band to staff; it does **not** expose p as a number (the trust view below does, for the
coordinator only, labelled as a model estimate).

### Stock and shortfalls
- `POST /api/centres/{id}/stock-posts`
```json
{ "units": [ {"component": "RDP", "abo_rh": "O+", "expires_at": "2026-10-16T18:29:59Z"} ], "source": "form" }
```
→ `201 {"stock_post_id": 12, "listed": 9, "superseded": 7}`. Errors: 400 `unknown_group`, 400 if `expires_at` is in
the past, 403 `not_your_centre`.
- `POST /api/centres/{id}/stock-posts/csv` (multipart, columns `component,abo_rh,count,expires_on`) → same as above.
  **P1.**
- `POST /api/shortfalls` `{"abo_rh":"O+","component":"RDP","count":3}` → `201 {"id": 5, "status": "open"}`.
  The body schema has `extra="forbid"`, so any extra field (e.g. a patient name) is a 400.
- `GET /api/shortfalls?status=open`

### Matching
- `POST /api/match/run` `{"policy": "strict"}` (`standard`/`relaxed` require `"acknowledged_by_mo": "<user id>"`,
  see `MATCHING_POLICY.md` §2)
```json
{
  "match_run_id": 3, "policy": "strict",
  "suggested": [{
    "transfer_id": 21, "from": "C-F", "to": "C-C", "abo_rh_needed": "O+", "abo_rh_offered": "O+",
    "tier": 0, "qty": 2, "anti_d_flag": false, "sender_band": "High", "listing_bucket": 0,
    "reason": "Centre C requested 3 O+ RDP. Centre F lists 2 O+ units expiring within 2 days beyond its own expected use. Identical group. Listing updated today."
  }],
  "unmatched_needs": [{"shortfall_id": 6, "abo_rh": "B-", "open": 1, "why": "no offerable B- unit under strict policy"}]
}
```
Idempotence: a run does not duplicate transfers for a shortfall that already has a non-terminal transfer covering
it; it matches only `count_open`.

### Transfers
- `GET /api/transfers?status=…&centre=…` → list of transfer summaries.
- `GET /api/transfers/{id}` → transfer + reserved units + audit trail.
- `POST /api/transfers/{id}/request-confirmation` `{}` → `200 {"status":"confirm_requested"}`
- `POST /api/transfers/{id}/confirm` `{"units_available": 1, "note": "only 1 left"}` →
```json
{ "status": "confirmed", "qty_confirmed": 1, "margin": {"passed": 1, "blocked": 0},
  "trust": {"centre": "C-G", "bucket": 2, "alpha": 5.0, "beta": 4.0, "band_before": "Medium", "band_after": "Medium"} }
```
`units_available` > requested → 400. 0 → `"status": "failed"`.
- `POST /api/transfers/{id}/approve` `{"note": "ok"}` → `200 {"status":"approved","approved_by":"u-mo-F"}`;
  409 `margin_failed` if the re-check fails; 403 `forbidden_role` for anyone but the sender's MO.
- `POST /api/transfers/{id}/reject` `{"reason": "…"}` → `cancelled`.
- `POST /api/transfers/{id}/dispatch` `{"transport_min": 90}` (optional override) → `dispatched`; 409 if not
  approved or margin fails.
- `POST /api/transfers/{id}/deliver` `{}` → `delivered`; units appear at the receiver with
  `received_via_transfer: true`.
- `POST /api/transfers/{id}/cancel` `{"reason": "…"}` → `cancelled`.

All transition endpoints accept an optional `If-Match: <updated_at>`; a mismatch returns 409 `stale_version` (two
people clicking at once during a live demo).

### Trust (coordinator / MO view)
- `GET /api/trust` → per centre and bucket: `alpha`, `beta`, `p` (rounded to 2 dp), `band`, `seeded_alpha`,
  `seeded_beta`, `n_confirmations`. Labelled "model estimate on simulated history; Beta(2,1) prior". Not public.

### Public finder
- `GET /api/public/finder?group=O%2B&component=RDP`
```json
{
  "group": "O+", "component": "RDP",
  "results": [{
    "centre_name": "Centre F · Regional centre", "area": "…", "phone": "+91-00000-000F (fictional)",
    "listed_compatible": 4, "updated": "3 h ago", "band": "High"
  }],
  "advice": "Call before travelling. Bands are estimates from past confirmations, not a guarantee.",
  "band_note": "In simulation, centres in the High band had stock on 87% of visits, Medium 71%, Low 54% (simulated; sim_v3/results/finder_bands.json, S1).",
  "labels": ["simulated data", "not clinically validated"]
}
```
The result objects have **no** numeric probability field (`test_finder_response_has_no_probability`). Compatible =
identical group (strict) for the public finder. No query is logged with any identifier.

### Mock channel and parser
- `POST /api/channel/mock/inbound` `{"channel":"mock_whatsapp","sender":"+91-00000-0000H","text":"…"}` →
  `201 {"inbound_message_id": 4, "parse_draft_id": 9, "parser": "rules", "needs_review": ["expiry_relative"]}`.
  Shape is deliberately simple; it is **not** the WhatsApp Cloud API webhook format.
- `POST /api/parser/parse` `{"text":"…","centre_id":"C-H","mode":"auto"}` → draft payload without saving (dry run).
- `GET /api/parser/drafts?status=pending`
- `PATCH /api/parser/drafts/{id}` `{"payload": {…}}` → edited draft (human check).
- `POST /api/parser/drafts/{id}/commit` → creates a stock post or shortfall from the reviewed payload; returns its id.
- `POST /api/parser/drafts/{id}/discard` `{"reason":"…"}`

### Audit
- `GET /api/audit?entity=transfer&entity_id=21` → ordered audit rows.

## 4. Implementation notes (Stage 2, 16 Oct 2026)

- Built: every endpoint above except `POST /api/centres/{id}/stock-posts/csv` (P1, stretch) and the mock channel /
  parser endpoints (Stage 4). Added `GET /api/centres/{id}/units` (internal roles) for the UI.
- `If-Match` carries the transfer's integer `version` (returned on every transfer), not a timestamp.
- Shortfalls accept `identical_only` (strict matching for that need, e.g. infants; no patient detail).
- Board KPI keys: `near_expiry_listed`, `transfers_awaiting_action`, `centres_fresh_24h`, `delivered_7d`.
- `GET /api/health` returns `now` and `demo_clock: true` when the seeded demo clock is active (ADR-013).
- Validation errors use HTTP 400 with `code: validation_error` and the offending fields in `details.errors`.
- Run with `make api` (uvicorn `--factory app.main:create_app`); OpenAPI at `/docs`.

## 5. Implementation notes (Stage 4, 16 Oct 2026)

- `POST /api/channel/mock/inbound` body `{channel: mock_whatsapp|mock_sms|paste, text, sender?, centre_id?}`.
  Staff may only send as their own centre; the coordinator may pick any centre. The response includes the draft.
- `GET /api/channel/samples`: synthetic demo messages from the seed (not part of the parser test set).
- `GET /api/parser/drafts`; `PATCH /api/parser/drafts/{id}` body `{message_type?, items?: [{abo_rh, component,
  count, expiry_date}], commit_mode?: add|replace, patient_data_redacted?}`. Flags are recomputed after every edit.
- `POST /api/parser/drafts/{id}/commit` returns 409 `needs_review` with the blocking flags while any remain.
- `GET /api/health` now reports `parser_mode`, `llm_available` (key present, never the key) and `llm_model`.
