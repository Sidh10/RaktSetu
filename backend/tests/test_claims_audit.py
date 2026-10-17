"""Claims audit (docs/CLAIMS_AND_LIMITS.md section 4, NFR-5): forbidden claims must not appear in anything a user,
judge or audience sees, and the required labels must be present. A forbidden phrase is allowed only right after a
negation ("not clinically validated", "no decay"). CLAIMS_AND_LIMITS.md and CLAUDE.md are not scanned: they quote
the phrases on purpose."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCANNED = (
    [p for p in (ROOT / "frontend" / "src").rglob("*") if p.suffix in (".js", ".jsx", ".css", ".html")]
    + [p for p in (ROOT / "backend" / "app").rglob("*.py")]
    + [ROOT / "data" / "seed" / "demo_city.json", ROOT / "README.md", ROOT / "docs" / "DEMO_SCRIPT.md"]
    + [p for p in [ROOT / "docs" / "REPORT_INSERTS.md", ROOT / "docs" / "PRESENTATION_RUNBOOK.md"] if p.exists()]
)

FORBIDDEN = {
    "clinical validation claimed": r"clinically (validated|safe|approved)|safe for clinical use",
    "probability shown": r"\bprobabilit(y|ies)\b|\bchance of (stock|finding)\b",
    "real messaging claimed": r"real[- ]time (whatsapp|sms|messag\w*|updates?|integration|stock)|live whatsapp|whatsapp (cloud api )?integration|integrated with whatsapp|sms gateway",
    "security claimed": r"\bsecure\b|\bauthenticated\b|real authentication",
    "production claimed": r"production[- ]ready|\bdeployed\b",
    "optimal matcher claimed": r"\boptimal\b|or-tools",
    "trust decay claimed": r"half-life|\bdecays?\b",
    "approval by authority claimed": r"(approved|validated|endorsed) by (a |the )?(specialist|nbtc|fda|dghs|sbtc|government)",
    "measured outcome claimed": r"reduces? (platelet )?wastage by|saves? \d+ (units|lives)",
    "failed targets claimed as passed": r"\bg[12] passed\b|met (all )?our targets",
}
NEGATION = re.compile(r"\b(not|no|never|nor|without|isn't|aren't|cannot|don't)\b[^.\n]{0,40}$", re.I)
SENTENCE_REST = re.compile(r"[^.!?\n]*(?:[.!?\n]|$)")


def hits(text: str):
    for name, pattern in FORBIDDEN.items():
        for m in re.finditer(pattern, text, re.I):
            before = text[max(0, m.start() - 45):m.start()]
            after = SENTENCE_REST.match(text[m.end():]).group(0)
            if NEGATION.search(before) or after.endswith("?"):      # negated, or asked as a question
                continue
            yield name, m.group(0), text[max(0, m.start() - 60):m.end() + 30].replace("\n", " ")


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_forbidden_claims(path):
    found = list(hits(path.read_text(encoding="utf-8")))
    assert not found, "\n".join(f"{n}: '{m}' in …{ctx}…" for n, m, ctx in found)


def test_zero_wasted_trips_always_says_by_design():
    for path in SCANNED:
        for m in re.finditer(r"0 wasted (courier )?trips", path.read_text(encoding="utf-8"), re.I):
            ctx = path.read_text(encoding="utf-8")[m.start():m.end() + 60]
            assert "by design" in ctx, f"{path.name}: '0 wasted trips' without 'by design'"


def test_auditor_catches_planted_claims():
    planted = ["The matching is clinically validated.", "Real-time WhatsApp updates from every centre.", "Probability in stock: 87%", "Live WhatsApp integration",
               "Secure login for staff", "Optimal matching with OR-Tools", "Trust decays with a half-life",
               "Approved by NBTC", "Reduces wastage by 40%", "G1 passed"]
    for s in planted:
        assert list(hits(s)), s
    for s in ["not clinically validated", "Demo users · not real authentication", "There is no decay",
              "Bands, never a probability", "no SMS gateway", "Is the matching clinically safe?",
              "built on real timestamps", "the clock runs in real time from the anchor"]:
        assert not list(hits(s)), s


def test_required_labels_present():
    app = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    for label in ("Simulated data", "mock channel", "not clinically validated", "Demo users · not real authentication"):
        assert label in app, label
    inbox = (ROOT / "frontend" / "src" / "components" / "Inbox.jsx").read_text(encoding="utf-8")
    assert "Mock channel" in inbox and "human check required" in inbox
    views = (ROOT / "backend" / "app" / "services" / "views.py").read_text(encoding="utf-8")
    assert "Call before travelling" in views and "simulated" in views
    finder = (ROOT / "frontend" / "src" / "components" / "Finder.jsx").read_text(encoding="utf-8")
    assert "%" not in re.sub(r"/\*.*?\*/|//.*", "", finder)          # no percentage typed into the public finder
