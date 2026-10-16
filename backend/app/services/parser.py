"""Turn a message into a draft payload (docs/PARSER_SPEC.md section 2). Drafts never change stock by themselves."""
from __future__ import annotations

import re
from datetime import date, datetime

from app.config import Settings
from app.core import parser_rules as pr
from app.services import llm_extract
from app.services.errors import DomainError

INFO_FLAGS = {"component_assumed", "expiry_relative", "centre_mismatch"}
REPLACE_HINT = re.compile(r"\b(stock update|total stock|current stock|full stock|closing stock|complete list)\b", re.I)


def _confidence(flags: list[str]) -> str:
    if not flags:
        return "high"
    return "medium" if set(flags) <= INFO_FLAGS else "low"


def item_dict(it: pr.Item) -> dict:
    e = it.expiry
    return dict(abo_rh=it.abo_rh, component=it.component or "RDP", component_stated=it.component is not None,
                count=it.count,
                expiry=None if e is None else dict(kind=e.kind, value=e.value,
                                                   resolved_date=e.resolved_date.isoformat() if e.resolved_date else None),
                source_span=it.source_span, flags=it.flags, confidence=_confidence(it.flags))


def needs_review(message_flags: list[str], items: list[dict]) -> list[str]:
    out = set(message_flags)
    for it in items:
        out |= set(it["flags"])
    return sorted(out)


def blocking(payload: dict) -> list[str]:
    return sorted(set(payload["needs_review"]) & (pr.BLOCKING | {"unknown_sender"}))


def _from_llm(out: llm_extract.LlmOutput, today: date) -> pr.ParseResult:
    items = []
    for x in out.items:
        if x.count == 0:
            continue
        grp = x.abo_rh if x.abo_rh in pr.GROUPS else None
        comp = x.component if x.component in ("RDP", "SDP") else None
        items.append(pr.Item(grp, comp, x.count, pr.resolve_expiry(x.expiry_kind, x.expiry_value, today),
                             x.source_span))
    mtype = out.message_type if items else "other"
    for it in items:
        it.flags = pr.item_flags(it, mtype, today)
    return pr.ParseResult(mtype, items, [] if items else ["no_items"])


def parse_message(text: str, centre_id: str | None, received_at: datetime, settings: Settings,
                  mode: str | None = None) -> dict:
    """Parse with the configured mode: rules | llm (error if unavailable) | auto (LLM if a key is set, else rules)."""
    mode = mode or settings.parser_mode
    if mode not in ("rules", "llm", "auto"):
        raise DomainError(400, "validation_error", f"unknown parser mode {mode!r}")
    local = received_at.astimezone(settings.tz)
    today = local.date()
    letter = centre_id[-1] if centre_id else None
    parser, model, notes = "rules", None, []
    result = None
    if mode == "llm" or (mode == "auto" and settings.llm_key_present):
        try:
            result = _from_llm(llm_extract.extract(text, today, settings.llm_model, settings.llm_timeout_s), today)
            parser, model = "llm", settings.llm_model
        except llm_extract.LLMUnavailable as e:
            if mode == "llm":
                raise DomainError(502, "llm_unavailable", f"LLM parser unavailable: {e}")
            notes.append(f"LLM unavailable ({e}); fell back to the rule-based parser")
    if result is None:
        result = pr.parse(text, today, letter)
    msg_flags = sorted(set(result.flags) | set(pr.scan_message_flags(text, letter)))
    if centre_id is None:
        msg_flags.append("unknown_sender")
    items = [item_dict(it) for it in result.items]
    payload = dict(message_type=result.message_type, centre_id=centre_id, as_of=local.isoformat(), items=items,
                   message_flags=msg_flags, notes=notes + result.notes, parser=parser, model=model,
                   commit_mode="replace" if REPLACE_HINT.search(text) else "add")
    payload["needs_review"] = needs_review(msg_flags, items)
    return payload


def rebuild_after_review(payload: dict, edits: dict, today: date) -> dict:
    """Apply a reviewer's edits and recompute the flags (the same post-checks as parsing)."""
    mtype = edits.get("message_type", payload["message_type"])
    items = []
    for e in edits.get("items", None) if edits.get("items") is not None else payload["items"]:
        exp = None
        d = e.get("expiry_date") if "expiry_date" in e else ((e.get("expiry") or {}).get("resolved_date"))
        if d:
            dd = date.fromisoformat(d)
            exp = pr.Expiry("reviewed", dd.isoformat(), dd)
        it = pr.Item(e.get("abo_rh"), e.get("component") or "RDP", e.get("count"), exp, e.get("source_span", ""))
        it.flags = [f for f in pr.item_flags(it, mtype, today) if f != "expiry_relative"]
        items.append(item_dict(it) | {"component_stated": True})
    msg_flags = [f for f in payload["message_flags"] if f != "no_items"]
    if edits.get("patient_data_redacted"):
        msg_flags = [f for f in msg_flags if f != "possible_patient_data"]
    if not items and mtype != "other":
        msg_flags.append("no_items")
    out = dict(payload, message_type=mtype, items=items, message_flags=sorted(set(msg_flags)),
               commit_mode=edits.get("commit_mode", payload.get("commit_mode", "add")))
    out["needs_review"] = needs_review(out["message_flags"], items)
    return out
