"""Shared dashboard CSS, injectable from any page.

Extracted from dashboard.py so Home and other pages get the same metric-card
and term-definition styling (the verdict panel relies on these classes).
"""

import streamlit as st

_CSS = """
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
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-color) !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-color) !important;
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
    .stAlert {
        margin-bottom: 0.5rem;
    }
    .stPlotlyChart {
        margin-bottom: 0.5rem;
    }
    .term-def {
        font-size: 0.82rem;
        color: var(--text-color);
        margin-bottom: 0.3rem;
    }
    .term-label {
        font-weight: 600;
        color: var(--text-color);
    }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
