"""Tests for the cost model: flat-rate conversion and EV rebates."""

from models.ratio_model import flat_to_eir, ev_rebate, calculate_monthly_car_cost
from config import EV_INCENTIVES


def test_flat_to_eir_known_value():
    # 2.8% flat over 7 years ≈ 4.9% EIR (2*n*flat / (n+1)).
    eir = flat_to_eir(0.028, 7)
    assert 0.048 < eir < 0.050


def test_flat_to_eir_monotonic_in_tenure():
    assert flat_to_eir(0.028, 7) > flat_to_eir(0.028, 5)


def test_ev_rebate_only_for_ev():
    assert ev_rebate("cat_a") == 0
    assert ev_rebate("cat_a_ev") == EV_INCENTIVES["eeai_current"] + EV_INCENTIVES["ves_rebate"]


def test_ev_rebate_drops_after_sunset():
    with_eeai = ev_rebate("cat_a_ev", eeai_active=True)
    without = ev_rebate("cat_a_ev", eeai_active=False)
    assert with_eeai - without == EV_INCENTIVES["eeai_current"]


def test_ev_rebate_lowers_vehicle_cost():
    active = calculate_monthly_car_cost("cat_a_ev", coe_override=100000, eeai_active=True)
    gone = calculate_monthly_car_cost("cat_a_ev", coe_override=100000, eeai_active=False)
    assert active["total_vehicle_cost"] < gone["total_vehicle_cost"]
    assert active["monthly_total"] < gone["monthly_total"]
