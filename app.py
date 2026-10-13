"""Multi-page entry point.

Top-level navigation (rendered by st.navigation):
  Home  — personal daily briefing (app_pages/home.py)
  COE   — financial-stress dashboard (dashboard.py)
  Intel — weekly sector intel brief (app_pages/intel.py)

Each page script owns its own st.set_page_config so dashboard.py's
existing configuration keeps working without modification.
"""

import streamlit as st


home_page = st.Page(
    "app_pages/home.py",
    title="Home",
    icon="🏠",
    default=True,
    url_path="home",
)
coe_page = st.Page(
    "dashboard.py",
    title="COE",
    icon="🚗",
)

intel_page = st.Page(
    "app_pages/intel.py",
    title="Intel",
    icon="🛰️",
    url_path="intel",
)

pg = st.navigation([home_page, coe_page, intel_page])
pg.run()
