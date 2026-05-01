"""Thought Leaders — blank page that lists tracked analyst names."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysts import ANALYSTS


st.set_page_config(
    page_title="Thought Leaders — Singapore Car Ownership: Affordability, COE & Household Stress Index",
    page_icon="🧠",
    layout="wide",
)

st.markdown("## Thought Leaders")

for analyst in ANALYSTS.values():
    st.markdown(f"- {analyst['name']}")
