"""Collector for CPF contribution data by wage band.

CPF publishes annual statistical reports with contribution distributions.
This gives us another income proxy cross-reference.
"""

import pandas as pd
from database import get_conn, log_refresh

# CPF Annual Report - Distribution of active CPF members by wage band
# Source: cpf.gov.sg/employer/cpf-contributions
# These figures are from CPF Annual Reports 2022-2023
CPF_WAGE_DISTRIBUTION = {
    2023: [
        ("Below $500", 3.2, 250),
        ("$500 - $999", 4.8, 750),
        ("$1,000 - $1,499", 5.1, 1250),
        ("$1,500 - $1,999", 5.9, 1750),
        ("$2,000 - $2,499", 6.8, 2250),
        ("$2,500 - $2,999", 6.5, 2750),
        ("$3,000 - $3,499", 6.2, 3250),
        ("$3,500 - $3,999", 5.8, 3750),
        ("$4,000 - $4,499", 5.3, 4250),
        ("$4,500 - $4,999", 4.7, 4750),
        ("$5,000 - $5,999", 8.2, 5500),
        ("$6,000 - $6,999", 6.5, 6500),
        ("$7,000 - $7,999", 5.1, 7500),
        ("$8,000 - $8,999", 4.0, 8500),
        ("$9,000 - $9,999", 3.1, 9500),
        ("$10,000 - $11,999", 4.8, 11000),
        ("$12,000 - $14,999", 4.2, 13500),
        ("$15,000 & Above", 5.8, 18000),
    ],
}


def store_cpf_data():
    """Store CPF wage distribution data."""
    rows = []
    for year, bands in CPF_WAGE_DISTRIBUTION.items():
        for band_label, pct_members, midpoint in bands:
            rows.append({
                "year": year,
                "wage_band": band_label,
                "pct_members": pct_members,
                "midpoint_wage": midpoint,
            })

    df = pd.DataFrame(rows)

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cpf_wages (
                year INTEGER,
                wage_band TEXT,
                pct_members REAL,
                midpoint_wage REAL,
                PRIMARY KEY (year, wage_band)
            )
        """)
        df.to_sql("cpf_wages", conn, if_exists="replace", index=False)

    count = len(df)
    log_refresh("cpf_wages", count)
    print(f"Stored {count} CPF wage band records")
    return count


def get_car_affordable_pct(monthly_car_cost, max_ratio=0.35):
    """Calculate what % of workers can afford a car at given ratio threshold."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT wage_band, pct_members, midpoint_wage
            FROM cpf_wages
            WHERE year = (SELECT MAX(year) FROM cpf_wages)
            ORDER BY midpoint_wage
        """).fetchall()

    min_income_needed = monthly_car_cost / max_ratio
    affordable_pct = sum(
        r["pct_members"] for r in rows
        if r["midpoint_wage"] >= min_income_needed
    )
    return round(affordable_pct, 1)


def run():
    """Main collector entry point."""
    print("=== CPF Wage Data Collector ===")
    count = store_cpf_data()

    # Show affordability preview
    from models.ratio_model import calculate_monthly_car_cost
    cat_a_cost = calculate_monthly_car_cost("cat_a")["monthly_total"]
    cat_b_cost = calculate_monthly_car_cost("cat_b")["monthly_total"]

    pct_a = get_car_affordable_pct(cat_a_cost)
    pct_b = get_car_affordable_pct(cat_b_cost)
    print(f"Workers who can afford Cat A at <35% income: {pct_a}%")
    print(f"Workers who can afford Cat B at <35% income: {pct_b}%")

    return count


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
