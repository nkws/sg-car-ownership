"""Home — personal daily briefing.

A single page tuned for a daily glance: today's date, a personalised car-
purchase verdict driven by the saved profile, the latest movement on the
COE market and FSI score, and freshly published items from the thought
leaders being tracked. Deeper analysis lives on the COE and Thought
Leaders pages.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysts import ANALYSTS
from config import SIGNAL_FILE
from models.coe_reversal import detect_reversal
from models.profile import (
    DWELLING_TYPES,
    INCOME_PERCENTILES,
    Profile,
    default_profile,
)
from models.ratio_model import stress_test as _stress_test
from models.verdict import compute_verdict


SIGNAL_CATEGORY_COLORS: dict[str, str] = {
    "geopolitical": "#4e79a7",
    "economic": "#f28e2b",
    "technology": "#59a14f",
    "security": "#e15759",
    "energy": "#edc948",
    "other": "#b07aa1",
}

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
_REC_TONE = {
    "Wait": "red",
    "Caution": "yellow",
    "Proceed with caution": "green",
}


st.set_page_config(
    page_title="Home — Singapore Car Ownership: Affordability, COE & Household Stress Index",
    page_icon="🏠",
    layout="wide",
)

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
    .briefing-card {
        padding: 1.1rem 1.3rem;
        border-radius: 10px;
        background: rgba(127, 127, 127, 0.08);
        margin-bottom: 0.75rem;
    }
    .briefing-headline {
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
    .profile-line {
        font-size: 0.92rem;
        color: var(--text-color);
        margin: 0.2rem 0;
    }
    .profile-label { opacity: 0.7; }
</style>
    """,
    unsafe_allow_html=True,
)


# ─── Profile bootstrap ───────────────────────────────────────────────────────
# The profile widgets live on the COE page. Seed defaults here so the home
# briefing is computable even on a cold start (no COE visit yet).

_DEFAULT = default_profile()
_PROFILE_KEYS = {
    "profile_income": _DEFAULT["monthly_income"],
    "profile_dwelling": _DEFAULT["dwelling_type"],
    "profile_town": _DEFAULT["town"],
    "profile_vehicle_cat": _DEFAULT["vehicle_category"],
    "profile_vehicle_price": _DEFAULT["vehicle_price"],
    "profile_tenure": _DEFAULT["loan_tenure_years"],
    "profile_stress_coe_mult": _DEFAULT["stress_coe_mult"],
    "profile_stress_rate_add": _DEFAULT["stress_rate_add"],
    "profile_threshold_wait": _DEFAULT["threshold_wait"],
    "profile_threshold_proceed": _DEFAULT["threshold_proceed"],
}
for _k, _v in _PROFILE_KEYS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _profile() -> Profile:
    return Profile(
        monthly_income=int(st.session_state["profile_income"]),
        dwelling_type=st.session_state["profile_dwelling"],
        town=st.session_state["profile_town"],
        vehicle_category=st.session_state["profile_vehicle_cat"],
        vehicle_price=int(st.session_state["profile_vehicle_price"]),
        loan_tenure_years=int(st.session_state["profile_tenure"]),
        stress_coe_mult=float(st.session_state["profile_stress_coe_mult"]),
        stress_rate_add=float(st.session_state["profile_stress_rate_add"]),
        threshold_wait=float(st.session_state["profile_threshold_wait"]),
        threshold_proceed=float(st.session_state["profile_threshold_proceed"]),
    )


# ─── Data ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_signal() -> dict | None:
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    return None


def _worst_market_state() -> dict:
    a = detect_reversal("Category A")
    b = detect_reversal("Category B")
    return a if _STATE_RANK.get(a["state"], -1) >= _STATE_RANK.get(b["state"], -1) else b


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


def _parse_iso(d: str) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date.min


# ─── Header ──────────────────────────────────────────────────────────────────

today = date.today()
greeting_hour = datetime.now().hour
if greeting_hour < 12:
    greeting = "Good morning"
elif greeting_hour < 18:
    greeting = "Good afternoon"
else:
    greeting = "Good evening"

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown(f"## {greeting}")
    st.caption(today.strftime("%A, %d %B %Y") + " · Daily briefing")
with col_refresh:
    st.markdown("")
    if st.button("Refresh Data", help="Run the data pipeline to fetch latest data."):
        with st.spinner("Running data pipeline..."):
            from run_pipeline import main as run_pipeline
            run_pipeline()
            st.cache_data.clear()
        st.rerun()

signal = _load_signal()
profile = _profile()


# ─── Personal verdict ────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Your verdict today</div>",
    unsafe_allow_html=True,
)

if signal:
    market = _worst_market_state()
    market_state = market["state"]

    stress_results = _stress_test(profile["stress_coe_mult"], profile["stress_rate_add"])
    profile_stress = next(
        (r for r in stress_results if r["category"] == profile["vehicle_category"]),
        stress_results[0],
    )
    stressed_monthly = profile_stress["stressed_monthly_cost"]
    stress_ratio = stressed_monthly / max(profile["monthly_income"], 1)

    fsi = float(signal.get("fsi_score", 0))
    previous_fsi = st.session_state.get("_last_fsi_score")
    verdict = compute_verdict(
        market_state=market_state,
        market_reason=market["summary"],
        stress_ratio=stress_ratio,
        fsi_score=fsi,
        previous_fsi=previous_fsi,
        threshold_wait=profile["threshold_wait"],
        threshold_proceed=profile["threshold_proceed"],
    )
    st.session_state["_last_fsi_score"] = fsi

    rec_tone = _REC_TONE[verdict["recommendation"]]
    st.markdown(
        f"<div class='briefing-card metric-{rec_tone}'>"
        f"<div class='briefing-headline'>{verdict['recommendation']} — "
        f"market {market_state}, your stress-tested cost is "
        f"{stress_ratio:.0%} of income.</div></div>",
        unsafe_allow_html=True,
    )

    v1, v2, v3 = st.columns(3)
    v1.metric(
        f"Market: {market_state}",
        f"{market.get('score', 0)}/5 reversal signals",
        delta=verdict["market_reason"].split("—")[-1].strip().rstrip(".")
              if "—" in verdict["market_reason"] else None,
        delta_color="off",
    )
    v2.metric(
        "Your stress-tested ratio",
        f"{stress_ratio:.0%}",
        delta=f"${stressed_monthly:,.0f}/mo on ${profile['monthly_income']:,}/mo",
        delta_color="off",
    )
    v3.metric(
        "Composite FSI",
        f"{fsi:.0f} / 100  {verdict['fsi_arrow']}",
        delta=_stress_label(fsi),
        delta_color="off",
    )
    st.caption(
        "Driven by the profile saved on the COE page. "
        "Heuristic only — not financial advice."
    )
else:
    st.info(
        "Verdict will appear once the data pipeline has run. "
        "Click **Refresh Data** above to populate."
    )


# ─── Your profile snapshot ───────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Your profile</div>",
    unsafe_allow_html=True,
)

p1, p2, p3 = st.columns(3)
with p1:
    st.markdown("**Household**")
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Income:</span> "
        f"${profile['monthly_income']:,}/mo</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Dwelling:</span> "
        f"{profile['dwelling_type']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Town:</span> "
        f"{profile['town'] or '—'}</div>",
        unsafe_allow_html=True,
    )
with p2:
    st.markdown("**Vehicle target**")
    cat_label = "Cat A (≤1600cc)" if profile["vehicle_category"] == "cat_a" else "Cat B (>1600cc)"
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Category:</span> "
        f"{cat_label}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Price:</span> "
        f"${profile['vehicle_price']:,}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Tenure:</span> "
        f"{profile['loan_tenure_years']} years</div>",
        unsafe_allow_html=True,
    )
with p3:
    st.markdown("**Stress scenario**")
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>COE multiplier:</span> "
        f"×{profile['stress_coe_mult']:.1f}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Rate add:</span> "
        f"+{profile['stress_rate_add']:.2f} pp</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='profile-line'><span class='profile-label'>Wait threshold:</span> "
        f"{profile['threshold_wait']:.0%}</div>",
        unsafe_allow_html=True,
    )

if st.button("Edit profile on COE page →", key="edit_profile"):
    st.switch_page("dashboard.py")


# ─── Active alerts ───────────────────────────────────────────────────────────

if signal:
    alerts = signal.get("alerts", [])
    if alerts:
        st.markdown(
            "<div class='section-header'>Alerts to know</div>",
            unsafe_allow_html=True,
        )
        for a in alerts[:3]:
            st.warning(a)
        if len(alerts) > 3:
            st.caption(f"+{len(alerts) - 3} more on the COE page")


# ─── Today's headlines ───────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Today's headlines</div>",
    unsafe_allow_html=True,
)
st.caption("Most recent items from the thought leaders you track.")

headlines: list[dict] = []
for analyst in ANALYSTS.values():
    for item in analyst.get("recent_items", []):
        headlines.append({**item, "_analyst": analyst["name"], "_id": analyst["id"]})

headlines.sort(key=lambda h: _parse_iso(h["published"]), reverse=True)
top_headlines = headlines[:5]

if top_headlines:
    for h in top_headlines:
        with st.container(border=True):
            st.markdown(f"**{h['title']}**")
            st.caption(
                f"{h['_analyst']}  ·  {h['source']}  ·  {h['published']}"
            )
            st.write(h["summary"])
            if h.get("url"):
                st.markdown(f"[Open source →]({h['url']})")
else:
    st.info("No headlines yet.")


# ─── Signals on your radar ───────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>On your radar</div>",
    unsafe_allow_html=True,
)
st.caption("Highest severity × velocity signals across tracked analysts.")

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
    st.info("No signals tracked yet.")


# ─── Quick navigation ────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header'>Jump in</div>",
    unsafe_allow_html=True,
)

nav_a, nav_b = st.columns(2)
with nav_a:
    with st.container(border=True):
        st.markdown("#### 🚗 COE")
        st.write(
            "Personal verdict, FSI breakdown, affordability segmentation, "
            "stress tests, and the COE tipping-point monitor."
        )
        if st.button("Open COE →", key="nav_coe", use_container_width=True):
            st.switch_page("dashboard.py")

with nav_b:
    with st.container(border=True):
        st.markdown("#### 🧠 Thought Leaders")
        st.write(
            "Weekly synthesis, framework trackers, and signal scatter for "
            "the analysts you follow (Bremmer, Galloway, Burry, Eisman)."
        )
        if st.button(
            "Open Thought Leaders →",
            key="nav_thought_leaders",
            use_container_width=True,
        ):
            st.switch_page("app_pages/thought_leaders.py")

if signal:
    ts = signal.get("timestamp", "")[:10]
    if ts:
        st.caption(f"Pipeline data as of {ts}")
