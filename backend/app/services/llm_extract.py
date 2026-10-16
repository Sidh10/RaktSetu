"""LLM extraction for stock messages via the Claude API (ADR-003). Optional: used only when ANTHROPIC_API_KEY is set.

The model extracts fields as written (group, component, count, expiry kind/value). It never resolves dates and never
decides what needs review: app.core.parser_rules does both, the same way for both parser paths. Any failure (no key,
timeout, API error, refusal, truncated or schema-invalid output) raises LLMUnavailable and the caller falls back to
the rule-based parser. Messages in this prototype are synthetic; no real data is sent.
"""
from __future__ import annotations

import json
from datetime import date

from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.parser_rules import GROUPS

MAX_TOKENS = 4000


class LLMUnavailable(Exception):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmItem(_Strict):
    abo_rh: str | None
    component: str | None
    count: int | None
    expiry_kind: str
    expiry_value: str | None
    source_span: str


class LlmOutput(_Strict):
    message_type: str
    items: list[LlmItem]


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["message_type", "items"],
    "properties": {
        "message_type": {"type": "string", "enum": ["stock_post", "shortfall", "other"]},
        "items": {"type": "array", "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["abo_rh", "component", "count", "expiry_kind", "expiry_value", "source_span"],
            "properties": {
                "abo_rh": _nullable({"type": "string", "enum": list(GROUPS)}),
                "component": _nullable({"type": "string", "enum": ["RDP", "SDP"]}),
                "count": _nullable({"type": "integer"}),
                "expiry_kind": {"type": "string", "enum": ["absolute_date", "relative_day", "weekday", "none"]},
                "expiry_value": _nullable({"type": "string"}),
                "source_span": {"type": "string"},
            },
        }},
    },
}

SYSTEM = """You extract platelet stock information from short messages sent by blood-centre staff in India.
Messages are in English or Hinglish (Hindi written in Latin script, mixed with English).

Return one item per blood group mentioned.
- message_type: "stock_post" if the centre reports platelets it has; "shortfall" if it asks for platelets it needs
  (need, required, chahiye, urgent); "other" for anything else (greetings, questions). "other" has no items.
- abo_rh: one of O+, O-, A+, A-, B+, B-, AB+, AB-. "pos/positive/+ve" means +, "neg/negative/-ve" means -.
  If the message gives an ABO group without an RhD sign, or the group is unclear, use null. Never guess.
- component: "SDP" for single donor / apheresis / SDP; "RDP" for random donor / RDP / PC / platelet concentrate;
  null if the message does not say.
- count: the number of units for that group as an integer (Hindi number words: ek 1, do 2, teen 3, char 4,
  paanch 5). null if not stated. Omit rows reported as nil, none or zero.
- Expiry, copied as written, never computed:
  - an explicit date -> expiry_kind "absolute_date", expiry_value "YYYY-MM-DD" (use the reference date's year if
    the message gives none);
  - today/aaj/tonight -> "relative_day", "today"; tomorrow/kal -> "relative_day", "tomorrow";
    day after tomorrow/parso -> "relative_day", "day_after_tomorrow";
  - a weekday -> "weekday" with the full English weekday name in lower case;
  - no expiry stated for that item -> "none" and null.
  An expiry said for all items ("all expire 18/10", "sab parso tak") applies to every item.
- source_span: the part of the message the item came from. Never copy names of people, ward or bed numbers.
Shortfall items have expiry_kind "none"."""


def client_factory(timeout_s: float):
    """Indirection so tests can inject a fake client. Reads ANTHROPIC_API_KEY from the environment."""
    import anthropic
    return anthropic.Anthropic(timeout=timeout_s, max_retries=1)


def extract(text: str, today: date, model: str, timeout_s: float) -> LlmOutput:
    try:
        import anthropic
    except ImportError as e:   # pragma: no cover
        raise LLMUnavailable(f"anthropic SDK missing: {e}")
    try:
        client = client_factory(timeout_s)
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": f"Reference date: {today.isoformat()}\nMessage:\n{text}"}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}, "effort": "low"},
        )
    except anthropic.APITimeoutError:
        raise LLMUnavailable("timeout")
    except anthropic.APIConnectionError:
        raise LLMUnavailable("network unavailable")
    except anthropic.APIStatusError as e:
        raise LLMUnavailable(f"API error {e.status_code}")
    except anthropic.AnthropicError as e:   # e.g. no API key configured
        raise LLMUnavailable(type(e).__name__)
    if resp.stop_reason != "end_turn":
        raise LLMUnavailable(f"stop_reason {resp.stop_reason}")
    raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        out = LlmOutput.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as e:
        raise LLMUnavailable(f"invalid output: {type(e).__name__}")
    if out.message_type not in ("stock_post", "shortfall", "other"):
        raise LLMUnavailable("invalid message_type")
    return out
