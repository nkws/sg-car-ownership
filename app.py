"""Multi-page entry point.

Top-level navigation (rendered by st.navigation):
  Home  — personal daily briefing (app_pages/home.py)
  COE   — financial-stress dashboard (dashboard.py)
  Forecasts — scored prediction ledger (app_pages/forecasts.py)

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

forecasts_page = st.Page(
    "app_pages/forecasts.py",
    title="Forecasts",
    icon="🎯",
    url_path="forecasts",
)

pg = st.navigation([home_page, coe_page, forecasts_page])
pg.run()
