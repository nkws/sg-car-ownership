"""Alerting — closes the loop on the fsi_signal.json the pipeline already writes.

Reads the signal file and fires a notification when something actionable
changes: an FSI stress alert appears, Cat A closes below the buy trigger, or the
overall stress band shifts. State is remembered between runs so an unchanged
situation does not re-notify.

Channels:
  - Telegram, when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.
  - Otherwise log-only (prints what it *would* send and sends nothing).

This is intended to run after run_pipeline.py, e.g. from the daily GitHub
Action in .github/workflows/daily-pipeline.yml.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SIGNAL_FILE, DATA_DIR, COE_BUY_TRIGGER_CAT_A

NOTIFY_STATE_FILE = DATA_DIR / "notify_state.json"


def _latest_cat_a() -> float | None:
    """Latest Cat A premium, via the COE loader (falls back to bundled data)."""
    try:
        from analysis.coe_market import _load_recent_premiums
        data = _load_recent_premiums()
        return float(data[-1]["catA"]) if data else None
    except Exception:
        return None


def _fsi_band(score: float) -> str:
    if score < 30:
        return "Low"
    if score < 45:
        return "Moderate"
    if score < 60:
        return "Elevated"
    if score < 75:
        return "High"
    return "Critical"


def build_notification(signal: dict) -> tuple[str, dict]:
    """Return (message, state). State is the dedupe key for "did anything change?"."""
    fsi = signal.get("fsi_score", 0)
    band = _fsi_band(fsi)
    alerts = signal.get("alerts", [])
    cat_a = _latest_cat_a()
    below_trigger = cat_a is not None and cat_a < COE_BUY_TRIGGER_CAT_A

    lines = [f"🚗 SG Car Ownership — FSI {fsi:.0f}/100 ({band})"]
    if cat_a is not None:
        mark = "✅ below" if below_trigger else "above"
        lines.append(f"Cat A latest: ${cat_a:,.0f} ({mark} ${COE_BUY_TRIGGER_CAT_A:,} trigger)")
    if alerts:
        lines.append("Alerts:")
        lines.extend(f"  • {a}" for a in alerts)

    message = "\n".join(lines)
    state = {
        "fsi_band": band,
        "below_trigger": below_trigger,
        "alerts": sorted(alerts),
    }
    return message, state


def _load_prev_state() -> dict | None:
    if NOTIFY_STATE_FILE.exists():
        try:
            with open(NOTIFY_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _save_state(state: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(NOTIFY_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    import requests
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=20,
    )
    resp.raise_for_status()
    return True


def run(force: bool = False) -> int:
    """Evaluate the signal and notify if state changed. Returns 0/1 like a CLI."""
    if not SIGNAL_FILE.exists():
        print(f"notify: no signal file at {SIGNAL_FILE}; run run_pipeline.py first")
        return 1

    with open(SIGNAL_FILE) as f:
        signal = json.load(f)

    message, state = build_notification(signal)
    prev = _load_prev_state()

    if not force and prev == state:
        print("notify: no change since last run — nothing to send")
        print(message)
        return 0

    sent = _send_telegram(message)
    if sent:
        print("notify: sent via Telegram")
    else:
        print("notify: no channel configured (set TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID) "
              "— would have sent:")
    print(message)

    _save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(run(force="--force" in sys.argv))
