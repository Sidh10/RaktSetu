"""Rule-based stock-message parser and the post-checks shared with the LLM path (docs/PARSER_SPEC.md).

Pure: no I/O, no clock (pass `today`). English and Hinglish (Latin script) only. The output is a DRAFT; a human
reviews every draft before stock changes. Unknowns are left empty and flagged, never guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

GROUPS = ("O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-")

# Flags that block commit until a reviewer fixes the field (PARSER_SPEC.md section 5)
BLOCKING = {"unknown_group", "count_missing", "expiry_missing", "expiry_in_past", "possible_patient_data", "no_items"}

_SIGN = r"(\+\s*ve\b|\+ve|\+|-\s*ve\b|-ve|-|\s+pos(?:itive)?\b|pos(?:itive)?\b|\s+neg(?:ative)?\b|neg(?:ative)?\b|\s*ve\s*[+-])"
GROUP_RE = re.compile(r"(?<![a-z0-9])(ab|a|b|o)\s*" + _SIGN)
UNSIGNED_RE = re.compile(r"(?<![a-z0-9])(ab|a|b|o)\s+(?=(?:group|grp)\b)|(?<![a-z0-9])(ab|b|o)\s+(?=(?:platelets?|units?|rdp|sdp|\d))")

WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6,
            "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10}
ZERO_RE = re.compile(r"\b(nil|none|zero|no stock|khatam|nahi hai|nahin hai)\b")
COUNT_RE = re.compile(r"(?:(?<=[x×])|\b)(\d{1,3}|" + "|".join(WORD_NUM) + r")\b")
EXPIRY_WORD_RE = re.compile(r"\b(exp|expire[sd]?|expiry|expiring|tak|till|until|upto|valid|use by|by)\b")

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                          "nov", "dec"])}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
DATE_NUM_RE = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b")
DATE_DM_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + _MON + r"\b")
DATE_MD_RE = re.compile(r"\b" + _MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b")
REL = [(re.compile(r"\b(day after tomorrow|parso|parson)\b"), 2, "day_after_tomorrow"),
       (re.compile(r"\b(tomorrow|tmrw|tmw|kal)\b"), 1, "tomorrow"),
       (re.compile(r"\b(today|tonight|aaj)\b"), 0, "today")]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_RE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
                        r"mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b")

SDP_RE = re.compile(r"\b(sdp|apheresis|single donor)\b")
RDP_RE = re.compile(r"\b(rdp|random donor|pc|platelet concentrate)\b")
SHORTFALL_RE = re.compile(r"\b(need|needed|needs|require|required|requirement|chahiye|chahie|want|wanted|short|"
                          r"shortage|request(?:ing)?|urgent(?:ly)?)\b")
ALL_RE = re.compile(r"\b(all|sab|sabhi|both|dono)\b")
CENTRE_RE = re.compile(r"\bcent(?:re|er)\s+([a-h])\b")
PATIENT_RE = re.compile(r"\b(patient|pt\.?|mr\.|mrs\.|ms\.|ward|bed\s*(?:no)?\.?\s*\d|uhid|mrn|ipd|opd no|"
                        r"\d{1,3}\s*(?:yrs|years|yo|y/o)|age\s*\d|name)\b")


@dataclass
class Expiry:
    kind: str              # absolute_date | relative_day | weekday
    value: str             # as written / normalised (e.g. "tomorrow", "friday", "2026-10-17")
    resolved_date: date | None


@dataclass
class Item:
    abo_rh: str | None
    component: str | None
    count: int | None
    expiry: Expiry | None
    source_span: str
    flags: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    message_type: str      # stock_post | shortfall | other
    items: list[Item]
    flags: list[str]       # message-level flags
    notes: list[str] = field(default_factory=list)


def normalise(text: str) -> str:
    t = text.lower()
    for ch in "–—−‐":
        t = t.replace(ch, "-")
    t = t.replace("’", "'")
    return re.sub(r"[ \t]+", " ", t)


def _blank(s: str, spans) -> str:
    """Replace spans with spaces (keeps positions) so dates are not read as counts."""
    chars = list(s)
    for a, b in spans:
        for k in range(a, b):
            chars[k] = " "
    return "".join(chars)


def _year_for(d_month: int, d_day: int, today: date, year: int | None) -> date | None:
    try:
        if year is not None:
            return date(year + 2000 if year < 100 else year, d_month, d_day)
        return date(today.year, d_month, d_day)
    except ValueError:
        return None


def find_expiries(s: str, today: date) -> list[tuple[int, int, Expiry]]:
    """All expiry expressions in s with their spans."""
    out = []
    for m in DATE_NUM_RE.finditer(s):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        rd = _year_for(mo, d, today, int(y) if y else None) if 1 <= mo <= 12 else None
        if rd:
            out.append((m.start(), m.end(), Expiry("absolute_date", rd.isoformat(), rd)))
    for rx, dm in ((DATE_DM_RE, True), (DATE_MD_RE, False)):
        for m in rx.finditer(s):
            day, mon = (m.group(1), m.group(2)) if dm else (m.group(2), m.group(1))
            rd = _year_for(MONTHS[mon[:3]], int(day), today, None)
            if rd:
                out.append((m.start(), m.end(), Expiry("absolute_date", rd.isoformat(), rd)))
    for rx, off, name in REL:
        for m in rx.finditer(s):
            if not any(a <= m.start() < b for a, b, _ in out):
                out.append((m.start(), m.end(), Expiry("relative_day", name, today + timedelta(days=off))))
    for m in WEEKDAY_RE.finditer(s):
        idx = next(i for i, w in enumerate(WEEKDAYS) if w.startswith(m.group(1)[:3]))
        rd = today + timedelta(days=(idx - today.weekday()) % 7)
        out.append((m.start(), m.end(), Expiry("weekday", WEEKDAYS[idx], rd)))
    out.sort(key=lambda x: x[0])
    return out


def _group_of(m) -> str:
    abo, sign = m.group(1).upper(), m.group(2)
    return abo + ("-" if ("-" in sign or "neg" in sign) else "+")


def _count_in(window: str, gpos: int) -> int | None:
    """Count after the group (preferred) else just before it. 0 for nil/none."""
    after, before = window[gpos:], window[:gpos]
    for part, pick in ((after, 0), (before, -1)):
        if ZERO_RE.search(part):
            return 0
        found = [m for m in COUNT_RE.finditer(part)]
        if found:
            tok = found[pick].group(1)
            return int(tok) if tok.isdigit() else WORD_NUM[tok]
    return None


def parse(text: str, today: date, sender_centre_letter: str | None = None) -> ParseResult:
    s = normalise(text)
    flags: list[str] = []
    notes: list[str] = []
    expiries = find_expiries(s, today)
    no_dates = _blank(s, [(a, b) for a, b, _ in expiries])
    comps = {"SDP" for _ in SDP_RE.finditer(s)} | {"RDP" for _ in RDP_RE.finditer(s)}
    msg_component = next(iter(comps)) if len(comps) == 1 else None

    # group mentions (signed, then unsigned = unknown group)
    hits = [(m.start(), m.end(), _group_of(m)) for m in GROUP_RE.finditer(no_dates)]
    for m in UNSIGNED_RE.finditer(no_dates):
        a = m.start()
        if not any(x <= a < y for x, y, _ in hits):
            hits.append((a, m.end(), None))
    hits.sort()

    # segment boundaries: punctuation / newlines / "and" separate items
    bounds = sorted({0, len(s)} | {m.end() for m in re.finditer(r"[,;\n]|\band\b|\baur\b|&", s)})

    def seg_of(pos):
        lo = max(b for b in bounds if b <= pos)
        hi = min(b for b in bounds if b > pos)
        return lo, hi

    def tagged(i):
        """An expiry phrase next to an expiry word ("exp 17/10", "kal tak") beats a bare one ("aaj 2 ...")."""
        ea, eb, _ = expiries[i]
        return bool(EXPIRY_WORD_RE.search(s[max(0, ea - 12):min(len(s), eb + 12)]))

    def global_(i):
        return bool(ALL_RE.search(s[max(0, expiries[i][0] - 15):expiries[i][0]]))

    items: list[Item] = []
    item_exp: list[int | None] = []      # index into `expiries` of each item's own expiry
    used = set()
    for k, (a, b, grp) in enumerate(hits):
        lo, hi = seg_of(a)
        lo = max(lo, hits[k - 1][1] if k and hits[k - 1][0] >= lo else lo)
        hi = min(hi, hits[k + 1][0] if k + 1 < len(hits) and hits[k + 1][0] < hi else hi)
        count = _count_in(no_dates[lo:hi], b - lo)
        comp_here = SDP_RE.search(s[lo:hi]) and "SDP" or (RDP_RE.search(s[lo:hi]) and "RDP") or msg_component
        here = sorted((i for i, (ea, _, _) in enumerate(expiries) if lo <= ea < hi and i not in used),
                      key=lambda i: not tagged(i))
        idx = here[0] if here else None
        if idx is not None:
            used.add(idx)
        if count == 0:
            notes.append(f"{grp or 'unknown group'} reported as nil; row dropped")
            continue
        items.append(Item(grp, comp_here, count, expiries[idx][2] if idx is not None else None,
                          text_span(text, lo, hi)))
        item_exp.append(idx)

    is_shortfall = bool(SHORTFALL_RE.search(s))
    mtype = "other" if not items else ("shortfall" if is_shortfall else "stock_post")

    if mtype == "stock_post" and expiries:
        if len(items) == 1:
            # one item: an expiry next to an expiry word anywhere beats a bare one ("aaj 2 ..., kal tak")
            best = min(range(len(expiries)), key=lambda i: (not tagged(i), i))
            cur = item_exp[0]
            if cur is None or (not tagged(cur) and tagged(best)):
                items[0].expiry = expiries[best][2]
        else:
            # "all expire 18/10", "sab parso tak": applies to every item without its own expiry
            glob = [i for i in range(len(expiries)) if global_(i)]
            if glob:
                for it, idx in zip(items, item_exp):
                    if idx is None or idx == glob[0]:
                        it.expiry = expiries[glob[0]][2]

    for it in items:
        it.flags = item_flags(it, mtype, today)

    if not items:
        flags.append("no_items")
    letters = set(CENTRE_RE.findall(s))
    if sender_centre_letter and letters - {sender_centre_letter.lower()}:
        flags.append("centre_mismatch")
    if PATIENT_RE.search(s):
        flags.append("possible_patient_data")
    return ParseResult(mtype, items, flags, notes)


def text_span(text: str, lo: int, hi: int) -> str:
    return text[lo:hi].strip(" ,;\n")


def item_flags(it: Item, message_type: str, today: date) -> list[str]:
    """Post-checks shared by both parser paths (PARSER_SPEC.md section 4)."""
    f = []
    if it.abo_rh not in GROUPS:
        f.append("unknown_group")
    if it.count is None or it.count < 1:
        f.append("count_missing")
    if it.component is None:
        f.append("component_assumed")
    if message_type == "stock_post":
        if it.expiry is None or it.expiry.resolved_date is None:
            f.append("expiry_missing")
        else:
            if it.expiry.kind in ("relative_day", "weekday"):
                f.append("expiry_relative")
            if it.expiry.resolved_date < today:
                f.append("expiry_in_past")
    return f


def resolve_expiry(kind: str, value: str | None, today: date) -> Expiry | None:
    """Turn an extracted (kind, value) into a dated Expiry. Used for LLM output so dates are never model-made."""
    if kind == "none" or not value:
        return None
    if kind == "relative_day":
        off = {"today": 0, "tomorrow": 1, "day_after_tomorrow": 2}.get(value)
        return None if off is None else Expiry(kind, value, today + timedelta(days=off))
    if kind == "weekday":
        v = value.lower()
        if v not in WEEKDAYS:
            return None
        return Expiry(kind, v, today + timedelta(days=(WEEKDAYS.index(v) - today.weekday()) % 7))
    if kind == "absolute_date":
        try:
            d = date.fromisoformat(value)
        except ValueError:
            return None
        return Expiry(kind, d.isoformat(), d)
    return None


def scan_message_flags(text: str, sender_centre_letter: str | None) -> list[str]:
    s = normalise(text)
    flags = []
    letters = set(CENTRE_RE.findall(s))
    if sender_centre_letter and letters - {sender_centre_letter.lower()}:
        flags.append("centre_mismatch")
    if PATIENT_RE.search(s):
        flags.append("possible_patient_data")
    return flags
