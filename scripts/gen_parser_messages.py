"""Generate the template-based part of the synthetic parser test set (docs/PARSER_SPEC.md 6.1).

    python scripts/gen_parser_messages.py        # writes backend/tests/parser/data/generated.jsonl

90 messages: about 70% stock posts, 20% shortfalls, 10% other; English and Hinglish. Gold labels come from the
template parameters. Some templates use phrasings the rule parser is not written for ("zarurat hai", "please
arrange", "nos", "bags of"), on purpose. Written by Claude Code, so results on this subset are reported separately
from the hand-written subset and are weak evidence on their own.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "backend" / "tests" / "parser" / "data" / "generated.jsonl"
SEED = 20261016
AS_OF = "2026-10-16T08:10:00+05:30"
TODAY = date(2026, 10, 16)
CENTRES = ["C-A", "C-B", "C-C", "C-D", "C-E", "C-F", "C-G", "C-H"]
GROUPS = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
WEIGHTS = [34, 3, 22, 2, 30, 2, 6, 1]          # roughly the West-region shares, so common groups dominate
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
HI_NUM = {1: "ek", 2: "do", 3: "teen", 4: "char", 5: "paanch"}
EN_NUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def gword(r, g, style=None):
    abo, sign = g[:-1], g[-1]
    style = style or r.choice(["sym", "sym", "pos", "long", "ve"])
    if style == "sym":
        return g
    if style == "pos":
        return f"{abo} {'pos' if sign == '+' else 'neg'}"
    if style == "long":
        return f"{abo} {'positive' if sign == '+' else 'negative'}"
    return f"{abo}{sign}ve"


def date_words(r, d: date):
    style = r.choice(["slash", "dot", "mon", "th"])
    if style == "slash":
        return f"{d.day}/{d.month}"
    if style == "dot":
        return f"{d.day:02d}.{d.month:02d}"
    if style == "mon":
        return f"{d.day} {MON[d.month - 1].capitalize()}"
    suf = "th" if 10 <= d.day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    return f"{d.day}{suf} {MON[d.month - 1]}"


def item(g, n, comp="RDP", exp=None):
    return {"abo_rh": g, "component": comp, "count": n, "expiry_date": exp.isoformat() if exp else None}


def stock_en(r):
    g, n = r.choices(GROUPS, WEIGHTS)[0], r.randint(1, 5)
    d = TODAY + timedelta(days=r.randint(0, 4))
    t = r.randrange(8)
    if t == 0:
        comp = r.choice(["RDP", "SDP"])
        return f"{g} {comp} x{n} exp {date_words(r, d)}", [item(g, n, comp, d)]
    if t == 1:
        return f"{gword(r, g)} {n} units expiring {date_words(r, d)}", [item(g, n, "RDP", d)]
    if t == 2:
        g2 = r.choice([x for x in GROUPS[:5:2] if x != g] or ["A+"])
        n2 = r.randint(1, 4)
        d1, d2 = TODAY + timedelta(days=1), TODAY + timedelta(days=2)
        return (f"Platelets available: {g} {n} (expire tomorrow), {g2} {n2} (expire {date_words(r, d2)})",
                [item(g, n, "RDP", d1), item(g2, n2, "RDP", d2)])
    if t == 3:
        wd = r.randint(0, 6)
        dd = TODAY + timedelta(days=(wd - TODAY.weekday()) % 7)
        return f"{EN_NUM[n]} {gword(r, g, 'long')} platelets, expiry {WEEKDAYS[wd].capitalize()}", [item(g, n, "RDP", dd)]
    if t == 4:
        return f"{g} - {n} nos - exp {d.day:02d}.{d.month:02d}", [item(g, n, "RDP", d)]
    if t == 5:
        g2 = r.choice([x for x in ["O+", "A+", "B+", "AB+"] if x != g])
        n2 = r.randint(1, 3)
        return (f"Stock update: {g} {n}, {g2} {n2}, all expire {d.day}/{d.month}",
                [item(g, n, "RDP", d), item(g2, n2, "RDP", d)])
    if t == 6:
        return f"{n} bags of {g} apheresis expiring on {date_words(r, d)}", [item(g, n, "SDP", d)]
    wd = r.randint(0, 6)
    dd = TODAY + timedelta(days=(wd - TODAY.weekday()) % 7)
    return f"{g} ({n}) valid till {WEEKDAYS[wd].capitalize()}", [item(g, n, "RDP", dd)]


def stock_hi(r):
    g, n = r.choices(GROUPS, WEIGHTS)[0], r.randint(1, 5)
    rel, off = r.choice([("kal", 1), ("aaj", 0), ("parso", 2)])
    d = TODAY + timedelta(days=off)
    t = r.randrange(5)
    if t == 0:
        return f"{g} {n} unit {rel} expire", [item(g, n, "RDP", d)]
    if t == 1:
        return f"aaj {HI_NUM[n]} {gword(r, g, 'pos')} platelet bacha hai, {rel} tak", [item(g, n, "RDP", d)]
    if t == 2:
        return f"{g} ke {n} unit {rel} expire honge", [item(g, n, "RDP", d)]
    if t == 3:
        g2 = r.choice([x for x in ["O+", "A+", "B+"] if x != g])
        n2 = r.randint(1, 4)
        return (f"{HI_NUM[n]} {g} aur {HI_NUM[n2]} {g2} hai, sab {rel} tak",
                [item(g, n, "RDP", d), item(g2, n2, "RDP", d)])
    d2 = TODAY + timedelta(days=r.randint(1, 4))
    return f"hamare paas {g} {n} unit hai, expiry {d2.day}/{d2.month}", [item(g, n, "RDP", d2)]


def shortfall(r, lang):
    g, n = r.choices(GROUPS, WEIGHTS)[0], r.randint(1, 4)
    comp = r.choice(["RDP", "RDP", "SDP"])
    if lang == "en":
        t = r.randrange(3)
        if t == 0:
            return f"Need {n} {g} platelets urgently", [item(g, n, "RDP")]
        if t == 1:
            return f"Requirement: {g} {comp} {n} units", [item(g, n, comp)]
        return f"Please arrange {n} units {gword(r, g)} {comp}", [item(g, n, comp)]
    t = r.randrange(2)
    if t == 0:
        return f"humko {HI_NUM[n]} {gword(r, g, 'pos')} {comp} chahiye", [item(g, n, comp)]
    return f"{g} ki {n} unit ki zarurat hai", [item(g, n, "RDP")]


OTHER = {"en": ["Good morning sir", "Ok noted, thanks", "Thank you, units received", "Will call you in 10 min",
                "Is the courier on the way?"],
         "hinglish": ["Kal call karta hoon", "Stock update baad mein bhejte hain", "Theek hai sir",
                      "Courier nikal gaya kya?"]}


def main():
    r = random.Random(SEED)
    plan = ([("stock", "en")] * 38 + [("stock", "hinglish")] * 25 + [("shortfall", "en")] * 10 +
            [("shortfall", "hinglish")] * 8 + [("other", "en")] * 5 + [("other", "hinglish")] * 4)
    rows = []
    for n, (kind, lang) in enumerate(plan, 1):
        if kind == "stock":
            text, items = (stock_en if lang == "en" else stock_hi)(r)
            mtype = "stock_post"
        elif kind == "shortfall":
            (text, items), mtype = shortfall(r, lang), "shortfall"
        else:
            text, items, mtype = r.choice(OTHER[lang]), [], "other"
        rows.append(dict(id=f"g-{n:03d}", author="generated:templates", lang=lang, as_of=AS_OF,
                         sender_centre=r.choice(CENTRES), text=text, gold=dict(message_type=mtype, items=items)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    print(f"wrote {len(rows)} messages to {OUT}")


if __name__ == "__main__":
    main()
