"""Shared Verdict / Decision Hurdle Index panel.

Gathers the raw inputs the DHI needs (premium level, reversal state, profile,
FSI history) and renders the headline recommendation plus a sub-hurdle
breakdown. Called by both the dashboard header and the Home briefing so the two
pages can never disagree on the call.
"""

from __future__ import annotations

import streamlit as st

from config import EV_CATEGORIES, CAR_COSTS
from models.coe_reversal import detect_reversal
from models.ratio_model import stress_test, ev_rebate
from models.decision_index import build_decision_score
from models.verdict import compute_verdict
from app_pages.data_access import load_previous_composite_fsi
from analysis.coe_market import (
    _load_recent_premiums,
    _compute_market_stats,
    is_thesis_stale,
)


_REC_COLOR = {"Wait": "red", "Caution": "yellow", "Proceed with caution": "green"}
_STATE_RANK = {"NO DATA": -1, "STABLE": 0, "WATCH": 1, "POSSIBLE": 2,
               "LIKELY": 3, "CONFIRMED": 4}


def build_verdict(profile, signal):
    """Compute the Verdict for a profile without rendering. Pure-ish (reads data)."""
    is_ev = profile["vehicle_category"] in EV_CATEGORIES
    base_cat = "cat_a" if profile["vehicle_category"] in ("cat_a", "cat_a_ev") else "cat_b"

    # Market state: worse of Cat A / Cat B reversal (conservative).
    rev_a = detect_reversal("Category A")
    rev_b = detect_reversal("Category B")
    worst = rev_a if _STATE_RANK.get(rev_a["state"], -1) >= _STATE_RANK.get(rev_b["state"], -1) else rev_b

    # Premium level for the chosen category, vs window average.
    data = _load_recent_premiums()
    stats = _compute_market_stats(data)
    prem_key = "catA" if base_cat == "cat_a" else "catB"
    if data:
        premium = data[-1][prem_key]
        avg_premium = sum(d[prem_key] for d in data) / len(data)
        correction = stats.get("correction_pct_a" if base_cat == "cat_a" else "correction_pct_b", 0.0)
    else:
        premium = CAR_COSTS[profile["vehicle_category"]]["coe_premium_avg"]
        avg_premium = premium
        correction = 0.0

    # Personal stress-tested monthly cost for the chosen category.
    stress_results = stress_test(profile["stress_coe_mult"], profile["stress_rate_add"])
    pstress = next(
        (r for r in stress_results if r["category"] == profile["vehicle_category"]),
        stress_results[0],
    )
    stressed_monthly = pstress["stressed_monthly_cost"]
    stress_ratio = stressed_monthly / max(profile["monthly_income"], 1)

    # Downpayment (40%) for the commitment hurdle.
    rebate = ev_rebate(profile["vehicle_category"])
    total_vehicle = profile["vehicle_price"] + premium - rebate
    downpayment = 0.40 * total_vehicle

    fsi = signal.get("fsi_score", 0) if signal else 0
    previous_fsi = load_previous_composite_fsi()
    if previous_fsi is None:
        previous_fsi = st.session_state.get("_last_fsi_score")

    decision = build_decision_score(
        stress_ratio=stress_ratio,
        fsi_score=fsi,
        premium=premium,
        avg_premium=avg_premium,
        reversal_state=worst["state"],
        correction_pct=correction,
        downpayment=downpayment,
        monthly_income=profile["monthly_income"],
        tenure_years=profile["loan_tenure_years"],
        is_ev=is_ev,
        thesis_stale=is_thesis_stale(),
        weights=None,
        bands={"proceed_below": int(profile["threshold_proceed"] * 100),
               "wait_above": int(profile["threshold_wait"] * 100)},
    )

    verdict = compute_verdict(
        decision=decision,
        market_state=worst["state"],
        market_reason=worst["summary"],
        stress_ratio=stress_ratio,
        fsi_score=fsi,
        previous_fsi=previous_fsi,
        threshold_wait=profile["threshold_wait"],
        threshold_proceed=profile["threshold_proceed"],
    )
    st.session_state["_last_fsi_score"] = fsi

    return verdict, {
        "stressed_monthly": stressed_monthly,
        "worst": worst,
        "previous_fsi": previous_fsi,
        "premium": premium,
    }


def render_verdict(profile, signal, *, compact: bool = False):
    """Render the verdict headline, chips, and DHI breakdown.

    compact=True drops the FSI/market chips (used on the Home briefing).
    Returns the verdict dict so callers can reuse the recommendation.
    """
    verdict, ctx = build_verdict(profile, signal)

    color = _REC_COLOR[verdict["recommendation"]]
    st.markdown(
        f"<div class='metric-{color}' style='padding:1rem 1.2rem;border-radius:8px;"
        f"background:rgba(127,127,127,0.08);margin-bottom:0.5rem;'>"
        f"<div style='font-size:1.15rem;font-weight:600;'>{verdict['headline']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Headline metrics: DHI, personal ratio, market.
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Decision Hurdle Index",
        f"{verdict['dhi']:.0f} / 100",
        delta=f"binding: {verdict['binding_hurdle']}",
        delta_color="off",
    )
    c2.metric(
        "Your stress-tested ratio",
        f"{verdict['stress_ratio']:.0%}",
        delta=f"${ctx['stressed_monthly']:,.0f}/mo on ${profile['monthly_income']:,}/mo",
        delta_color="off",
    )
    c3.metric(
        f"Market: {verdict['market_state']}",
        f"{ctx['worst']['score']}/5 signals",
        delta=f"Composite FSI {verdict['fsi_score']:.0f} {verdict['fsi_arrow']}",
        delta_color="off",
    )

    with st.expander("Why this call — hurdle breakdown", expanded=not compact):
        st.caption(
            "The Decision Hurdle Index asks *how high is the bar to confidently buy "
            "now*, not just how financially hard it is. Each hurdle below adds to the "
            "score; urgency (the cost of waiting) subtracts."
        )
        for h in verdict["hurdles"]:
            st.markdown(
                f"<div class='term-def'><span class='term-label'>{h['label']}: "
                f"{h['score']:.0f}/100</span> — {h['reason']}</div>",
                unsafe_allow_html=True,
            )
        u = verdict["urgency"]
        st.markdown(
            f"<div class='term-def'><span class='term-label'>↓ {u['label']}: "
            f"−{u['score']:.0f}</span> — {u['reason']}</div>",
            unsafe_allow_html=True,
        )

    st.caption("Heuristic only — not financial advice. Adjust the decision thresholds in the sidebar.")
    return verdict
