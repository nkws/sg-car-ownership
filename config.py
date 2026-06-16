"""Configuration for SG Car Ownership Financial Profiling Pipeline."""

import os
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "sg_car_ownership.db"
SIGNAL_FILE = DATA_DIR / "fsi_signal.json"

# data.gov.sg API
DATAGOVSG_BASE = "https://data.gov.sg/api/action/datastore_search"
DATAGOVSG_V2_BASE = "https://api-open.data.gov.sg/v1/public"

# Dataset IDs on data.gov.sg (CKAN resource IDs)
DATASETS = {
    "coe_results": "d_862948de751847e3847050ce7740e5ae",
    "hdb_carpark_info": "d_23f946fa557947f93a8c62c43a6b8687",
}

# DOS (SingStat) Table Builder API
SINGSTAT_BASE = "https://tablebuilder.singstat.gov.sg/api/table/tabledata"
SINGSTAT_TABLES = {
    "household_income_by_dwelling": "M810361",   # Monthly household income by dwelling type
    "household_expenditure": "M810421",           # Average monthly household expenditure
}

# Known monthly car ownership costs (SGD, 2024-2025 estimates)
# Used for income-to-car-cost ratio model
#
# IMPORTANT: Singapore car loan rates are advertised as FLAT rates, not EIR.
# A 2.78% flat rate ≈ 5.2% EIR for a 7-year loan.
# Flat rate formula: total_interest = principal × flat_rate × years
# This is how banks/dealers quote and compute repayments in SG.
CAR_COSTS = {
    "cat_a": {  # Cars up to 1600cc
        "coe_premium_avg": 95000,     # Will be overwritten by actual data
        "loan_tenure_months": 84,     # 7 years typical
        "loan_flat_rate": 0.028,      # 2.8% p.a. FLAT rate (advertised rate)
        "insurance_annual": 1800,
        "road_tax_annual": 742,
        "petrol_monthly": 300,
        "parking_monthly": 110,       # HDB season parking
        "maintenance_monthly": 150,
        "vehicle_base_price": 80000,  # Typical Cat A car OMV + dealer margin
    },
    "cat_b": {  # Cars above 1600cc
        "coe_premium_avg": 130000,
        "loan_tenure_months": 84,
        "loan_flat_rate": 0.028,      # 2.8% p.a. FLAT rate (advertised rate)
        "insurance_annual": 2800,
        "road_tax_annual": 1500,
        "petrol_monthly": 400,
        "parking_monthly": 110,
        "maintenance_monthly": 200,
        "vehicle_base_price": 120000,
    },
    # EV variants — same COE categories (an EV bids in Cat A or Cat B by power
    # output), but cheaper "fuel" (electricity) and a different road-tax basis.
    # Upfront cost is offset by EEAI/VES rebates (see EV_INCENTIVES) which the
    # ratio model applies to the financed base.
    "cat_a_ev": {  # EVs qualifying for Cat A (≤110kW)
        "coe_premium_avg": 95000,
        "loan_tenure_months": 84,
        "loan_flat_rate": 0.028,
        "insurance_annual": 2000,
        "road_tax_annual": 1100,       # EV road tax incl. additional flat component
        "petrol_monthly": 90,          # home/public charging equivalent
        "parking_monthly": 110,
        "maintenance_monthly": 90,     # EVs cheaper to maintain
        "vehicle_base_price": 90000,
    },
    "cat_b_ev": {  # EVs qualifying for Cat B (>110kW)
        "coe_premium_avg": 130000,
        "loan_tenure_months": 84,
        "loan_flat_rate": 0.028,
        "insurance_annual": 3000,
        "road_tax_annual": 2300,
        "petrol_monthly": 130,
        "parking_monthly": 110,
        "maintenance_monthly": 120,
        "vehicle_base_price": 130000,
    },
}

# Which categories are electric — used by the ratio model and DHI.
EV_CATEGORIES = {"cat_a_ev", "cat_b_ev"}

# EV purchase incentives and their sunset dates. The EEAI rebate steps down to
# $0 from Jan 2027; VES Band A1 rebate continues. Amounts in SGD. These drive
# the "EEAI cliff" calculator and the Decision Hurdle Index urgency offset.
EV_INCENTIVES = {
    "eeai_current": 15000,            # Electric Vehicle Early Adoption Incentive (45% of ARF, capped)
    "eeai_sunset": "2027-01-01",      # EEAI drops to $0 from this date
    "ves_rebate": 15000,              # Vehicle Emissions Scheme Band A1 rebate (continues)
}

# Known forward-looking policy dates that raise decision uncertainty or create
# act-now urgency. Consumed by models/decision_index.py.
POLICY_CLIFFS = {
    "eeai_sunset":        "2027-01-01",  # EV rebate to $0
    "vgr_review":         "2028-02-01",  # 0% vehicle growth rate review
    "buying_window_open": "2026-07-01",  # thesis primary window opens
    "buying_window_close":"2026-11-30",  # thesis primary window closes
}

# Cat A premium below which the thesis says to bid (the "$95K trigger").
COE_BUY_TRIGGER_CAT_A = 95000

# ── Decision Hurdle Index (DHI) ──────────────────────────────────────────────
# Forward-looking composite (0-100, higher = harder to confidently buy NOW),
# layered on top of the financial-only FSI. Weights sum the four hurdles; the
# urgency factor is subtracted (opportunity cost of waiting). See
# models/decision_index.py for the component definitions.
DHI_WEIGHTS = {
    "affordability": 0.35,   # can the household sustain it
    "timing":        0.30,   # is now a bad time to buy (prices elevated, reversal likely)
    "commitment":    0.20,   # liquidity + 10-year lock-in
    "policy":        0.15,   # policy-cliff uncertainty
    "urgency":       0.30,   # SUBTRACTED — cost of waiting (EEAI cliff, window proximity)
}

# DHI score → recommendation band cutoffs (mirrors the verdict thresholds).
DHI_BANDS = {
    "proceed_below": 40,     # DHI ≤ 40 → Proceed with caution
    "wait_above":    65,     # DHI ≥ 65 → Wait; between → Caution
}

# Town-level mapping for geographic analysis
# Maps HDB towns to approximate planning regions
TOWN_REGIONS = {
    "Ang Mo Kio": "North-East",
    "Bedok": "East",
    "Bishan": "Central",
    "Bukit Batok": "West",
    "Bukit Merah": "Central",
    "Bukit Panjang": "West",
    "Bukit Timah": "Central",
    "Central": "Central",
    "Choa Chu Kang": "West",
    "Clementi": "West",
    "Geylang": "Central",
    "Hougang": "North-East",
    "Jurong East": "West",
    "Jurong West": "West",
    "Kallang/Whampoa": "Central",
    "Marine Parade": "Central",
    "Pasir Ris": "East",
    "Punggol": "North-East",
    "Queenstown": "Central",
    "Sembawang": "North",
    "Sengkang": "North-East",
    "Serangoon": "North-East",
    "Tampines": "East",
    "Toa Payoh": "Central",
    "Woodlands": "North",
    "Yishun": "North",
}

# Segmentation thresholds (car cost as % of gross monthly income)
SEGMENT_THRESHOLDS = {
    "A_affluent":    (0.00, 0.15),  # <15% of income on car
    "B_comfortable": (0.15, 0.25),  # 15-25%
    "C_stretched":   (0.25, 0.35),  # 25-35%
    "D_stressed":    (0.35, 0.50),  # 35-50%
    "E_distressed":  (0.50, 1.00),  # >50%
}

# Google Sheets (configure when ready)
GOOGLE_SHEETS = {
    "credentials_file": os.getenv("GOOGLE_CREDS_FILE", "credentials.json"),
    "spreadsheet_name": "SG Car Ownership - Financial Profiling",
}
