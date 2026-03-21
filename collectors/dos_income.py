"""Collector for DOS (SingStat) household income data.

SingStat Table Builder API provides household income distribution
by dwelling type, which we use to map income bands to housing types.
"""

import requests
import pandas as pd
from database import get_conn, log_refresh
from config import SINGSTAT_BASE, SINGSTAT_TABLES


# Fallback data: DOS 2022/23 Household Expenditure Survey key figures
# Source: singstat.gov.sg - if API fails, we use these known values
FALLBACK_INCOME_BY_DWELLING = {
    2023: {
        "HDB 1-2 Room": {"median_income": 2340, "pct_households": 7.5},
        "HDB 3 Room": {"median_income": 4744, "pct_households": 17.8},
        "HDB 4 Room": {"median_income": 7870, "pct_households": 24.2},
        "HDB 5 Room/Exec": {"median_income": 10600, "pct_households": 18.1},
        "Condo/Private Apt": {"median_income": 16388, "pct_households": 17.5},
        "Landed Property": {"median_income": 21540, "pct_households": 10.5},
    }
}

# Detailed income brackets by dwelling type (% of households)
FALLBACK_INCOME_BRACKETS = {
    2023: {
        "HDB 1-2 Room": [
            ("Below $2,000", 52.0),
            ("$2,000-$3,999", 28.0),
            ("$4,000-$5,999", 11.0),
            ("$6,000-$9,999", 6.0),
            ("$10,000 & Over", 3.0),
        ],
        "HDB 3 Room": [
            ("Below $2,000", 22.0),
            ("$2,000-$3,999", 24.0),
            ("$4,000-$5,999", 20.0),
            ("$6,000-$9,999", 20.0),
            ("$10,000 & Over", 14.0),
        ],
        "HDB 4 Room": [
            ("Below $2,000", 10.0),
            ("$2,000-$3,999", 14.0),
            ("$4,000-$5,999", 16.0),
            ("$6,000-$9,999", 26.0),
            ("$10,000 & Over", 34.0),
        ],
        "HDB 5 Room/Exec": [
            ("Below $2,000", 6.0),
            ("$2,000-$3,999", 10.0),
            ("$4,000-$5,999", 12.0),
            ("$6,000-$9,999", 24.0),
            ("$10,000 & Over", 48.0),
        ],
        "Condo/Private Apt": [
            ("Below $2,000", 4.0),
            ("$2,000-$3,999", 5.0),
            ("$4,000-$5,999", 7.0),
            ("$6,000-$9,999", 16.0),
            ("$10,000 & Over", 68.0),
        ],
        "Landed Property": [
            ("Below $2,000", 3.0),
            ("$2,000-$3,999", 4.0),
            ("$4,000-$5,999", 5.0),
            ("$6,000-$9,999", 12.0),
            ("$10,000 & Over", 76.0),
        ],
    }
}


def fetch_singstat_table(table_id):
    """Fetch data from SingStat Table Builder API."""
    url = f"{SINGSTAT_BASE}/{table_id}"
    headers = {"Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"SingStat API error: {e}")
        return None


def parse_income_data(raw_data):
    """Parse SingStat JSON response into structured DataFrame."""
    if not raw_data or "Data" not in raw_data:
        return None

    rows = []
    for record in raw_data["Data"].get("row", []):
        row_text = record.get("rowText", "")
        for col in record.get("columns", []):
            rows.append({
                "dwelling_type": row_text,
                "year": col.get("key", ""),
                "value": col.get("value", ""),
            })

    return pd.DataFrame(rows) if rows else None


def store_income_data(df=None):
    """Store income data in SQLite. Falls back to hardcoded data if df is None."""
    rows = []

    if df is not None and not df.empty:
        # Parse API data
        for _, row in df.iterrows():
            rows.append({
                "year": int(row.get("year", 2023)),
                "dwelling_type": row.get("dwelling_type", ""),
                "income_bracket": row.get("income_bracket", "All"),
                "percentage": float(row.get("value", 0)),
                "median_income": 0,
            })
    else:
        # Use fallback data
        print("Using fallback DOS income data (2022/23 HES)")
        for year, dwellings in FALLBACK_INCOME_BRACKETS.items():
            for dwelling, brackets in dwellings.items():
                median = FALLBACK_INCOME_BY_DWELLING[year][dwelling]["median_income"]
                for bracket, pct in brackets:
                    rows.append({
                        "year": year,
                        "dwelling_type": dwelling,
                        "income_bracket": bracket,
                        "percentage": pct,
                        "median_income": median,
                    })

    df_store = pd.DataFrame(rows)

    with get_conn() as conn:
        df_store.to_sql("household_income", conn, if_exists="replace", index=False)

    count = len(df_store)
    log_refresh("household_income", count)
    print(f"Stored {count} household income records")
    return count


def get_income_by_dwelling():
    """Get median income by dwelling type."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT dwelling_type, median_income,
                   SUM(CASE WHEN income_bracket LIKE '%10,000%' THEN percentage ELSE 0 END) as pct_high_income
            FROM household_income
            WHERE year = (SELECT MAX(year) FROM household_income)
            GROUP BY dwelling_type
            ORDER BY median_income DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def run():
    """Main collector entry point."""
    print("=== DOS Income Collector ===")

    # Try SingStat API first
    table_id = SINGSTAT_TABLES["household_income_by_dwelling"]
    raw = fetch_singstat_table(table_id)

    if raw:
        df = parse_income_data(raw)
        if df is not None and not df.empty:
            count = store_income_data(df)
            return count

    # Fallback to hardcoded data
    count = store_income_data(None)
    return count


if __name__ == "__main__":
    run()
