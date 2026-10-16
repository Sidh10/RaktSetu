"""Split the synthetic parser messages into dev / test and freeze the test split (docs/PARSER_SPEC.md 6.1).

    python scripts/parser_split.py            # check the data and show what the split would be
    python scripts/parser_split.py --freeze   # write split.json and test_set.sha256 (once, before any test score)

Refuses to freeze until at least 60 hand-written messages exist, and refuses to overwrite an existing freeze.
Stratified by (source: human / generated, language, message type); 50 dev / 100 test when 150 messages exist,
otherwise one third dev.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "tests" / "parser" / "data"
SPLIT = DATA / "split.json"
SHA = ROOT / "backend" / "tests" / "parser" / "test_set.sha256"
TARGETS = ROOT / "backend" / "tests" / "parser" / "targets.json"
MIN_HANDWRITTEN = 60
GROUPS = {"O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", None}


def load_all() -> list[dict]:
    rows, errors = [], []
    for f in sorted(DATA.glob("*.jsonl")):
        if f.name == "handwritten_TEMPLATE.jsonl":
            continue
        for k, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                x = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{f.name}:{k}: bad JSON ({e})")
                continue
            if str(x.get("id", "")).startswith("example-"):
                continue
            errors += [f"{f.name}:{k}: {e}" for e in validate(x)]
            x["_file"] = f.name
            rows.append(x)
    ids = [x["id"] for x in rows]
    errors += [f"duplicate id {i}" for i in {i for i in ids if ids.count(i) > 1}]
    if errors:
        sys.exit("data errors:\n  " + "\n  ".join(errors))
    return rows


def validate(x: dict) -> list[str]:
    e = []
    for k in ("id", "author", "lang", "as_of", "sender_centre", "text", "gold"):
        if k not in x:
            e.append(f"missing {k}")
    g = x.get("gold", {})
    if g.get("message_type") not in ("stock_post", "shortfall", "other"):
        e.append("gold.message_type invalid")
    for it in g.get("items", []):
        if it.get("abo_rh") not in GROUPS:
            e.append(f"bad abo_rh {it.get('abo_rh')}")
        if it.get("component") not in ("RDP", "SDP"):
            e.append(f"bad component {it.get('component')}")
    if g.get("message_type") == "other" and g.get("items"):
        e.append("'other' must have no items")
    return e


def source(x: dict) -> str:
    return "human" if str(x.get("author", "")).startswith("human:") else "generated"


def canonical_test(rows: list[dict], test_ids: list[str]) -> str:
    by_id = {x["id"]: {k: v for k, v in x.items() if not k.startswith("_")} for x in rows}
    return json.dumps([by_id[i] for i in sorted(test_ids)], sort_keys=True, ensure_ascii=False)


def make_split(rows: list[dict]) -> dict:
    rng = random.Random(20261016)
    strata = defaultdict(list)
    for x in rows:
        strata[(source(x), x["lang"], x["gold"]["message_type"])].append(x["id"])
    n_dev = 50 if len(rows) >= 150 else len(rows) // 3
    frac = n_dev / len(rows)
    dev, test = [], []
    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        k = round(len(ids) * frac)
        dev += ids[:k]
        test += ids[k:]
    return dict(dev=sorted(dev), test=sorted(test))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    rows = load_all()
    n_h = sum(source(x) == "human" for x in rows)
    print(f"{len(rows)} messages: {n_h} hand-written, {len(rows) - n_h} generated")
    split = make_split(rows)
    print(f"split would be {len(split['dev'])} dev / {len(split['test'])} test")
    if not a.freeze:
        return
    if SPLIT.exists() or SHA.exists():
        sys.exit("already frozen; the test split must not change after freezing")
    if n_h < MIN_HANDWRITTEN:
        sys.exit(f"refusing to freeze: {n_h} hand-written messages, need at least {MIN_HANDWRITTEN} (task 4.1)")
    if not TARGETS.exists():
        sys.exit("refusing to freeze: targets must be frozen first (backend/tests/parser/targets.json)")
    split["targets_sha256"] = hashlib.sha256(TARGETS.read_bytes()).hexdigest()
    SPLIT.write_text(json.dumps(split, indent=1) + "\n", encoding="utf-8")
    SHA.write_text(hashlib.sha256(canonical_test(rows, split["test"]).encode()).hexdigest() + "\n", encoding="utf-8")
    print(f"frozen: {SPLIT.name}, {SHA.name}")


if __name__ == "__main__":
    main()
