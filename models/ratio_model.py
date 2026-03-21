"""Income-to-Car-Cost Ratio Model.

Calculates monthly car ownership cost per COE category,
then maps against income bands to determine affordability segments.
"""

import pandas as pd
from database import get_conn, log_refresh
from config import CAR_COSTS, SEGMENT_THRESHOLDS


def flat_to_eir(flat_rate, tenure_years):
    """Convert SG flat rate to approximate EIR.

    SG car loans use flat rate: interest = principal × flat_rate × years.
    The borrower pays interest on the full principal even as it amortises,
    so the effective rate is roughly 1.78× the flat rate for a 7-year loan.

    Uses the standard approximation: EIR ≈ (2 × n × flat_rate) / (n + 1)
    where n = number of years.
    """
    n = tenure_years
    return (2 * n * flat_rate) / (n + 1)


def calculate_monthly_car_cost(category="cat_a", coe_override=None, flat_rate_override=None):
    """Calculate total monthly cost of car ownership for a given COE category.

    Components:
    - Loan repayment (vehicle price + COE, minus 40% downpayment, over loan tenure)
    - Insurance (annualized)
    - Road tax (annualized)
    - Petrol
    - Parking
    - Maintenance

    IMPORTANT: SG car loans are computed using FLAT rates, not EIR.
    Flat rate formula: total_interest = principal × flat_rate × years.
    This is how banks and dealers quote and calculate repayments.
    """
    params = CAR_COSTS[category].copy()

    if coe_override is not None:
        params["coe_premium_avg"] = coe_override

    flat_rate = flat_rate_override if flat_rate_override is not None else params["loan_flat_rate"]

    # Total vehicle cost = base price + COE + ARF (approx 100% of OMV for simplicity)
    total_vehicle_cost = params["vehicle_base_price"] + params["coe_premium_avg"]

    # Loan: 60% financed (40% downpayment typical in SG)
    loan_amount = total_vehicle_cost * 0.60
    tenure = params["loan_tenure_months"]
    tenure_years = tenure / 12

    # Monthly loan repayment using SG flat rate method
    # total_interest = principal × flat_rate × years (charged on full principal)
    total_interest = loan_amount * flat_rate * tenure_years
    monthly_loan = (loan_amount + total_interest) / tenure

    # EIR for reference/display
    eir = flat_to_eir(flat_rate, tenure_years)

    # Monthly fixed costs
    monthly_insurance = params["insurance_annual"] / 12
    monthly_road_tax = params["road_tax_annual"] / 12
    monthly_petrol = params["petrol_monthly"]
    monthly_parking = params["parking_monthly"]
    monthly_maintenance = params["maintenance_monthly"]

    monthly_total = (
        monthly_loan
        + monthly_insurance
        + monthly_road_tax
        + monthly_petrol
        + monthly_parking
        + monthly_maintenance
    )

    return {
        "category": category,
        "monthly_total": round(monthly_total, 2),
        "monthly_loan": round(monthly_loan, 2),
        "monthly_insurance": round(monthly_insurance, 2),
        "monthly_road_tax": round(monthly_road_tax, 2),
        "monthly_petrol": round(monthly_petrol, 2),
        "monthly_parking": round(monthly_parking, 2),
        "monthly_maintenance": round(monthly_maintenance, 2),
        "total_vehicle_cost": round(total_vehicle_cost, 2),
        "loan_amount": round(loan_amount, 2),
        "flat_rate": round(flat_rate, 4),
        "eir": round(eir, 4),
    }


def calculate_all_costs():
    """Calculate costs for both COE categories, using latest COE data if available."""
    from collectors.coe_premium import get_latest_premiums

    latest_premiums = get_latest_premiums()
    results = {}

    for category in ["cat_a", "cat_b"]:
        # Try to use actual COE premium
        coe_override = None
        if latest_premiums:
            # COE data may use different labels
            for key, val in latest_premiums.items():
                if isinstance(key, str):
                    key_lower = key.lower()
                    if category == "cat_a" and ("cat a" in key_lower or "category a" in key_lower):
                        coe_override = val
                    elif category == "cat_b" and ("cat b" in key_lower or "category b" in key_lower):
                        coe_override = val

        results[category] = calculate_monthly_car_cost(category, coe_override)

    return results


def map_income_to_segments():
    """Map household income bands against car costs to determine stress segments.

    For each dwelling type, calculates what % of income goes to car ownership,
    and assigns a segment label (A through E).
    """
    costs = calculate_all_costs()

    with get_conn() as conn:
        income_rows = conn.execute("""
            SELECT DISTINCT dwelling_type, median_income
            FROM household_income
            WHERE median_income > 0
            ORDER BY median_income
        """).fetchall()

    segments = []
    for row in income_rows:
        dwelling = row["dwelling_type"]
        income = row["median_income"]

        for cat_key, cost_data in costs.items():
            monthly_cost = cost_data["monthly_total"]
            ratio = monthly_cost / income if income > 0 else 999

            # Determine segment
            segment = "E_distressed"
            for seg_name, (low, high) in SEGMENT_THRESHOLDS.items():
                if low <= ratio < high:
                    segment = seg_name
                    break

            segments.append({
                "dwelling_type": dwelling,
                "median_income": income,
                "coe_category": cat_key,
                "monthly_car_cost": monthly_cost,
                "cost_to_income_ratio": round(ratio, 4),
                "segment": segment,
            })

    return pd.DataFrame(segments)


def store_cost_model(costs):
    """Store calculated car costs in database."""
    rows = []
    for cat_key, data in costs.items():
        rows.append({
            "segment": "all",
            "coe_category": cat_key,
            "monthly_total_cost": data["monthly_total"],
            "monthly_loan": data["monthly_loan"],
            "monthly_insurance": data["monthly_insurance"],
            "monthly_road_tax": data["monthly_road_tax"],
            "monthly_petrol": data["monthly_petrol"],
            "monthly_parking": data["monthly_parking"],
            "monthly_maintenance": data["monthly_maintenance"],
        })

    df = pd.DataFrame(rows)
    with get_conn() as conn:
        df.to_sql("car_cost_model", conn, if_exists="replace", index=False)

    log_refresh("car_cost_model", len(rows))
    return rows


def stress_test(coe_multiplier=1.0, flat_rate_add=0.0):
    """Run stress test: what happens if COE rises or flat rates increase?

    Args:
        coe_multiplier: multiplier on current COE premium (1.0 = no change)
        flat_rate_add: additional percentage points on flat rate (not EIR).
                       E.g. 0.5 means flat rate goes from 2.8% to 3.3%.

    Returns segment shifts for each dwelling type.
    """
    results = []
    for category in ["cat_a", "cat_b"]:
        params = CAR_COSTS[category].copy()
        stressed_coe = params["coe_premium_avg"] * coe_multiplier
        stressed_flat_rate = params["loan_flat_rate"] + (flat_rate_add / 100)

        total_vehicle_cost = params["vehicle_base_price"] + stressed_coe
        loan_amount = total_vehicle_cost * 0.60
        tenure = params["loan_tenure_months"]
        tenure_years = tenure / 12

        # SG flat rate calculation
        total_interest = loan_amount * stressed_flat_rate * tenure_years
        monthly_loan = (loan_amount + total_interest) / tenure

        eir = flat_to_eir(stressed_flat_rate, tenure_years)

        monthly_total = (
            monthly_loan
            + params["insurance_annual"] / 12
            + params["road_tax_annual"] / 12
            + params["petrol_monthly"]
            + params["parking_monthly"]
            + params["maintenance_monthly"]
        )

        results.append({
            "category": category,
            "coe_multiplier": coe_multiplier,
            "flat_rate_add": flat_rate_add,
            "stressed_flat_rate": round(stressed_flat_rate, 4),
            "stressed_eir": round(eir, 4),
            "stressed_monthly_cost": round(monthly_total, 2),
        })

    return results


def run():
    """Calculate and store the ratio model."""
    print("=== Income-to-Car-Cost Ratio Model ===")

    costs = calculate_all_costs()
    store_cost_model(costs)

    print("\nMonthly car ownership costs:")
    for cat, data in costs.items():
        print(f"  {cat}: ${data['monthly_total']:,.2f}/month "
              f"(loan: ${data['monthly_loan']:,.2f}, "
              f"vehicle cost: ${data['total_vehicle_cost']:,.0f})")

    print("\nIncome-to-cost mapping:")
    segments_df = map_income_to_segments()
    if not segments_df.empty:
        for _, row in segments_df.iterrows():
            print(f"  {row['dwelling_type']} × {row['coe_category']}: "
                  f"ratio={row['cost_to_income_ratio']:.1%} → {row['segment']}")

    return costs, segments_df


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
