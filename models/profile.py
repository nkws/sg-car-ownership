"""User profile schema for the Decide view.

A single Profile drives the Calculator, Stress Test, Affordability Cliff,
Town-Level Stress, and the Verdict panel — replacing what used to be
disconnected per-section inputs.

Stored at runtime in `st.session_state.profile` so it persists across
Streamlit reruns within a session.
"""

from __future__ import annotations

from typing import Literal, TypedDict


# Dwelling-type strings must match the values in the household_income table
# (see collectors/dos_income.py). Don't rename without updating the data layer.
DWELLING_TYPES: list[str] = [
    "HDB 1-2 Room",
    "HDB 3 Room",
    "HDB 4 Room",
    "HDB 5 Room/Exec",
    "Condo/Private Apt",
    "Landed Property",
]


# SG household monthly income percentiles, including employer CPF.
# Reference: DOS Household Expenditure Survey 2023 / Key Household Income Trends.
# These are population-level, not car-buying-cohort. Used as quick-pick presets;
# user can always type a custom value.
INCOME_PERCENTILES: dict[int, int] = {
    25: 5_500,
    50: 10_500,
    75: 17_000,
    90: 26_000,
}

INCOME_PERCENTILES_REFERENCE = "DOS HES 2023 — household incl. employer CPF"


# Default decision-rule thresholds for the Verdict panel.
# Stress ratio = stressed monthly car cost / monthly household income.
DEFAULT_THRESHOLD_WAIT = 0.50      # ≥ this → "Wait"
DEFAULT_THRESHOLD_PROCEED = 0.35   # ≤ this AND market stable → "Proceed with caution"


VehicleCategory = Literal["cat_a", "cat_b"]


class Profile(TypedDict):
    # Income & housing
    monthly_income: int          # SGD per month, household, gross
    dwelling_type: str           # one of DWELLING_TYPES
    town: str                    # HDB town name; "" = no preference

    # Vehicle target
    vehicle_category: VehicleCategory
    vehicle_price: int           # OMV + dealer markup, SGD
    loan_tenure_years: int       # 5, 6, or 7

    # Stress scenario the user wants applied throughout
    stress_coe_mult: float       # 1.0 = current; 1.5 = +50%
    stress_rate_add: float       # additional flat-rate pp; 0.0 = no change

    # Decision-rule thresholds (overridable in the sidebar)
    threshold_wait: float        # default 0.50
    threshold_proceed: float     # default 0.35


def default_profile() -> Profile:
    """Profile used on first load — median income, conservative defaults."""
    return Profile(
        monthly_income=INCOME_PERCENTILES[50],
        dwelling_type="HDB 4 Room",
        town="",
        vehicle_category="cat_a",
        vehicle_price=80_000,
        loan_tenure_years=7,
        stress_coe_mult=1.0,
        stress_rate_add=0.0,
        threshold_wait=DEFAULT_THRESHOLD_WAIT,
        threshold_proceed=DEFAULT_THRESHOLD_PROCEED,
    )
