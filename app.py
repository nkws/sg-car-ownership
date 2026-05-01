"""Multi-page entry point.

Top-level navigation (rendered by st.navigation):
  Home             — personal daily briefing (app_pages/home.py)
  COE              — financial-stress dashboard (dashboard.py)
  Thought Leaders  — analyst profiles (app_pages/thought_leaders.py)

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
thought_leaders_page = st.Page(
    "app_pages/thought_leaders.py",
    title="Thought Leaders",
    icon="🧠",
    url_path="thought-leaders",
)

pg = st.navigation([home_page, coe_page, thought_leaders_page])
pg.run()
