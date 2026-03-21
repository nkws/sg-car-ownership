"""Collector for URA private property carpark utilisation.

URA publishes quarterly carpark statistics for private developments.
This helps proxy car ownership in private housing areas.
"""

import pandas as pd
from database import get_conn, log_refresh

# URA quarterly carpark utilisation for private residential
# Source: ura.gov.sg/Corporate/Media-Room/Media-Releases
# Average utilisation rates by planning area (approximate)
URA_CARPARK_UTILISATION = {
    (2024, 3): {
        "Core Central Region": {"lots": 45000, "utilisation": 0.72, "season_pct": 0.65},
        "Rest of Central Region": {"lots": 38000, "utilisation": 0.78, "season_pct": 0.70},
        "Outside Central Region": {"lots": 52000, "utilisation": 0.85, "season_pct": 0.80},
    },
    (2024, 4): {
        "Core Central Region": {"lots": 45200, "utilisation": 0.73, "season_pct": 0.66},
        "Rest of Central Region": {"lots": 38100, "utilisation": 0.79, "season_pct": 0.71},
        "Outside Central Region": {"lots": 52300, "utilisation": 0.86, "season_pct": 0.81},
    },
    (2025, 1): {
        "Core Central Region": {"lots": 45400, "utilisation": 0.74, "season_pct": 0.67},
        "Rest of Central Region": {"lots": 38200, "utilisation": 0.80, "season_pct": 0.72},
        "Outside Central Region": {"lots": 52500, "utilisation": 0.87, "season_pct": 0.82},
    },
}


def store_ura_data():
    """Store URA carpark data."""
    rows = []
    for (year, quarter), regions in URA_CARPARK_UTILISATION.items():
        for region, data in regions.items():
            rows.append({
                "period": f"{year}-Q{quarter}",
                "year": year,
                "quarter": quarter,
                "region": region,
                "total_lots": data["lots"],
                "utilisation": data["utilisation"],
                "season_parking_pct": data["season_pct"],
            })

    df = pd.DataFrame(rows)

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ura_carpark (
                period TEXT,
                year INTEGER,
                quarter INTEGER,
                region TEXT,
                total_lots INTEGER,
                utilisation REAL,
                season_parking_pct REAL,
                PRIMARY KEY (period, region)
            )
        """)
        df.to_sql("ura_carpark", conn, if_exists="replace", index=False)

    count = len(df)
    log_refresh("ura_carpark", count)
    print(f"Stored {count} URA carpark records")
    return count


def get_private_car_estimate():
    """Estimate private property car ownership from season parking rates."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT region, total_lots, utilisation, season_parking_pct
            FROM ura_carpark
            WHERE period = (SELECT MAX(period) FROM ura_carpark)
        """).fetchall()

    estimates = {}
    for r in rows:
        # Season parking % approximates resident car ownership
        estimated_cars = int(r["total_lots"] * r["season_parking_pct"])
        estimates[r["region"]] = {
            "lots": r["total_lots"],
            "estimated_resident_cars": estimated_cars,
            "utilisation": r["utilisation"],
        }
    return estimates


def run():
    """Main collector entry point."""
    print("=== URA Private Carpark Collector ===")
    count = store_ura_data()

    estimates = get_private_car_estimate()
    print("\nPrivate residential car estimates:")
    for region, data in estimates.items():
        print(f"  {region}: ~{data['estimated_resident_cars']:,} cars "
              f"({data['utilisation']:.0%} utilisation)")

    return count


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
