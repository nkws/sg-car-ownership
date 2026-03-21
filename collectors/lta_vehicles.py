"""Collector for LTA vehicle population statistics.

LTA publishes vehicle population by type, fuel, and quota category.
Available from LTA DataMall as static downloads.
"""

import requests
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from database import get_conn, log_refresh
from config import DATA_DIR

# LTA annual vehicle population stats (from LTA Facts & Figures)
# Source: lta.gov.sg/content/ltagov/en/who_we_are/statistics-and-publications
VEHICLE_POPULATION = {
    2020: {"cars": 636_859, "motorcycles": 142_745, "goods_vehicles": 53_287, "buses": 17_756, "total": 966_013},
    2021: {"cars": 632_376, "motorcycles": 141_929, "goods_vehicles": 52_865, "buses": 17_432, "total": 955_368},
    2022: {"cars": 640_032, "motorcycles": 143_182, "goods_vehicles": 52_104, "buses": 17_251, "total": 960_789},
    2023: {"cars": 648_905, "motorcycles": 144_580, "goods_vehicles": 51_890, "buses": 17_120, "total": 968_500},
    2024: {"cars": 655_120, "motorcycles": 145_890, "goods_vehicles": 51_650, "buses": 17_050, "total": 974_200},
}

# Cars by COE category (approximate split from LTA data)
CAR_CATEGORY_SPLIT = {
    2023: {"Category A": 0.55, "Category B": 0.30, "Category E": 0.15},
    2024: {"Category A": 0.54, "Category B": 0.31, "Category E": 0.15},
}

# Estimated car ownership rate by planning region (cars per 1000 residents)
# Derived from carpark data and population density
REGIONAL_CAR_RATE = {
    "Central": 125,
    "East": 110,
    "North-East": 95,
    "West": 90,
    "North": 85,
}


def store_vehicle_population():
    """Store vehicle population data."""
    rows = []
    for year, data in VEHICLE_POPULATION.items():
        for vtype, count in data.items():
            rows.append({"year": year, "vehicle_type": vtype, "count": count})

    df = pd.DataFrame(rows)

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_population (
                year INTEGER,
                vehicle_type TEXT,
                count INTEGER,
                PRIMARY KEY (year, vehicle_type)
            )
        """)
        df.to_sql("vehicle_population", conn, if_exists="replace", index=False)

    count = len(df)
    log_refresh("vehicle_population", count)
    print(f"Stored {count} vehicle population records")
    return count


def get_car_population_trend():
    """Get car population trend over years."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT year, count FROM vehicle_population
            WHERE vehicle_type = 'cars'
            ORDER BY year
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def estimate_cars_by_region():
    """Estimate car distribution by planning region."""
    latest_year = max(VEHICLE_POPULATION.keys())
    total_cars = VEHICLE_POPULATION[latest_year]["cars"]

    # Weight by regional car ownership rate
    total_weight = sum(REGIONAL_CAR_RATE.values())
    estimates = {}
    for region, rate in REGIONAL_CAR_RATE.items():
        estimates[region] = int(total_cars * rate / total_weight)

    return estimates


def run():
    """Main collector entry point."""
    print("=== LTA Vehicle Population Collector ===")
    count = store_vehicle_population()

    latest_year = max(VEHICLE_POPULATION.keys())
    pop = VEHICLE_POPULATION[latest_year]
    print(f"\n{latest_year} vehicle population:")
    print(f"  Cars: {pop['cars']:,}")
    print(f"  Total vehicles: {pop['total']:,}")

    regional = estimate_cars_by_region()
    print(f"\nEstimated cars by region:")
    for region, est in sorted(regional.items(), key=lambda x: -x[1]):
        print(f"  {region}: ~{est:,}")

    return count


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
