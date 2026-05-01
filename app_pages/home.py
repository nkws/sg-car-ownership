"""Home page — at-a-glance dashboard across COE and Macro.

Surfaces the top-line verdict, FSI composite, COE market state, and the
most pressing macro signals from tracked thought leaders. Acts as the
landing page; deeper analysis lives on the COE and Macro pages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysts import ANALYSTS
from config import SIGNAL_FILE
from models.coe_reversal import detect_reversal


SIGNAL_CATEGORY_COLORS: dict[str, str] = {
    "geopolitical": "#4e79a7",
    "economic": "#f28e2b",
    "technology": "#59a14f",
    "security": "#e15759",
    "energy": "#edc948",
    "other": "#b07aa1",
}

# Worst-first ordering for picking the dominant market state across Cat A/B.
_STATE_RANK = {
    "NO DATA": -1,
    "STABLE": 0,
    "WATCH": 1,
    "POSSIBLE": 2,
    "LIKELY": 3,
    "CONFIRMED": 4,
}
_STATE_TONE = {
    "STABLE": "green",
    "WATCH": "yellow",
    "POSSIBLE": "yellow",
    "LIKELY": "red",
    "CONFIRMED": "red",
    "NO DATA": "yellow",
}


st.set_page_config(
    page_title="Home — Singapore Car Ownership: Affordability, COE & Household Stress Index",
    page_icon="🏠",
    layout="wide",
)

# Mirror the visual language used by COE and Macro pages.
st.markdown(
    """
<style>
    .block-container {
        padding-top: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid var(--secondary-background-color);
        color: var(--text-color);
    }
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 8px;
        padding: 1rem;
    }
    .metric-green [data-testid="stMetric"] {
        border-left: 4px solid #4caf50;
        background: rgba(76, 175, 80, 0.15);
    }
    .metric-yellow [data-testid="stMetric"] {
        border-left: 4px solid #ffca28;
        background: rgba(255, 202, 40, 0.15);
    }
    .metric-red [data-testid="stMetric"] {
        border-left: 4px solid #ef5350;
        background: rgba(239, 83, 80, 0.15);
    }
    .verdict-card {
        padding: 1.1rem 1.3rem;
        border-radius: 10px;
        background: rgba(127, 127, 127, 0.08);
        margin-bottom: 0.75rem;
    }
    .verdict-headline {
        font-size: 1.2rem;
        font-weight: 600;
    }
    .signal-pill {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        margin-right: 0.4rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
    }
    .nav-card {
        background: var(--secondary-background-color);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        height: 100%;
    }
</style>
    """,
    unsafe_allow_html=True,
)


# ─── Data loaders ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_signal() -> dict | None:
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    return None


def _worst_market_state() -> dict:
    """Return the worse reversal result across Cat A and Cat B."""
    a = detect_reversal("Category A")
    b = detect_reversal("Category B")
    return a if _STATE_RANK.get(a["state"], -1) >= _STATE_RANK.get(b["state"], -1) else b


def _score_color(score: float) -> str:
    if score < 40:
        return "green"
    if score < 60:
        return "yellow"
    return "red"


def _stress_label(score: float) -> str:
    if score < 30:
        return "Low"
    if score < 45:
        return "Moderate"
    if score < 60:
        return "Elevated"
    if score < 75:
        return "High"
    return "Critical"


# ─── Header ──────────────────────────────────────────────────────────────────

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown("## Home")
    st.markdown("**At-a-glance view across COE affordability and macro signals**")
with col_refresh:
    st.markdown("")
    if st.button("Refresh Data", help="Run the data pipeline to fetch latest data."):
        with st.spinner("Running data pipeline..."):
            from run_pipeline import main as run_pipeline
            run_pipeline()
            st.cache_data.clear()
        st.rerun()

signal = _load_signal()
if signal:
    ts = signal.get("timestamp", "N/A")[:10]
    st.caption(f"Data as of {ts}")
else:
    st.warning("No pipeline data found yet. Click **Refresh Data** to populate.")


# ─── Verdict snapshot ────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Verdict snapshot</div>",
    unsafe_allow_html=True,
)

if signal:
    market = _worst_market_state()
    market_state = market["state"]
    fsi = float(signal.get("fsi_score", 0))
    tone = _STATE_TONE.get(market_state, "yellow")

    # Mirror the COE dashboard's verdict heuristic at a high level: market
    # stress alone (>= POSSIBLE) is enough to advise waiting.
    if market_state in {"POSSIBLE", "LIKELY", "CONFIRMED"} or fsi >= 60:
        recommendation = "Wait"
        rec_tone = "red"
    elif market_state == "STABLE" and fsi < 40:
        recommendation = "Proceed with caution"
        rec_tone = "green"
    else:
        recommendation = "Caution"
        rec_tone = "yellow"

    st.markdown(
        f"<div class='verdict-card metric-{rec_tone}'>"
        f"<div class='verdict-headline'>"
        f"Market: {market_state} · Composite FSI: {fsi:.0f} / 100 · "
        f"Recommendation: {recommendation}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "High-level signal only. Visit the COE page for a personalised "
        "verdict that factors in your income, dwelling type, and target vehicle."
    )

    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.markdown(f"<div class='metric-{_score_color(fsi)}'>", unsafe_allow_html=True)
        st.metric("Composite FSI", f"{fsi:.0f} / 100", delta=_stress_label(fsi))
        st.markdown("</div>", unsafe_allow_html=True)
    with v2:
        st.markdown(f"<div class='metric-{tone}'>", unsafe_allow_html=True)
        st.metric(
            "COE Market",
            market_state,
            delta=f"{market.get('score', 0)}/5 reversal signals",
            delta_color="off",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    car_costs = signal.get("car_costs", {})
    cat_a = car_costs.get("cat_a", {})
    cat_b = car_costs.get("cat_b", {})
    with v3:
        st.metric(
            "Cat A monthly",
            f"${cat_a.get('monthly_total', 0):,.0f}",
            delta=f"Vehicle ${cat_a.get('vehicle_cost', 0):,.0f}",
            delta_color="off",
        )
    with v4:
        st.metric(
            "Cat B monthly",
            f"${cat_b.get('monthly_total', 0):,.0f}",
            delta=f"Vehicle ${cat_b.get('vehicle_cost', 0):,.0f}",
            delta_color="off",
        )
else:
    st.info("Verdict snapshot will appear once the data pipeline has run.")


# ─── Active alerts ───────────────────────────────────────────────────────────

if signal:
    alerts = signal.get("alerts", [])
    if alerts:
        st.markdown(
            "<div class='section-header'>Active alerts</div>",
            unsafe_allow_html=True,
        )
        for a in alerts[:3]:
            st.warning(a)
        if len(alerts) > 3:
            st.caption(f"+{len(alerts) - 3} more on the COE page")


# ─── Macro snapshot ──────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Top macro signals</div>",
    unsafe_allow_html=True,
)
st.caption(
    "Highest severity × velocity signals across tracked thought leaders. "
    "Drill into the Macro page for full analyst profiles."
)

# Flatten signals across all analysts and rank by severity × velocity.
flat_signals = []
for analyst in ANALYSTS.values():
    for s in analyst.get("signals", []):
        flat_signals.append({
            **s,
            "_analyst": analyst["name"],
            "_score": s.get("severity", 0) * s.get("velocity", 0),
        })

flat_signals.sort(key=lambda r: r["_score"], reverse=True)
top_signals = flat_signals[:6]

if top_signals:
    cols = st.columns(3)
    for i, s in enumerate(top_signals):
        color = SIGNAL_CATEGORY_COLORS.get(s["category"], "#888888")
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<span class='signal-pill' style='background:{color};'>"
                    f"{s['category']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{s['name']}**")
                st.caption(
                    f"Severity {s['severity']}/10 · Velocity {s['velocity']}/10"
                )
                st.caption(f"Tracked by {s['_analyst']}")
else:
    st.info("No macro signals tracked yet.")


# ─── Navigation cards ────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Explore</div>",
    unsafe_allow_html=True,
)

nav_a, nav_b = st.columns(2)
with nav_a:
    with st.container(border=True):
        st.markdown("#### 🚗 COE dashboard")
        st.write(
            "Personal verdict, FSI breakdown, affordability segmentation, "
            "stress tests, and the COE tipping-point monitor."
        )
        if st.button("Open COE →", key="nav_coe", use_container_width=True):
            st.switch_page("dashboard.py")

with nav_b:
    with st.container(border=True):
        st.markdown("#### 🌐 Macro")
        st.write(
            "Cross-cutting macro indicators and weekly synthesis from "
            "tracked thought leaders (Bremmer, Galloway, Burry, Eisman)."
        )
        if st.button("Open Macro →", key="nav_macro", use_container_width=True):
            st.switch_page("app_pages/macro.py")
