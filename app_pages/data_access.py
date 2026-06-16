"""Shared, cached data loaders.

Centralises the SQLite/JSON reads that several pages need (dashboard, Home,
COE Outlook) so the caching and SQL live in one place instead of being
duplicated inline in dashboard.py.
"""

import json

import pandas as pd
import streamlit as st

from database import get_conn, init_db
from config import SIGNAL_FILE


@st.cache_data(ttl=3600)
def load_signal():
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    return None


@st.cache_data(ttl=3600)
def load_coe_history():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium
            FROM coe_results
            GROUP BY month, vehicle_class
            ORDER BY month
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=3600)
def load_town_profiles():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM town_profile ORDER BY fsi_score DESC").fetchall()
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=3600)
def load_income_segments():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT dwelling_type, median_income, income_bracket, percentage
            FROM household_income
            ORDER BY median_income
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=3600)
def load_hp_data():
    init_db()
    with get_conn() as conn:
        try:
            rows = conn.execute("SELECT * FROM mas_hire_purchase ORDER BY year, quarter").fetchall()
            return pd.DataFrame([dict(r) for r in rows])
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_refresh_log():
    """Per-source freshness from the data_refresh_log table."""
    init_db()
    with get_conn() as conn:
        try:
            rows = conn.execute(
                "SELECT source, last_updated, records_count, status "
                "FROM data_refresh_log ORDER BY source"
            ).fetchall()
            return pd.DataFrame([dict(r) for r in rows])
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_previous_composite_fsi():
    """Previous run's composite FSI, for the 'vs last refresh' trend arrow.

    Reads the second-most-recent ``_composite_`` row written by the pipeline
    (models/fsi.py). Returns None when there is no prior reading yet.
    """
    init_db()
    with get_conn() as conn:
        try:
            rows = conn.execute(
                "SELECT date, fsi_score FROM fsi_history "
                "WHERE segment = '_composite_' ORDER BY date DESC LIMIT 2"
            ).fetchall()
        except Exception:
            return None
    if len(rows) < 2:
        return None
    return rows[1]["fsi_score"]
