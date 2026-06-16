"""Home — daily car-buying briefing.

A 10-second answer to "should I buy a car right now?": the Decision Hurdle
Index verdict, the latest COE round vs the buy trigger, countdowns to the next
bidding round and the thesis buying window, thesis health, and live alerts.
Everything here is computed from existing models — this page only arranges it.
"""

from datetime import date

import streamlit as st

st.set_page_config(
    page_title="Home — Singapore Car Ownership: Affordability, COE & Household Stress Index",
    page_icon="🏠",
    layout="wide",
)

from config import COE_BUY_TRIGGER_CAT_A
from app_pages.styles import inject_css
from app_pages.profile_state import seed_profile_state, render_sidebar, current_profile
from app_pages.verdict_panel import render_verdict
from app_pages.data_access import load_signal
from app_pages.coe_calendar import next_bidding_round, buying_window_status
from analysis.coe_market import _load_recent_premiums, _audit_thesis, _compute_market_stats

inject_css()
seed_profile_state()
render_sidebar()

profile = current_profile()
signal = load_signal()

st.markdown("## Your Car-Buying Briefing")
st.caption(f"As of {date.today():%A, %d %b %Y} · Singapore COE & affordability")

# ── Verdict / Decision Hurdle Index ──────────────────────────────────────────
render_verdict(profile, signal, compact=True)

st.markdown("")

# ── Live countdowns + latest round vs trigger ────────────────────────────────
data = _load_recent_premiums()
latest = data[-1] if data else None
nxt = next_bidding_round()
window = buying_window_status()

m1, m2, m3, m4 = st.columns(4)

if latest:
    gap = latest["catA"] - COE_BUY_TRIGGER_CAT_A
    cls = "metric-green" if gap <= 0 else "metric-red"
    m1.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
    m1.metric(
        f"Cat A — {latest['period']}",
        f"${latest['catA']:,.0f}",
        delta=f"${gap:+,.0f} vs ${COE_BUY_TRIGGER_CAT_A:,} trigger",
        delta_color="inverse",
    )
    m1.markdown("</div>", unsafe_allow_html=True)
else:
    m1.metric("Cat A — latest", "—", delta="no data")

m2.metric("Next bidding round", nxt["label"], delta=f"in {nxt['days_until']} days", delta_color="off")

if window["state"] == "before":
    m3.metric("Buying window opens", f"{window['open']:%b %Y}", delta=f"in {window['days']} days", delta_color="off")
elif window["state"] == "open":
    m3.markdown('<div class="metric-green">', unsafe_allow_html=True)
    m3.metric("Buying window", "OPEN now", delta=f"{window['days']} days left", delta_color="off")
    m3.markdown("</div>", unsafe_allow_html=True)
else:
    m3.metric("Buying window", "closed", delta=f"{window['days']} days ago", delta_color="off")

# Thesis health summary
stats = _compute_market_stats(data)
audit = _audit_thesis(stats)
n_stale = sum(1 for _, status, _ in audit if status == "STALE")
n_watch = sum(1 for _, status, _ in audit if status == "WATCH")
m4.metric(
    "Thesis health",
    f"🟢{len(audit) - n_stale - n_watch} 🟡{n_watch} 🔴{n_stale}",
    delta="claims tracked", delta_color="off",
)

st.markdown("")

# ── Active alerts ────────────────────────────────────────────────────────────
alerts = signal.get("alerts", []) if signal else []
if alerts:
    st.markdown('<div class="section-header">Active alerts</div>', unsafe_allow_html=True)
    for a in alerts:
        st.warning(a)
elif signal is None:
    st.info("No data yet — run `python3 run_pipeline.py`, then click **Refresh Data** on the COE page.")

st.markdown("")
st.caption(
    "Dig deeper: **COE** page for the full stress dashboard · **COE Outlook** for the "
    "structural thesis and buying-window analysis. Adjust your profile in the sidebar."
)
