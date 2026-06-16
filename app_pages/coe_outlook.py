"""COE Outlook — the structural COE thesis as a top-level page.

Previously this analysis was nested as a tab-within-a-tab inside the COE
dashboard, which made it two levels deep and hard to navigate. It now stands on
its own. The heavy lifting still lives in analysis/coe_market.render().
"""

import streamlit as st

st.set_page_config(
    page_title="COE Outlook — Singapore Car Ownership",
    page_icon="📈",
    layout="wide",
)

from app_pages.styles import inject_css
from app_pages.profile_state import seed_profile_state, render_sidebar
from analysis.coe_market import render as render_coe_analysis

inject_css()
seed_profile_state()
render_sidebar()

render_coe_analysis()
