"""Parser accuracy on the synthetic labelled set (docs/PARSER_SPEC.md section 6).

    python scripts/parser_eval.py --split preview            # generated messages only; checks the pipeline; NOT reportable
    python scripts/parser_eval.py --split dev  [--parser rules|llm|both]
    python scripts/parser_eval.py --split test [--parser rules|llm|both]   # needs the frozen split AND frozen targets

Metrics are ratios of totals over messages with 95% bootstrap CIs (B = 10,000, random.Random(7)), reported overall
and separately for hand-written and generated messages. Writes scripts/out/parser_eval_<split>_<time>.json and .md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.config import Settings  # noqa: E402
from app.services import parser  # noqa: E402
from app.services.errors import DomainError  # noqa: E402
import parser_split as ps  # noqa: E402

OUT = ROOT / "scripts" / "out"
TARGETS = ROOT / "backend" / "tests" / "parser" / "targets.json"
B = 10_000
METRICS = ["item_exact", "item_precision", "group_acc", "count_acc", "expiry_acc", "component_acc", "type_acc",
           "message_exact", "critical_error_rate", "human_check_rate", "fallback_rate"]


def norm_items(items, mtype, pred=False):
    out = []
    for i in items:
        exp = None if mtype != "stock_post" else (
            (i.get("expiry") or {}).get("resolved_date") if pred else i.get("expiry_date"))
        out.append((i.get("abo_rh"), i.get("component") or "RDP", i.get("count"), exp))
    return out


def score(gold: dict, payload: dict) -> dict:
    gtype = gold["message_type"]
    g = norm_items(gold["items"], gtype)
    p = norm_items(payload["items"], gtype, pred=True)
    exact = sum((Counter(g) & Counter(p)).values())
    groups = sum((Counter(x[0] for x in g) & Counter(x[0] for x in p)).values())
    # align by group, in order, for field accuracy
    pool = list(p)
    aligned = []
    for x in g:
        m = next((y for y in pool if y[0] == x[0]), None)
        if m:
            pool.remove(m)
            aligned.append((x, m))
    # critical error: a wrong group/count that could be committed with no flag
    blocking_msg = bool(set(payload["message_flags"]) & (parser.pr.BLOCKING | {"unknown_sender"}))
    gold_gc = Counter((x[0], x[2]) for x in g)
    critical = 0
    for it in payload["items"]:
        key = (it.get("abo_rh"), it.get("count"))
        if gold_gc[key] > 0:
            gold_gc[key] -= 1
        elif not it["flags"] and not blocking_msg and payload["message_type"] != "other":
            critical = 1
    n_exp = sum(1 for x, _ in aligned if gtype == "stock_post")
    return dict(
        n_gold=len(g), n_pred=len(p), exact=exact, groups=groups, n_aligned=len(aligned),
        count_ok=sum(x[2] == y[2] for x, y in aligned), comp_ok=sum(x[1] == y[1] for x, y in aligned),
        n_exp=n_exp, exp_ok=sum(x[3] == y[3] for x, y in aligned if gtype == "stock_post"),
        type_ok=int(payload["message_type"] == gtype),
        msg_exact=int(payload["message_type"] == gtype and Counter(g) == Counter(p)),
        critical=critical, human_check=int(bool(payload["needs_review"])),
        fallback=int(any("fell back" in n for n in payload.get("notes", []))))


def aggregate(rows: list[dict]) -> dict:
    def tot(k):
        return sum(r[k] for r in rows)

    def ratio(a, b):
        return None if b == 0 else a / b
    n = len(rows)
    return dict(item_exact=ratio(tot("exact"), tot("n_gold")), item_precision=ratio(tot("exact"), tot("n_pred")),
                group_acc=ratio(tot("groups"), tot("n_gold")), count_acc=ratio(tot("count_ok"), tot("n_aligned")),
                expiry_acc=ratio(tot("exp_ok"), tot("n_exp")), component_acc=ratio(tot("comp_ok"), tot("n_aligned")),
                type_acc=ratio(tot("type_ok"), n), message_exact=ratio(tot("msg_exact"), n),
                critical_error_rate=ratio(tot("critical"), n), human_check_rate=ratio(tot("human_check"), n),
                fallback_rate=ratio(tot("fallback"), n))


def bootstrap(rows: list[dict]) -> dict:
    rng = random.Random(7)
    n = len(rows)
    samples = {m: [] for m in METRICS}
    for _ in range(B):
        res = aggregate([rows[rng.randrange(n)] for _ in range(n)])
        for m in METRICS:
            if res[m] is not None:
                samples[m].append(res[m])
    ci = {}
    for m, v in samples.items():
        v.sort()
        ci[m] = None if not v else [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]]
    return ci


def target_verdict(targets: dict | None, res: dict) -> list[str]:
    """PASS/FAIL against backend/tests/parser/targets.json (frozen at Checkpoint E). Failures are reported, not tuned."""
    out = []
    for metric, t in (targets or {}).get("pass_fail", {}).items():
        v = res["overall"].get(metric)
        ok = v is not None and v <= t["max"]
        out.append(f"{metric} = {'n/a' if v is None else f'{v:.1%}'} (max {t['max']:.0%}): {'PASS' if ok else 'FAIL'}")
    return out


def run_parser(msgs, mode, settings):
    rows, t0, failures = [], time.time(), []
    for x in msgs:
        try:
            payload = parser.parse_message(x["text"], x["sender_centre"], datetime.fromisoformat(x["as_of"]),
                                           settings, mode)
        except DomainError as e:
            sys.exit(f"{x['id']}: {e.message}")
        r = score(x["gold"], payload)
        r.update(id=x["id"], source=ps.source(x), lang=x["lang"])
        rows.append(r)
        if not r["msg_exact"]:
            failures.append(dict(id=x["id"], text=x["text"], gold=x["gold"],
                                 got=dict(message_type=payload["message_type"], items=payload["items"],
                                          flags=payload["needs_review"])))
    return rows, failures, time.time() - t0


def report(rows):
    out = dict(n=len(rows), overall=aggregate(rows), ci=bootstrap(rows) if rows else {})
    for key in ("source", "lang"):
        for val in sorted({r[key] for r in rows}):
            sub = [r for r in rows if r[key] == val]
            out[f"{key}={val}"] = dict(n=len(sub), metrics=aggregate(sub))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["preview", "dev", "test"], required=True)
    ap.add_argument("--parser", choices=["rules", "llm", "both"], default="rules")
    a = ap.parse_args()
    rows = ps.load_all()
    if a.split == "preview":
        msgs = [x for x in rows if ps.source(x) == "generated"]
        banner = "PREVIEW on generated messages only: checks the pipeline. NOT a reportable result."
    else:
        if not ps.SPLIT.exists():
            sys.exit("no frozen split yet: run scripts/parser_split.py --freeze after the hand-written set is in")
        split = json.loads(ps.SPLIT.read_text(encoding="utf-8"))
        if a.split == "test":
            want = ps.SHA.read_text(encoding="utf-8").strip()
            if hashlib.sha256(ps.canonical_test(rows, split["test"]).encode()).hexdigest() != want:
                sys.exit("test split changed since it was frozen; refusing to score")
            if not TARGETS.exists():
                sys.exit("targets not frozen: write backend/tests/parser/targets.json at Checkpoint E first")
            if hashlib.sha256(TARGETS.read_bytes()).hexdigest() != split.get("targets_sha256"):
                sys.exit("targets.json changed since the split was frozen; refusing to score")
        ids = set(split[a.split])
        msgs = [x for x in rows if x["id"] in ids]
        banner = f"{a.split} split, {len(msgs)} synthetic messages"
    modes = ["rules", "llm"] if a.parser == "both" else [a.parser]
    settings = Settings()
    if "llm" in modes and not settings.llm_key_present:
        sys.exit("ANTHROPIC_API_KEY not set: cannot run the LLM parser (Q4)")
    result = dict(banner=banner, split=a.split, generated_at=datetime.now().isoformat(timespec="seconds"),
                  targets=json.loads(TARGETS.read_text()) if TARGETS.exists() else None, parsers={})
    for mode in modes:
        rows_m, failures, secs = run_parser(msgs, mode, settings)
        result["parsers"][mode] = dict(report(rows_m), seconds=round(secs, 2), failures=failures,
                                       model=settings.llm_model if mode == "llm" else None)
    OUT.mkdir(exist_ok=True)
    stem = OUT / f"parser_eval_{a.split}_{datetime.now():%Y%m%d_%H%M%S}"
    lines = [f"# Parser evaluation: {banner}", ""]
    for mode, res in result["parsers"].items():
        lines += [f"## Parser: {mode} ({res['n']} messages, {res['seconds']} s)", "",
                  "| Metric | Overall [95% CI] | " + " | ".join(k for k in res if "=" in k) + " |",
                  "|---|---|" + "---|" * sum("=" in k for k in res)]
        for m in METRICS:
            v, ci = res["overall"][m], res["ci"].get(m)
            cell = "—" if v is None else f"{v:.1%}" + (f" [{ci[0]:.1%}, {ci[1]:.1%}]" if ci else "")
            subs = [("—" if res[k]["metrics"][m] is None else f"{res[k]['metrics'][m]:.1%}") + f" (n={res[k]['n']})"
                    for k in res if "=" in k]
            lines.append(f"| {m} | {cell} | " + " | ".join(subs) + " |")
        lines += ["", f"Messages not read exactly: {len(res['failures'])} (details in the JSON file).", ""]
        verdict = target_verdict(result["targets"], res) if a.split == "test" else None
        if verdict:
            res["verdict"] = verdict
            lines += [f"**Frozen target** {v}" for v in verdict] + [""]
    stem.with_suffix(".json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    stem.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"written: {stem}.json / .md")


if __name__ == "__main__":
    main()
