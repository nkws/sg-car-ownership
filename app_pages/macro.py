"""Macro page — overview + thought leaders.

Sub-nav via st.tabs. The Thought Leaders tab shows a grid of analyst cards;
selecting one swaps the tab contents to that analyst's profile. Navigation
between index and detail is driven by session state because Streamlit does
not expose nested URL paths.
"""

import streamlit as st

from analysts import ANALYSTS
from models.analyst import Analyst


st.set_page_config(
    page_title="Macro — Singapore Car Ownership: Affordability, COE & Household Stress Index",
    page_icon="🌐",
    layout="wide",
)

# Mirror the COE dashboard's visual language so nav feels native.
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
    .analyst-card {
        background: var(--secondary-background-color);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        height: 100%;
    }
    .framework-active { color: #4caf50; font-weight: 600; }
    .framework-watch { color: #ffca28; font-weight: 600; }
    .framework-dormant { color: #9e9e9e; font-weight: 600; }
</style>
    """,
    unsafe_allow_html=True,
)


# ─── Sub-nav ─────────────────────────────────────────────────────────────────

overview_tab, leaders_tab = st.tabs(["Overview", "Thought Leaders"])


# ─── Overview ────────────────────────────────────────────────────────────────

with overview_tab:
    st.markdown("## Macro Overview")
    st.caption(
        "Cross-cutting macro indicators that complement the COE-specific "
        "analysis on the main dashboard."
    )
    st.info("Coming soon — this page will be populated in a later session.")


# ─── Thought Leaders ─────────────────────────────────────────────────────────

SELECTED_KEY = "selected_analyst"


def _render_card(a: Analyst) -> None:
    with st.container(border=True):
        st.markdown(f"#### {a['name']}")
        st.caption(a["focus_area"])
        blurb = a["bio"]
        if len(blurb) > 180:
            blurb = blurb[:180].rstrip() + "…"
        st.write(blurb)
        st.caption(f"Last updated: {a['last_updated']}")
        if st.button("View profile →", key=f"view_{a['id']}"):
            st.session_state[SELECTED_KEY] = a["id"]
            st.rerun()


def _render_index() -> None:
    st.markdown("## Thought Leaders")
    st.caption(
        "Macro analysts we track for framework evolution and signal shifts."
    )
    analysts = list(ANALYSTS.values())
    cols = st.columns(3)
    for i, a in enumerate(analysts):
        with cols[i % 3]:
            _render_card(a)


def _framework_status_cell(status: str) -> str:
    cls = {
        "active": "framework-active",
        "watch": "framework-watch",
        "dormant": "framework-dormant",
    }.get(status, "")
    return f"<span class='{cls}'>{status}</span>"


def _render_detail(a: Analyst) -> None:
    if st.button("← Back to Thought Leaders"):
        st.session_state.pop(SELECTED_KEY, None)
        st.rerun()

    # Header
    st.markdown(f"# {a['name']}")
    st.caption(f"{a['focus_area']}  ·  Last updated {a['last_updated']}")
    st.write(a["bio"])

    # Latest synthesis
    st.markdown("<div class='section-header'>Latest content synthesis</div>", unsafe_allow_html=True)
    st.write(a["latest_content"])

    # Framework tracker
    st.markdown("<div class='section-header'>Framework tracker</div>", unsafe_allow_html=True)
    fw_rows = [
        {
            "Framework": f["name"],
            "Status": f["status"],
            "Signal": f["signal"],
            "Note": f["note"],
        }
        for f in a["frameworks"]
    ]
    st.dataframe(fw_rows, use_container_width=True, hide_index=True)

    # Top signals / risks — rendered as a styled table for now
    # (charting library decision deferred).
    st.markdown("<div class='section-header'>Top signals / risks</div>", unsafe_allow_html=True)
    sig_rows = sorted(
        (
            {
                "Signal": s["name"],
                "Category": s["category"],
                "Severity (0–10)": s["severity"],
                "Velocity (0–10)": s["velocity"],
            }
            for s in a["signals"]
        ),
        key=lambda r: (r["Severity (0–10)"], r["Velocity (0–10)"]),
        reverse=True,
    )
    st.dataframe(sig_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Severity = consequence if it plays out. "
        "Velocity = how quickly it is evolving."
    )

    # Recent episode log
    st.markdown("<div class='section-header'>Recent episode log</div>", unsafe_allow_html=True)
    for item in a["recent_items"]:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['source']}  ·  {item['published']}")
            st.write(item["summary"])


with leaders_tab:
    selected = st.session_state.get(SELECTED_KEY)
    if selected and selected in ANALYSTS:
        _render_detail(ANALYSTS[selected])
    else:
        _render_index()
