"""SQLite database setup and helpers."""

import sqlite3
from contextlib import contextmanager
from config import DB_PATH, DATA_DIR


def init_db():
    """Create all tables if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    return DB_PATH


@contextmanager
def get_conn():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS coe_results (
    month TEXT,
    bidding_no TEXT,
    vehicle_class TEXT,
    quota INTEGER,
    bids_success INTEGER,
    bids_received INTEGER,
    premium REAL,
    PRIMARY KEY (month, bidding_no, vehicle_class)
);

CREATE TABLE IF NOT EXISTS hdb_carpark (
    car_park_no TEXT PRIMARY KEY,
    address TEXT,
    town TEXT,
    car_park_type TEXT,
    type_of_parking TEXT,
    total_lots INTEGER,
    night_parking TEXT,
    free_parking TEXT
);

CREATE TABLE IF NOT EXISTS household_income (
    year INTEGER,
    dwelling_type TEXT,
    income_bracket TEXT,
    percentage REAL,
    median_income REAL,
    PRIMARY KEY (year, dwelling_type, income_bracket)
);

CREATE TABLE IF NOT EXISTS car_cost_model (
    segment TEXT,
    coe_category TEXT,
    monthly_total_cost REAL,
    monthly_loan REAL,
    monthly_insurance REAL,
    monthly_road_tax REAL,
    monthly_petrol REAL,
    monthly_parking REAL,
    monthly_maintenance REAL,
    PRIMARY KEY (segment, coe_category)
);

CREATE TABLE IF NOT EXISTS town_profile (
    town TEXT PRIMARY KEY,
    region TEXT,
    total_carpark_lots INTEGER,
    estimated_car_households INTEGER,
    median_income REAL,
    car_cost_ratio REAL,
    stress_segment TEXT,
    fsi_score REAL
);

CREATE TABLE IF NOT EXISTS fsi_history (
    date TEXT,
    segment TEXT,
    fsi_score REAL,
    coe_component REAL,
    credit_component REAL,
    affordability_component REAL,
    PRIMARY KEY (date, segment)
);

CREATE TABLE IF NOT EXISTS data_refresh_log (
    source TEXT,
    last_updated TEXT,
    records_count INTEGER,
    status TEXT,
    PRIMARY KEY (source)
);
"""


def log_refresh(source, count, status="success"):
    """Log a data refresh event."""
    from datetime import datetime
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO data_refresh_log VALUES (?, ?, ?, ?)",
            (source, datetime.now().isoformat(), count, status)
        )


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
