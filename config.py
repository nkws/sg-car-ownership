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
