"""Tests for the Decision Hurdle Index sub-hurdles and composite."""

from datetime import date

from models import decision_index as di


def test_affordability_monotonic():
    lo = di.affordability_hurdle(0.15, 30)["score"]
    hi = di.affordability_hurdle(0.45, 30)["score"]
    assert hi > lo


def test_timing_reversal_raises_hurdle():
    calm = di.timing_hurdle(100000, 100000, "STABLE")["score"]
    confirmed = di.timing_hurdle(100000, 100000, "CONFIRMED")["score"]
    assert confirmed > calm


def test_commitment_more_downpayment_raises_hurdle():
    thin = di.commitment_hurdle(downpayment=20000, monthly_income=10000, tenure_years=7)["score"]
    thick = di.commitment_hurdle(downpayment=90000, monthly_income=10000, tenure_years=7)["score"]
    assert thick > thin


def test_ev_cliff_creates_urgency():
    """An EV buyer near the EEAI sunset should see high urgency."""
    near = di.urgency_offset(today=date(2026, 12, 15), is_ev=True)["score"]
    petrol = di.urgency_offset(today=date(2026, 12, 15), is_ev=False)["score"]
    assert near > petrol
    assert near >= 55


def test_urgency_lowers_net_dhi():
    """Same hurdles, but an imminent EV cliff should reduce the composite."""
    common = dict(
        stress_ratio=0.30, fsi_score=50, premium=110000, avg_premium=100000,
        reversal_state="WATCH", correction_pct=0, downpayment=40000,
        monthly_income=10000, tenure_years=7, thesis_stale=False,
    )
    petrol = di.build_decision_score(is_ev=False, today=date(2026, 12, 15), **common)
    ev = di.build_decision_score(is_ev=True, today=date(2026, 12, 15), **common)
    assert ev["dhi"] < petrol["dhi"]


def test_bands():
    assert di.compute_dhi(
        affordability=di.Hurdle(label="a", score=90, reason=""),
        timing=di.Hurdle(label="t", score=90, reason=""),
        commitment=di.Hurdle(label="c", score=90, reason=""),
        policy=di.Hurdle(label="p", score=90, reason=""),
        urgency=di.Hurdle(label="u", score=0, reason=""),
    )["band"] == "Wait"

    assert di.compute_dhi(
        affordability=di.Hurdle(label="a", score=10, reason=""),
        timing=di.Hurdle(label="t", score=10, reason=""),
        commitment=di.Hurdle(label="c", score=10, reason=""),
        policy=di.Hurdle(label="p", score=10, reason=""),
        urgency=di.Hurdle(label="u", score=100, reason=""),
    )["band"] == "Proceed with caution"
