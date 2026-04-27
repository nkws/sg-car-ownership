"""Decision rule for the Verdict panel.

Pure function that combines:
  - COE market state from coe_reversal.detect_reversal
  - User's stressed cost-to-income ratio (computed by the caller)
  - Composite FSI score
  - User-overridable thresholds

…and returns a single Verdict — headline + recommendation + chip details.

Heuristic only. The caller is responsible for showing a "not financial
advice" caveat in the UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict


Recommendation = Literal["Wait", "Caution", "Proceed with caution"]

# COE reversal states from models/coe_reversal.py, ordered worst → best.
# Anything at POSSIBLE or beyond is treated as "market stress", which
# alone is enough to flip the verdict to Wait regardless of personal ratio.
_MARKET_STRESS_STATES = {"POSSIBLE", "LIKELY", "CONFIRMED"}
_MARKET_STABLE_STATES = {"STABLE"}


class Verdict(TypedDict):
    recommendation: Recommendation
    headline: str

    # Three explainer chips
    market_state: str          # e.g. "WATCH"
    market_reason: str         # one-line summary from coe_reversal
    stress_ratio: float        # 0.0–∞, e.g. 0.38 = 38% of income
    fsi_score: float           # 0–100
    fsi_arrow: str             # "↑", "↓", "→" — direction vs previous


def _direction(current: float, previous: float | None, eps: float = 0.5) -> str:
    """Return ↑ / ↓ / → comparing current FSI to a previous reading."""
    if previous is None:
        return "→"
    if current - previous > eps:
        return "↑"
    if previous - current > eps:
        return "↓"
    return "→"


def compute_verdict(
    *,
    market_state: str,
    market_reason: str,
    stress_ratio: float,
    fsi_score: float,
    previous_fsi: float | None,
    threshold_wait: float,
    threshold_proceed: float,
) -> Verdict:
    """Apply the decision rule.

    Rule:
      stress_ratio ≥ threshold_wait                  → Wait
      market_state in {POSSIBLE, LIKELY, CONFIRMED}  → Wait
      stress_ratio ≤ threshold_proceed AND market STABLE → Proceed with caution
      otherwise                                       → Caution
    """
    if stress_ratio >= threshold_wait or market_state in _MARKET_STRESS_STATES:
        recommendation: Recommendation = "Wait"
    elif (
        stress_ratio <= threshold_proceed
        and market_state in _MARKET_STABLE_STATES
    ):
        recommendation = "Proceed with caution"
    else:
        recommendation = "Caution"

    headline = (
        f"Market: {market_state} · "
        f"Your stress-tested ratio: {stress_ratio:.0%} · "
        f"Recommendation: {recommendation}"
    )

    return Verdict(
        recommendation=recommendation,
        headline=headline,
        market_state=market_state,
        market_reason=market_reason,
        stress_ratio=stress_ratio,
        fsi_score=fsi_score,
        fsi_arrow=_direction(fsi_score, previous_fsi),
    )
