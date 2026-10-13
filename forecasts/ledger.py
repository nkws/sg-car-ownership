"""Forecast ledger: load, save and score.

The ledger is a single JSON file committed to this repo (forecasts/ledger.json),
so it survives Streamlit Cloud restarts and Claude's scheduled tasks can edit it
with a normal git commit. See forecasts/README.md for the schema.

Saving from the dashboard:
  * If st.secrets has a `github_token` (fine-grained PAT, Contents: read/write on
    this repo), the page commits ledger.json through the GitHub API.
  * Otherwise it writes the local file (works when running on the Mac).
"""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

import requests

LEDGER_PATH = Path(__file__).parent / "ledger.json"
REPO = "nkws/sg-car-ownership"
REPO_FILE = "forecasts/ledger.json"
BRANCH = "main"

STATUSES = ("proposed", "active", "resolved", "rejected")


# ─── Load / save ──────────────────────────────────────────────────────────────

def load_local() -> dict:
    if not LEDGER_PATH.exists():
        return {"version": 1, "forecasts": []}
    return json.loads(LEDGER_PATH.read_text())


def _dump(ledger: dict) -> str:
    return json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"


def load_remote(token: str) -> tuple[dict, str]:
    """Fetch the ledger from GitHub. Returns (ledger, sha)."""
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/contents/{REPO_FILE}",
        params={"ref": BRANCH},
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    return json.loads(base64.b64decode(body["content"])), body["sha"]


def save_remote(ledger: dict, sha: str, token: str, message: str) -> str:
    """Commit the ledger. Raises on conflict (someone else committed first)."""
    r = requests.put(
        f"https://api.github.com/repos/{REPO}/contents/{REPO_FILE}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        json={"message": message,
              "content": base64.b64encode(_dump(ledger).encode()).decode(),
              "sha": sha, "branch": BRANCH},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["content"]["sha"]


def save_local(ledger: dict) -> None:
    LEDGER_PATH.write_text(_dump(ledger))


# ─── Scoring ──────────────────────────────────────────────────────────────────

def brier(p: float, outcome: bool) -> float:
    """Brier score for one binary forecast. 0 = perfect, 0.25 = coin flip."""
    return (p - (1.0 if outcome else 0.0)) ** 2


def scored(forecasts: list[dict], key: str = "claude_p") -> list[tuple[float, bool]]:
    return [(f[key], f["outcome"]) for f in forecasts
            if f.get("status") == "resolved"
            and f.get(key) is not None
            and isinstance(f.get("outcome"), bool)]


def mean_brier(forecasts: list[dict], key: str = "claude_p") -> float | None:
    pairs = scored(forecasts, key)
    if not pairs:
        return None
    return sum(brier(p, o) for p, o in pairs) / len(pairs)


def head_to_head(forecasts: list[dict], a: str, b: str) -> tuple[float, float, int] | None:
    """Mean Brier for forecaster `a` vs `b` on resolved rows where both gave a number."""
    both = [f for f in forecasts
            if f.get("status") == "resolved" and isinstance(f.get("outcome"), bool)
            and f.get(a) is not None and f.get(b) is not None]
    if not both:
        return None
    sa = sum(brier(f[a], f["outcome"]) for f in both) / len(both)
    sb = sum(brier(f[b], f["outcome"]) for f in both) / len(both)
    return sa, sb, len(both)


CAL_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001)]


def calibration(forecasts: list[dict], key: str = "claude_p") -> list[dict]:
    """Per probability bucket: average stated probability vs how often it happened."""
    pairs = scored(forecasts, key)
    rows = []
    for lo, hi in CAL_BINS:
        bucket = [(p, o) for p, o in pairs if lo <= p < hi]
        if bucket:
            rows.append({
                "bucket": f"{int(lo*100)}–{min(int(hi*100), 100)}%",
                "said": sum(p for p, _ in bucket) / len(bucket),
                "happened": sum(o for _, o in bucket) / len(bucket),
                "n": len(bucket),
            })
    return rows


def overdue(forecasts: list[dict], today: date | None = None) -> list[dict]:
    today = today or date.today()
    return [f for f in forecasts
            if f.get("status") == "active"
            and date.fromisoformat(f["resolve_by"]) < today]
