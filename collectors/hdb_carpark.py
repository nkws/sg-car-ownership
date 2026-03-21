"""Collector for HDB carpark data.

Primary source: data.gov.sg real-time carpark availability API (gives total lots per carpark).
Supplementary: HDB carpark information CSV (gives address, town, type).
"""

import requests
import pandas as pd
from database import get_conn, log_refresh
from config import TOWN_REGIONS

CARPARK_AVAILABILITY_URL = "https://api.data.gov.sg/v1/transport/carpark-availability"

# HDB carpark number prefix -> town mapping (common prefixes)
# HDB carpark numbers follow patterns like "ACB" = Ang Mo Kio area
CARPARK_PREFIX_TOWN = {
    "A": "Ang Mo Kio", "ACB": "Ang Mo Kio", "ACM": "Ang Mo Kio", "AK": "Ang Mo Kio",
    "AM": "Ang Mo Kio",
    "B": "Bukit Merah", "BB": "Bukit Batok", "BBM": "Bukit Batok",
    "BJ": "Bukit Panjang", "BN": "Bedok",
    "BR": "Bedok", "BRB": "Bedok",
    "C": "Clementi", "CK": "Choa Chu Kang", "CKM": "Choa Chu Kang",
    "CR": "Central",
    "CT": "Clementi",
    "D": "Bukit Merah",
    "E": "Pasir Ris",
    "FR": "Bukit Merah",
    "G": "Geylang",
    "GSM": "Geylang",
    "H": "Toa Payoh", "HE": "Hougang", "HG": "Hougang",
    "HLM": "Kallang/Whampoa",
    "J": "Jurong East", "JE": "Jurong East", "JW": "Jurong West",
    "K": "Kallang/Whampoa", "KE": "Kallang/Whampoa",
    "MP": "Marine Parade",
    "N": "Sembawang",
    "P": "Pasir Ris", "PE": "Pasir Ris", "PP": "Punggol",
    "Q": "Queenstown",
    "RHM": "Toa Payoh",
    "S": "Serangoon", "SE": "Sengkang", "SK": "Sengkang",
    "SB": "Sembawang", "SBM": "Sembawang",
    "T": "Tampines", "TM": "Tampines", "TP": "Toa Payoh",
    "W": "Woodlands", "WL": "Woodlands",
    "Y": "Yishun", "YS": "Yishun",
}


def fetch_carpark_availability():
    """Fetch real-time carpark availability from data.gov.sg."""
    print("Fetching carpark availability from data.gov.sg...")
    resp = requests.get(CARPARK_AVAILABILITY_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    if not items:
        return None

    carpark_data = items[0].get("carpark_data", [])
    rows = []
    for cp in carpark_data:
        cp_no = cp.get("carpark_number", "")
        info_list = cp.get("carpark_info", [])
        total_lots = sum(int(i.get("total_lots", 0)) for i in info_list)
        lots_available = sum(int(i.get("lots_available", 0)) for i in info_list)

        town = _match_town(cp_no)
        rows.append({
            "car_park_no": cp_no,
            "town": town,
            "total_lots": total_lots,
            "lots_available": lots_available,
            "utilisation": round(1 - lots_available / max(total_lots, 1), 4),
            "update_datetime": cp.get("update_datetime", ""),
        })

    return pd.DataFrame(rows)


def _match_town(carpark_no):
    """Match a carpark number to a town using prefix patterns."""
    if not carpark_no:
        return "Unknown"

    # Try longest prefix match first
    for length in range(min(len(carpark_no), 4), 0, -1):
        prefix = carpark_no[:length]
        if prefix in CARPARK_PREFIX_TOWN:
            return CARPARK_PREFIX_TOWN[prefix]

    return "Unknown"


def store_carpark_data(df):
    """Store carpark data in SQLite."""
    with get_conn() as conn:
        df.to_sql("hdb_carpark", conn, if_exists="replace", index=False)

    count = len(df)
    log_refresh("hdb_carpark", count)
    print(f"Stored {count} carpark records")
    return count


def get_lots_by_town():
    """Get total carpark lots aggregated by town."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT town,
                   COUNT(*) as num_carparks,
                   SUM(total_lots) as total_lots,
                   AVG(utilisation) as avg_utilisation
            FROM hdb_carpark
            WHERE town != 'Unknown'
            GROUP BY town
            ORDER BY total_lots DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def run():
    """Main collector entry point."""
    print("=== HDB Carpark Collector ===")
    df = fetch_carpark_availability()
    if df is not None and not df.empty:
        count = store_carpark_data(df)

        # Print summary
        by_town = df[df["town"] != "Unknown"].groupby("town").agg(
            carparks=("car_park_no", "count"),
            total_lots=("total_lots", "sum"),
        ).sort_values("total_lots", ascending=False)
        print(f"\nTop towns by carpark lots:")
        for town, row in by_town.head(10).iterrows():
            print(f"  {town}: {row['total_lots']:,} lots ({row['carparks']} carparks)")

        return count
    print("No carpark data retrieved")
    return 0


if __name__ == "__main__":
    run()
