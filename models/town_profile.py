"""Town-level financial profiling.

Cross-references carpark data (proxy for car ownership density) with
income estimates and regional car ownership rates to build town-level profiles.
"""

import pandas as pd
from database import get_conn, log_refresh
from config import TOWN_REGIONS, SEGMENT_THRESHOLDS
from collectors.lta_vehicles import REGIONAL_CAR_RATE

# Approximate median household income by town group
# Derived from DOS data + HDB resale price proxies
TOWN_INCOME_ESTIMATES = {
    # Central (higher income)
    "Bishan": 11500, "Bukit Timah": 18000, "Marine Parade": 13500,
    "Queenstown": 12000, "Toa Payoh": 9500, "Bukit Merah": 9000,
    "Central": 14000, "Kallang/Whampoa": 9200, "Geylang": 8500,
    # East
    "Bedok": 9800, "Tampines": 10200, "Pasir Ris": 10800,
    # North-East
    "Ang Mo Kio": 9600, "Hougang": 9400, "Serangoon": 10500,
    "Sengkang": 11000, "Punggol": 11500,
    # West
    "Bukit Batok": 9200, "Bukit Panjang": 9800, "Choa Chu Kang": 9500,
    "Clementi": 10800, "Jurong East": 9000, "Jurong West": 8800,
    # North
    "Sembawang": 9300, "Woodlands": 8700, "Yishun": 8900,
}


def build_town_profiles():
    """Build financial profiles for each HDB town."""
    # Get carpark data by town
    with get_conn() as conn:
        carpark_rows = conn.execute("""
            SELECT town, COUNT(*) as num_carparks, SUM(total_lots) as total_lots,
                   AVG(utilisation) as avg_utilisation
            FROM hdb_carpark
            WHERE town != 'Unknown'
            GROUP BY town
        """).fetchall()

    # Get latest car cost
    try:
        from models.ratio_model import calculate_all_costs
        costs = calculate_all_costs()
        cat_a_cost = costs["cat_a"]["monthly_total"]
        cat_b_cost = costs["cat_b"]["monthly_total"]
    except Exception:
        cat_a_cost = 2400
        cat_b_cost = 3100

    # Weighted average car cost (55% Cat A, 45% Cat B based on category split)
    avg_car_cost = cat_a_cost * 0.55 + cat_b_cost * 0.45

    profiles = []
    for row in carpark_rows:
        town = row["town"]
        region = TOWN_REGIONS.get(town, "Unknown")
        total_lots = row["total_lots"] or 0

        # Estimate car-owning households
        # Season parking ≈ 70-85% of lots → resident cars
        regional_rate = REGIONAL_CAR_RATE.get(region, 95)
        season_factor = 0.75  # approx season parking proportion
        estimated_cars = int(total_lots * season_factor)

        # Get income estimate
        median_income = TOWN_INCOME_ESTIMATES.get(town, 9500)

        # Calculate cost-to-income ratio
        ratio = avg_car_cost / median_income if median_income > 0 else 999

        # Determine stress segment
        segment = "E_distressed"
        for seg_name, (low, high) in SEGMENT_THRESHOLDS.items():
            if low <= ratio < high:
                segment = seg_name
                break

        # FSI score for town (simplified)
        fsi = min(100, max(0, ratio * 150))

        profiles.append({
            "town": town,
            "region": region,
            "total_carpark_lots": total_lots,
            "estimated_car_households": estimated_cars,
            "median_income": median_income,
            "car_cost_ratio": round(ratio, 4),
            "stress_segment": segment,
            "fsi_score": round(fsi, 1),
        })

    df = pd.DataFrame(profiles)

    # Store in database
    with get_conn() as conn:
        df.to_sql("town_profile", conn, if_exists="replace", index=False)

    log_refresh("town_profiles", len(df))
    return df


def get_stressed_towns(min_fsi=40):
    """Get towns above stress threshold."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM town_profile
            WHERE fsi_score >= ?
            ORDER BY fsi_score DESC
        """, (min_fsi,)).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def run():
    """Build and display town profiles."""
    print("=== Town-Level Financial Profiles ===")
    df = build_town_profiles()

    print(f"\nTown profiles ({len(df)} towns):")
    for _, row in df.sort_values("fsi_score", ascending=False).iterrows():
        print(f"  {row['town']:20s} | Income: ${row['median_income']:>6,} | "
              f"Ratio: {row['car_cost_ratio']:.1%} | FSI: {row['fsi_score']:5.1f} | "
              f"{row['stress_segment']}")

    return df


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
