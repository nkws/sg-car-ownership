"""Decision rule for the Verdict panel.

Combines the forward-looking Decision Hurdle Index (models/decision_index.py)
with two hard safety vetoes:

  - personal affordability: a stress-tested ratio at/above ``threshold_wait``
    forces Wait regardless of how attractive timing looks;
  - market stress: a POSSIBLE+ COE reversal forces Wait.

The DHI band sets the baseline recommendation; the vetoes can only make it more
conservative, never less. This is the piece that was previously missing — the
old rule ignored the composite score entirely and branched on the ratio alone.

Heuristic only. The caller shows a "not financial advice" caveat in the UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from models.decision_index import DecisionScore


Recommendation = Literal["Wait", "Caution", "Proceed with caution"]

# Severity ordering — used to take the most conservative of band + vetoes.
_SEVERITY = {"Proceed with caution": 0, "Caution": 1, "Wait": 2}
_BY_SEVERITY = {v: k for k, v in _SEVERITY.items()}

# COE reversal states (models/coe_reversal.py) that count as market stress.
_MARKET_STRESS_STATES = {"POSSIBLE", "LIKELY", "CONFIRMED"}
_MARKET_STABLE_STATES = {"STABLE"}


class Verdict(TypedDict):
    recommendation: Recommendation
    headline: str

    # Decision Hurdle Index
    dhi: float                 # 0-100 composite
    dhi_band: str              # the DHI's own band before vetoes
    binding_hurdle: str        # label of the largest hurdle
    hurdles: list              # full sub-hurdle breakdown for display
    urgency: dict              # the urgency offset

    # Explainer chips
    market_state: str
    market_reason: str
    stress_ratio: float
    fsi_score: float
    fsi_arrow: str             # "↑" / "↓" / "→" vs previous reading


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
    decision: DecisionScore,
    market_state: str,
    market_reason: str,
    stress_ratio: float,
    fsi_score: float,
    previous_fsi: float | None,
    threshold_wait: float,
    threshold_proceed: float,
) -> Verdict:
    """Apply the decision rule: DHI band, made more conservative by vetoes.

    Rule:
      base = decision["band"]                              (from the DHI)
      veto Wait if stress_ratio ≥ threshold_wait           (affordability)
      veto Wait if market_state in {POSSIBLE, LIKELY, …}   (market stress)
      cap Proceed → Caution unless ratio ≤ threshold_proceed AND market STABLE
      final = most conservative of the above
    """
    candidates = [decision["band"]]

    if stress_ratio >= threshold_wait or market_state in _MARKET_STRESS_STATES:
        candidates.append("Wait")

    # "Proceed" is only allowed when both personal and market conditions are calm.
    proceed_ok = (
        stress_ratio <= threshold_proceed and market_state in _MARKET_STABLE_STATES
    )
    if decision["band"] == "Proceed with caution" and not proceed_ok:
        candidates.append("Caution")

    recommendation: Recommendation = _BY_SEVERITY[max(_SEVERITY[c] for c in candidates)]

    headline = (
        f"Decision Hurdle Index: {decision['dhi']:.0f}/100 "
        f"(binding: {decision['binding']}) · "
        f"Recommendation: {recommendation}"
    )

    return Verdict(
        recommendation=recommendation,
        headline=headline,
        dhi=decision["dhi"],
        dhi_band=decision["band"],
        binding_hurdle=decision["binding"],
        hurdles=decision["hurdles"],
        urgency=decision["urgency"],
        market_state=market_state,
        market_reason=market_reason,
        stress_ratio=stress_ratio,
        fsi_score=fsi_score,
        fsi_arrow=_direction(fsi_score, previous_fsi),
    )
