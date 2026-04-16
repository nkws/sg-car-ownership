"""Multi-page entry point.

Top-level navigation (rendered by st.navigation):
  COE    — existing financial-stress dashboard (dashboard.py, untouched)
  Macro  — overview + thought leaders (app_pages/macro.py)

Each page script owns its own st.set_page_config so dashboard.py's
existing configuration keeps working without modification.
"""

import streamlit as st


coe_page = st.Page(
    "dashboard.py",
    title="COE",
    icon="🚗",
    default=True,
)
macro_page = st.Page(
    "app_pages/macro.py",
    title="Macro",
    icon="🌐",
    url_path="macro",
)

pg = st.navigation([coe_page, macro_page])
pg.run()
