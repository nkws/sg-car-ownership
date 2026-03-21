"""Collector for COE bidding results.

Primary source: LTA DataMall static download (ZIP containing CSV).
Fallback: local cached CSV file.
"""

import requests
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from database import get_conn, log_refresh
from config import DATA_DIR

LTA_COE_ZIP_URL = (
    "https://datamall.lta.gov.sg/content/dam/datamall/datasets/"
    "Facts_Figures/Vehicle Registration/COE Bidding Results.zip"
)
LOCAL_COE_CSV = DATA_DIR / "coe_raw" / "COE Bidding Results" / "M11-coe_results.csv"


def fetch_coe_results():
    """Fetch COE bidding results — try LTA download, fall back to local file."""
    # Try downloading fresh from LTA
    try:
        print("Downloading COE data from LTA DataMall...")
        resp = requests.get(LTA_COE_ZIP_URL, timeout=60)
        resp.raise_for_status()

        # Extract CSV from ZIP
        with ZipFile(BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith("coe_results.csv")]
            if csv_names:
                with zf.open(csv_names[0]) as f:
                    df = pd.read_csv(f)
                    print(f"Downloaded {len(df)} records from LTA")
                    return df
    except Exception as e:
        print(f"LTA download failed: {e}")

    # Fallback to local file
    if LOCAL_COE_CSV.exists():
        print(f"Loading local COE data from {LOCAL_COE_CSV}")
        return pd.read_csv(LOCAL_COE_CSV)

    print("No COE data available")
    return None


def store_coe_results(df):
    """Clean and store COE results in SQLite."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    expected = ["month", "bidding_no", "vehicle_class", "quota",
                "bids_success", "bids_received", "premium"]

    # Keep only columns we need
    cols = [c for c in expected if c in df.columns]
    df_clean = df[cols].copy()

    # Convert types
    for col in ["quota", "bids_success", "bids_received", "premium"]:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    with get_conn() as conn:
        df_clean.to_sql("coe_results", conn, if_exists="replace", index=False)

    count = len(df_clean)
    log_refresh("coe_results", count)
    print(f"Stored {count} COE bidding records")
    return count


def get_latest_premiums():
    """Get the most recent COE premiums by category."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT vehicle_class, premium, month
            FROM coe_results
            WHERE month = (SELECT MAX(month) FROM coe_results)
            ORDER BY vehicle_class
        """).fetchall()
    return {row["vehicle_class"]: row["premium"] for row in rows}


def get_premium_history(months=24):
    """Get COE premium history for trend analysis."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium
            FROM coe_results
            GROUP BY month, vehicle_class
            ORDER BY month DESC
            LIMIT ?
        """, (months * 5,)).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def run():
    """Main collector entry point."""
    print("=== COE Premium Collector ===")
    df = fetch_coe_results()
    if df is not None and not df.empty:
        return store_coe_results(df)
    print("No COE data retrieved")
    return 0


if __name__ == "__main__":
    run()
