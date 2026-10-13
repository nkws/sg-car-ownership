"""Load intel briefs and score past evidence leans. See intel/README.md."""

from __future__ import annotations

import json
from pathlib import Path

BRIEFS_PATH = Path(__file__).parent / "briefs.json"
BAND = 2.0  # ±% treated as flat


def load() -> list[dict]:
    if not BRIEFS_PATH.exists():
        return []
    briefs = json.loads(BRIEFS_PATH.read_text()).get("briefs", [])
    return sorted(briefs, key=lambda b: b["date"], reverse=True)


def verdict(lean: str, return_pct: float) -> str:
    """Score one lean against the benchmark's return over the check window."""
    if lean == "mixed":
        return "unscored"
    if abs(return_pct) <= BAND:
        return "flat"
    went_up = return_pct > 0
    return "right" if went_up == (lean == "bullish") else "wrong"


def scored_sections(briefs: list[dict]) -> list[dict]:
    rows = []
    for b in briefs:
        for s in b.get("sections", []):
            r = s.get("result")
            if r and r.get("verdict") in ("right", "wrong", "flat"):
                rows.append({"date": b["date"], **s, "result": r})
    return rows


def hit_rate(rows: list[dict]) -> tuple[float, int] | None:
    """Share of right calls among right+wrong (flat excluded)."""
    decided = [r for r in rows if r["result"]["verdict"] in ("right", "wrong")]
    if not decided:
        return None
    return sum(r["result"]["verdict"] == "right" for r in decided) / len(decided), len(decided)
