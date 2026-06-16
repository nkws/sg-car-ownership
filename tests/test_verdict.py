"""Tests for the verdict decision rule and its safety vetoes."""

from models.decision_index import compute_dhi, Hurdle
from models.verdict import compute_verdict


def _decision(dhi_band_scores, urgency=0):
    """Build a DecisionScore with explicit hurdle scores."""
    return compute_dhi(
        affordability=Hurdle(label="Affordability", score=dhi_band_scores, reason=""),
        timing=Hurdle(label="Timing", score=dhi_band_scores, reason=""),
        commitment=Hurdle(label="Commitment", score=dhi_band_scores, reason=""),
        policy=Hurdle(label="Policy uncertainty", score=dhi_band_scores, reason=""),
        urgency=Hurdle(label="Urgency", score=urgency, reason=""),
    )


def _verdict(decision, stress_ratio=0.20, market_state="STABLE"):
    return compute_verdict(
        decision=decision,
        market_state=market_state,
        market_reason="test",
        stress_ratio=stress_ratio,
        fsi_score=50,
        previous_fsi=None,
        threshold_wait=0.50,
        threshold_proceed=0.35,
    )


def test_affordability_veto_forces_wait():
    """A calm DHI cannot override an unaffordable personal ratio."""
    v = _verdict(_decision(10), stress_ratio=0.60)  # ratio >= threshold_wait
    assert v["recommendation"] == "Wait"


def test_market_stress_forces_wait():
    v = _verdict(_decision(10), stress_ratio=0.20, market_state="LIKELY")
    assert v["recommendation"] == "Wait"


def test_proceed_only_when_calm():
    """Low DHI + low ratio + stable market → Proceed."""
    v = _verdict(_decision(5, urgency=80), stress_ratio=0.20, market_state="STABLE")
    assert v["recommendation"] == "Proceed with caution"


def test_proceed_capped_to_caution_when_market_not_stable():
    v = _verdict(_decision(5, urgency=80), stress_ratio=0.20, market_state="WATCH")
    assert v["recommendation"] == "Caution"


def test_fsi_arrow_direction():
    up = compute_verdict(
        decision=_decision(50), market_state="STABLE", market_reason="",
        stress_ratio=0.2, fsi_score=60, previous_fsi=50,
        threshold_wait=0.5, threshold_proceed=0.35,
    )
    assert up["fsi_arrow"] == "↑"
