"""Extra calculator sections: EEAI cliff, renew-vs-buy, and cost-of-waiting.

These extend the existing Car Cost Calculator with the three trade-offs the COE
thesis raises in prose but never quantified. Each reuses existing model
functions so the numbers stay consistent with the rest of the dashboard.
"""

from __future__ import annotations

import re

import streamlit as st

from config import EV_INCENTIVES, EV_CATEGORIES, COE_BUY_TRIGGER_CAT_A
from models.ratio_model import calculate_monthly_car_cost
from analysis.coe_market import (
    _load_recent_premiums,
    _pqp_proxy_3mo,
    QUARTERLY_OUTLOOK,
)


def _latest_premium(base_cat: str) -> float:
    data = _load_recent_premiums()
    if not data:
        return 100000.0
    return float(data[-1]["catA" if base_cat == "cat_a" else "catB"])


def _ten_year_cost(cost: dict, downpayment_pct: float = 0.40) -> float:
    """Approximate 10-year total: downpayment + 120 months of total cost."""
    return cost["total_vehicle_cost"] * downpayment_pct + cost["monthly_total"] * 120


def _parse_range_midpoint(text: str) -> float | None:
    """Pull the midpoint out of a '$105K - $115K' style range string."""
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*K", text)
    if not nums:
        return None
    vals = [float(n) * 1000 for n in nums]
    return sum(vals) / len(vals)


def render(profile) -> None:
    base_cat = "cat_a" if profile["vehicle_category"] in ("cat_a", "cat_a_ev") else "cat_b"
    ev_cat = base_cat + "_ev"

    # ── EEAI cliff ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">EEAI Cliff: bid in 2026 vs wait to 2027</div>',
                unsafe_allow_html=True)
    st.caption(
        f"The EV Early Adoption Incentive (~${EV_INCENTIVES['eeai_current']:,}) drops to $0 "
        f"from {EV_INCENTIVES['eeai_sunset'][:7]}. Waiting for a lower COE only pays if the "
        "drop beats the rebate you forfeit. This compares an EV bought now against the same "
        "EV bought after the cliff at a lower COE."
    )

    current_coe = _latest_premium(base_cat)
    drop = st.slider(
        "Assumed COE drop if you wait to 2027 ($)",
        min_value=0, max_value=40000, value=15000, step=1000, format="$%d",
        help="How much lower you expect the COE premium to be after waiting.",
    )

    buy_now = calculate_monthly_car_cost(ev_cat, coe_override=current_coe, eeai_active=True)
    wait_27 = calculate_monthly_car_cost(ev_cat, coe_override=max(current_coe - drop, 0),
                                         eeai_active=False)

    now_10yr = _ten_year_cost(buy_now)
    wait_10yr = _ten_year_cost(wait_27)
    delta = wait_10yr - now_10yr

    e1, e2, e3 = st.columns(3)
    e1.metric("Buy EV now (2026, with EEAI)", f"${now_10yr:,.0f}", delta="10-yr total")
    e2.metric("Wait to 2027 (no EEAI)", f"${wait_10yr:,.0f}",
              delta=f"COE −${drop:,} but rebate gone")
    if delta >= 0:
        e3.markdown('<div class="metric-green">', unsafe_allow_html=True)
        e3.metric("Waiting costs you", f"${delta:,.0f}", delta="bidding now wins")
        e3.markdown("</div>", unsafe_allow_html=True)
    else:
        e3.markdown('<div class="metric-yellow">', unsafe_allow_html=True)
        e3.metric("Waiting saves you", f"${abs(delta):,.0f}", delta="only if COE drop holds")
        e3.markdown("</div>", unsafe_allow_html=True)

    breakeven = EV_INCENTIVES["eeai_current"] + EV_INCENTIVES["ves_rebate"]
    st.caption(
        f"Break-even: a COE drop larger than the ${breakeven:,} rebate you forfeit "
        "(EEAI + VES) is needed before waiting actually saves money."
    )

    st.markdown("")

    # ── Renew vs buy ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Renew COE vs buy new</div>',
                unsafe_allow_html=True)
    st.caption(
        "Renewing pays the Prevailing Quota Premium (PQP, a 3-month moving average of COE) "
        "to keep your existing car — no new ARF, no depreciation on a fresh purchase. "
        "Useful as the PARF rebate cut makes early scrapping less attractive."
    )

    data = _load_recent_premiums()
    pqp = _pqp_proxy_3mo(data, "catA" if base_cat == "cat_a" else "catB")
    if pqp:
        pqp_value = pqp["recent"]
        renew_years = st.selectbox("Renew for", [5, 10], index=1,
                                   format_func=lambda x: f"{x} years")
        # Renewal: PQP prorated over the renewed term, plus running costs only.
        buy_new = calculate_monthly_car_cost(base_cat, coe_override=_latest_premium(base_cat))
        running_monthly = (buy_new["monthly_insurance"] + buy_new["monthly_road_tax"]
                           + buy_new["monthly_petrol"] + buy_new["monthly_parking"]
                           + buy_new["monthly_maintenance"])
        renew_monthly = pqp_value / (renew_years * 12) + running_monthly

        rv1, rv2, rv3 = st.columns(3)
        rv1.metric("PQP (renewal premium)", f"${pqp_value:,.0f}",
                   delta=f"{pqp['delta']:+,.0f} vs prior 3 rounds")
        rv2.metric(f"Renew {renew_years}yr — monthly", f"${renew_monthly:,.0f}",
                   delta="PQP prorated + running costs")
        rv3.metric("Buy new — monthly", f"${buy_new['monthly_total']:,.0f}",
                   delta="loan + running + depreciation")
        if renew_monthly < buy_new["monthly_total"]:
            st.success(
                f"Renewing is ${buy_new['monthly_total'] - renew_monthly:,.0f}/mo cheaper — "
                "no new-car depreciation or downpayment. Best if your current car is sound."
            )
        else:
            st.info("Buying new is comparable here — weigh reliability and warranty of the old car.")
    else:
        st.info("Not enough COE history to estimate a PQP proxy. Run the pipeline to refresh data.")

    st.markdown("")

    # ── Cost of waiting (quarterly outlook) ──────────────────────────────────
    st.markdown('<div class="section-header">Cost of waiting for the dip</div>',
                unsafe_allow_html=True)
    st.caption(
        "Combines the thesis's quarterly COE forecast with your 10-year cost. Buying at "
        "today's premium vs a forecast quarter — what does the wait actually change?"
    )

    quarter_opts = {q["quarter"]: q for q in QUARTERLY_OUTLOOK
                    if _parse_range_midpoint(q["range"]) is not None}
    if quarter_opts:
        choice = st.selectbox("Compare against forecast quarter", list(quarter_opts.keys()))
        target_coe = _parse_range_midpoint(quarter_opts[choice]["range"])

        today_cost = calculate_monthly_car_cost(base_cat, coe_override=current_coe)
        future_cost = calculate_monthly_car_cost(base_cat, coe_override=target_coe)
        today_10yr = _ten_year_cost(today_cost)
        future_10yr = _ten_year_cost(future_cost)
        diff = today_10yr - future_10yr

        w1, w2, w3 = st.columns(3)
        w1.metric("Buy now", f"${today_10yr:,.0f}", delta=f"COE ${current_coe:,.0f}")
        w2.metric(f"Buy in {choice}", f"${future_10yr:,.0f}",
                  delta=f"COE ~${target_coe:,.0f} ({quarter_opts[choice]['outlook']})")
        w3.metric("10-yr saving from waiting", f"${diff:,.0f}",
                  delta="before factoring rebates/risk", delta_color="off")
        st.caption(
            "Forecast ranges are the analyst's estimates, not guarantees. Pair this with the "
            "EEAI cliff above — for EVs, the lost rebate often outweighs the COE saving."
        )
    else:
        st.info("Quarterly outlook unavailable.")
