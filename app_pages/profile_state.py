"""Shared sidebar profile.

The user's profile (income, dwelling, target vehicle, stress scenario) drives
the Verdict/DHI panel and the affordability sections. It used to live inline in
dashboard.py, which meant only that page could render it. Extracted here so the
Home page and any future page share the same widget and session state.

Usage on any page:
    from app_pages.profile_state import seed_profile_state, render_sidebar, current_profile
    seed_profile_state()
    render_sidebar()
    profile = current_profile()
"""

import streamlit as st

from models.profile import (
    DWELLING_TYPES,
    INCOME_PERCENTILES,
    INCOME_PERCENTILES_REFERENCE,
    VEHICLE_CATEGORY_LABELS,
    DEFAULT_THRESHOLD_WAIT,
    DEFAULT_THRESHOLD_PROCEED,
    Profile,
)
from app_pages.data_access import load_town_profiles


_PROFILE_KEYS = {
    "profile_income": INCOME_PERCENTILES[50],
    "profile_dwelling": "HDB 4 Room",
    "profile_town": "",
    "profile_vehicle_cat": "cat_a",
    "profile_vehicle_price": 80_000,
    "profile_tenure": 7,
    "profile_stress_coe_mult": 1.0,
    "profile_stress_rate_add": 0.0,
    "profile_threshold_wait": DEFAULT_THRESHOLD_WAIT,
    "profile_threshold_proceed": DEFAULT_THRESHOLD_PROCEED,
}


def seed_profile_state() -> None:
    """Seed session state with profile defaults once per session."""
    for k, v in _PROFILE_KEYS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _set_income(val: int) -> None:
    st.session_state["profile_income"] = val


def render_sidebar() -> None:
    """Render the profile sidebar widgets (writes into session state)."""
    with st.sidebar:
        st.markdown("### Your Profile")
        st.caption("Drives the Verdict/Decision panel and the affordability sections.")

        st.markdown("**Monthly household income**")
        _btn_cols = st.columns(4)
        for _i, (_pct, _val) in enumerate(INCOME_PERCENTILES.items()):
            _btn_cols[_i].button(
                f"P{_pct}",
                key=f"income_preset_p{_pct}",
                help=f"${_val:,}",
                on_click=_set_income,
                args=(_val,),
                use_container_width=True,
            )
        st.number_input(
            "$/month",
            min_value=1_000, max_value=200_000, step=500, format="%d",
            key="profile_income",
            label_visibility="collapsed",
        )
        st.caption(f"Presets: {INCOME_PERCENTILES_REFERENCE}")

        st.selectbox("Dwelling type", options=DWELLING_TYPES, key="profile_dwelling")

        _town_df = load_town_profiles()
        _town_options = [""] + (
            sorted(_town_df["town"].dropna().unique().tolist())
            if not _town_df.empty else []
        )
        if st.session_state["profile_town"] not in _town_options:
            st.session_state["profile_town"] = ""
        st.selectbox(
            "Town (optional)",
            options=_town_options,
            format_func=lambda x: x if x else "— not set —",
            key="profile_town",
        )

        st.divider()
        st.markdown("### Vehicle Target")
        st.selectbox(
            "Category",
            options=list(VEHICLE_CATEGORY_LABELS.keys()),
            format_func=lambda x: VEHICLE_CATEGORY_LABELS[x],
            key="profile_vehicle_cat",
        )
        st.slider(
            "Vehicle price (OMV + dealer)",
            min_value=30_000, max_value=300_000, step=5_000, format="$%d",
            key="profile_vehicle_price",
        )
        st.selectbox(
            "Loan tenure",
            options=[5, 6, 7],
            format_func=lambda x: f"{x} years",
            key="profile_tenure",
        )

        st.divider()
        st.markdown("### Stress Scenario")
        st.caption("Applied to the Verdict and Stress Test sections.")
        st.slider(
            "COE multiplier",
            min_value=0.5, max_value=2.0, step=0.1,
            key="profile_stress_coe_mult",
            help="1.0 = current level; 1.5 = +50%",
        )
        st.slider(
            "Flat rate increase (pp)",
            min_value=0.0, max_value=3.0, step=0.25,
            key="profile_stress_rate_add",
            help="Additional percentage points on the flat rate (not EIR)",
        )

        with st.expander("Advanced thresholds"):
            st.caption("Override the Verdict decision rule cutoffs.")
            st.number_input(
                "Wait at ratio ≥",
                min_value=0.10, max_value=1.0, step=0.05, format="%.2f",
                key="profile_threshold_wait",
            )
            st.number_input(
                "Proceed at ratio ≤",
                min_value=0.05, max_value=1.0, step=0.05, format="%.2f",
                key="profile_threshold_proceed",
            )


def current_profile() -> Profile:
    """Build a typed Profile from the current session state."""
    return Profile(
        monthly_income=int(st.session_state["profile_income"]),
        dwelling_type=st.session_state["profile_dwelling"],
        town=st.session_state["profile_town"],
        vehicle_category=st.session_state["profile_vehicle_cat"],
        vehicle_price=int(st.session_state["profile_vehicle_price"]),
        loan_tenure_years=int(st.session_state["profile_tenure"]),
        stress_coe_mult=float(st.session_state["profile_stress_coe_mult"]),
        stress_rate_add=float(st.session_state["profile_stress_rate_add"]),
        threshold_wait=float(st.session_state["profile_threshold_wait"]),
        threshold_proceed=float(st.session_state["profile_threshold_proceed"]),
    )
