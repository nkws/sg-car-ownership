"""Financial Stress Index (FSI) Engine.

Composite index combining:
1. COE affordability component (40%) — cost-to-income ratio trends
2. Credit stress component (30%) — hire purchase volumes and rates
3. Market signal component (30%) — COE premium trends, utilisation shifts

Score range: 0 (no stress) to 100 (maximum stress).
"""

import pandas as pd
from datetime import datetime
from database import get_conn, log_refresh
from config import SEGMENT_THRESHOLDS


def calculate_coe_component():
    """COE affordability component: how expensive are cars relative to income?

    Scores 0-100 based on:
    - Current Cat A premium vs 5-year average
    - Current Cat B premium vs 5-year average
    - Month-over-month premium trend
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium
            FROM coe_results
            WHERE vehicle_class IN ('Category A', 'Category B')
            GROUP BY month, vehicle_class
            ORDER BY month DESC
        """).fetchall()

    if not rows:
        return 50.0  # neutral if no data

    df = pd.DataFrame([dict(r) for r in rows])

    scores = []
    for cat in ["Category A", "Category B"]:
        cat_df = df[df["vehicle_class"] == cat].sort_values("month", ascending=False)
        if len(cat_df) < 2:
            continue

        current = cat_df.iloc[0]["avg_premium"]
        avg_all = cat_df["avg_premium"].mean()
        avg_recent_12 = cat_df.head(24)["avg_premium"].mean()  # ~12 months (2 exercises/month)

        # Score: how far above average is current premium?
        if avg_all > 0:
            ratio = current / avg_all
            # ratio of 1.0 = average → score 50
            # ratio of 1.5 = 50% above average → score 75
            # ratio of 0.5 = 50% below average → score 25
            score = min(100, max(0, 50 + (ratio - 1) * 50))
            scores.append(score)

        # Trend component: is it rising or falling?
        if len(cat_df) >= 4:
            recent = cat_df.head(4)["avg_premium"].mean()
            prior = cat_df.iloc[4:8]["avg_premium"].mean() if len(cat_df) >= 8 else avg_all
            if prior > 0:
                trend = (recent - prior) / prior
                trend_score = min(100, max(0, 50 + trend * 100))
                scores.append(trend_score)

    return round(sum(scores) / max(len(scores), 1), 1)


def calculate_credit_component():
    """Credit stress component: are hire purchase volumes and rates rising?

    Scores 0-100 based on:
    - Outstanding HP growth rate
    - HP interest rate level
    - New HP volume trend
    """
    with get_conn() as conn:
        try:
            rows = conn.execute("""
                SELECT * FROM mas_hire_purchase
                ORDER BY year, quarter
            """).fetchall()
        except Exception:
            return 50.0

    if len(rows) < 2:
        return 50.0

    df = pd.DataFrame([dict(r) for r in rows])

    scores = []

    # Outstanding HP growth
    if len(df) >= 4:
        recent_outstanding = df.tail(2)["outstanding_m"].mean()
        prior_outstanding = df.head(2)["outstanding_m"].mean()
        if prior_outstanding > 0:
            growth = (recent_outstanding - prior_outstanding) / prior_outstanding
            # 10% growth → score 60, 20% growth → score 70
            scores.append(min(100, max(0, 50 + growth * 100)))

    # Interest rate level
    latest_rate = df.iloc[-1]["avg_rate"]
    # 2.5% → score 40, 3.0% → score 50, 3.5% → score 60, 4.0% → score 70
    rate_score = min(100, max(0, (latest_rate - 2.0) * 20 + 30))
    scores.append(rate_score)

    # New HP volume trend
    if len(df) >= 4:
        recent_vol = df.tail(2)["new_hp_volume"].mean()
        prior_vol = df.iloc[-4:-2]["new_hp_volume"].mean()
        if prior_vol > 0:
            vol_change = (recent_vol - prior_vol) / prior_vol
            # Rising volume with rising rates = stress
            scores.append(min(100, max(0, 50 + vol_change * 50)))

    return round(sum(scores) / max(len(scores), 1), 1)


def calculate_market_component():
    """Market signal component: COE market dynamics.

    Scores 0-100 based on:
    - Bid-to-quota ratio (competition intensity)
    - Premium volatility
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class,
                   quota, bids_received, bids_success, premium
            FROM coe_results
            WHERE vehicle_class IN ('Category A', 'Category B')
            ORDER BY month DESC
            LIMIT 40
        """).fetchall()

    if not rows:
        return 50.0

    df = pd.DataFrame([dict(r) for r in rows])

    scores = []

    # Bid-to-quota ratio
    if "bids_received" in df.columns and "quota" in df.columns:
        df["bid_ratio"] = df["bids_received"] / df["quota"].replace(0, 1)
        recent_ratio = df.head(10)["bid_ratio"].mean()
        # ratio 1.0 = no competition → score 30
        # ratio 2.0 = double competition → score 70
        scores.append(min(100, max(0, recent_ratio * 30)))

    # Premium volatility (coefficient of variation)
    for cat in ["Category A", "Category B"]:
        cat_df = df[df["vehicle_class"] == cat]
        if len(cat_df) >= 4:
            cv = cat_df["premium"].std() / max(cat_df["premium"].mean(), 1)
            # Higher volatility → higher stress
            scores.append(min(100, max(0, cv * 200 + 30)))

    return round(sum(scores) / max(len(scores), 1), 1)


def calculate_fsi():
    """Calculate the composite Financial Stress Index.

    Weights:
    - COE affordability: 40%
    - Credit stress: 30%
    - Market signals: 30%
    """
    coe_comp = calculate_coe_component()
    credit_comp = calculate_credit_component()
    market_comp = calculate_market_component()

    fsi = (coe_comp * 0.40) + (credit_comp * 0.30) + (market_comp * 0.30)
    fsi = round(fsi, 1)

    print(f"FSI Components:")
    print(f"  COE Affordability: {coe_comp:.1f}/100 (weight: 40%)")
    print(f"  Credit Stress:     {credit_comp:.1f}/100 (weight: 30%)")
    print(f"  Market Signals:    {market_comp:.1f}/100 (weight: 30%)")
    print(f"  Composite FSI:     {fsi:.1f}/100")

    return {
        "fsi_score": fsi,
        "coe_component": coe_comp,
        "credit_component": credit_comp,
        "market_component": market_comp,
        "timestamp": datetime.now().isoformat(),
    }


def calculate_segment_fsi():
    """Calculate FSI per dwelling segment."""
    from models.ratio_model import map_income_to_segments

    base_fsi = calculate_fsi()
    segments_df = map_income_to_segments()

    segment_scores = []
    for _, row in segments_df.iterrows():
        ratio = row["cost_to_income_ratio"]

        # Higher ratio = more stressed = higher FSI for that segment
        # Scale: ratio 0.1 → FSI modifier -20, ratio 0.5 → FSI modifier +30
        modifier = (ratio - 0.25) * 100
        seg_fsi = min(100, max(0, base_fsi["fsi_score"] + modifier))

        segment_scores.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "dwelling_type": row["dwelling_type"],
            "coe_category": row["coe_category"],
            "segment": row["segment"],
            "fsi_score": round(seg_fsi, 1),
            "coe_component": base_fsi["coe_component"],
            "credit_component": base_fsi["credit_component"],
            "affordability_component": round(ratio * 100, 1),
        })

    df = pd.DataFrame(segment_scores)

    # Store history
    with get_conn() as conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO fsi_history
                (date, segment, fsi_score, coe_component, credit_component, affordability_component)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (row["date"], f"{row['dwelling_type']}_{row['coe_category']}",
                  row["fsi_score"], row["coe_component"],
                  row["credit_component"], row["affordability_component"]))

    log_refresh("fsi_scores", len(df))
    return base_fsi, df


def run():
    """Calculate and display FSI."""
    print("=== Financial Stress Index ===")
    base_fsi, segment_df = calculate_segment_fsi()

    print(f"\nSegment FSI Scores:")
    for _, row in segment_df.sort_values("fsi_score", ascending=False).iterrows():
        print(f"  {row['dwelling_type']} × {row['coe_category']}: "
              f"FSI={row['fsi_score']:.0f} ({row['segment']})")

    return base_fsi, segment_df


if __name__ == "__main__":
    from database import init_db
    init_db()
    run()
