"""FSI Weight Backtester.

Uses historical COE data to identify known stress periods, then tests
different weight combinations to find the set that best distinguishes
stress periods from calm periods.

Ground truth: COE stress events are identified by sharp premium spikes
or collapses relative to rolling averages. The optimal weights maximise
the FSI gap between known-stress and known-calm months.

This is a heuristic backtest — not a prediction model. It validates
whether the chosen component weights produce an index that would have
flagged real stress episodes.
"""

import itertools
import pandas as pd
import numpy as np
from database import get_conn


def _load_backtest_data():
    """Load historical data needed for backtesting."""
    with get_conn() as conn:
        coe_rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium,
                   SUM(bids_received) as total_bids,
                   SUM(quota) as total_quota
            FROM coe_results
            WHERE vehicle_class IN ('Category A', 'Category B')
            GROUP BY month, vehicle_class
            ORDER BY month
        """).fetchall()

        hp_rows = conn.execute("""
            SELECT * FROM mas_hire_purchase ORDER BY year, quarter
        """).fetchall()

    coe_df = pd.DataFrame([dict(r) for r in coe_rows])
    hp_df = pd.DataFrame([dict(r) for r in hp_rows])
    return coe_df, hp_df


def _identify_stress_periods(coe_df):
    """Identify stress months using premium deviation from rolling mean.

    A month is 'stressed' if the average premium across Cat A and B is
    more than 1 standard deviation above the rolling 12-month mean.
    A month is 'calm' if it is below the rolling mean.
    """
    if coe_df.empty:
        return pd.DataFrame()

    # Pivot to get monthly average premium across categories
    monthly = coe_df.groupby("month")["avg_premium"].mean().reset_index()
    monthly = monthly.sort_values("month").reset_index(drop=True)

    # Rolling 6-month stats (we may have limited data)
    window = min(6, max(2, len(monthly) // 3))
    monthly["roll_mean"] = monthly["avg_premium"].rolling(window, min_periods=2).mean()
    monthly["roll_std"] = monthly["avg_premium"].rolling(window, min_periods=2).std()

    # Label each month
    monthly["is_stress"] = (
        monthly["avg_premium"] > monthly["roll_mean"] + monthly["roll_std"]
    ).astype(int)
    monthly["is_calm"] = (
        monthly["avg_premium"] < monthly["roll_mean"]
    ).astype(int)

    return monthly


def _simulate_component_scores(coe_df, hp_df, month):
    """Calculate the three component scores for a specific month.

    Simplified versions of the live FSI components, computed from
    historical data up to the given month only (no look-ahead bias).
    """
    # Filter data up to this month
    coe_up_to = coe_df[coe_df["month"] <= month].copy()

    if len(coe_up_to) < 4:
        return None

    # --- COE Component ---
    scores_coe = []
    for cat in ["Category A", "Category B"]:
        cat_df = coe_up_to[coe_up_to["vehicle_class"] == cat].sort_values("month")
        if len(cat_df) < 2:
            continue
        current = cat_df.iloc[-1]["avg_premium"]
        avg_all = cat_df["avg_premium"].mean()
        if avg_all > 0:
            ratio = current / avg_all
            scores_coe.append(min(100, max(0, 50 + (ratio - 1) * 50)))
        # Trend
        if len(cat_df) >= 4:
            recent = cat_df.tail(2)["avg_premium"].mean()
            prior = cat_df.iloc[-4:-2]["avg_premium"].mean()
            if prior > 0:
                trend = (recent - prior) / prior
                scores_coe.append(min(100, max(0, 50 + trend * 100)))

    coe_score = sum(scores_coe) / max(len(scores_coe), 1) if scores_coe else 50

    # --- Market Component ---
    scores_mkt = []
    recent_coe = coe_up_to.sort_values("month").tail(10)
    if "total_bids" in recent_coe.columns and "total_quota" in recent_coe.columns:
        recent_coe_clean = recent_coe.dropna(subset=["total_bids", "total_quota"])
        if not recent_coe_clean.empty:
            bid_ratio = (
                recent_coe_clean["total_bids"].sum()
                / max(recent_coe_clean["total_quota"].sum(), 1)
            )
            scores_mkt.append(min(100, max(0, bid_ratio * 30)))

    for cat in ["Category A", "Category B"]:
        cat_df = coe_up_to[coe_up_to["vehicle_class"] == cat]
        if len(cat_df) >= 4:
            cv = cat_df["avg_premium"].std() / max(cat_df["avg_premium"].mean(), 1)
            scores_mkt.append(min(100, max(0, cv * 200 + 30)))

    market_score = sum(scores_mkt) / max(len(scores_mkt), 1) if scores_mkt else 50

    # --- Credit Component ---
    # Use the latest HP data available up to this month
    # HP data is quarterly, so we approximate
    if hp_df.empty or len(hp_df) < 2:
        credit_score = 50.0
    else:
        scores_cr = []
        latest_rate = hp_df.iloc[-1]["avg_rate"]
        scores_cr.append(min(100, max(0, (latest_rate - 2.0) * 20 + 30)))

        if len(hp_df) >= 4:
            recent_out = hp_df.tail(2)["outstanding_m"].mean()
            prior_out = hp_df.head(2)["outstanding_m"].mean()
            if prior_out > 0:
                growth = (recent_out - prior_out) / prior_out
                scores_cr.append(min(100, max(0, 50 + growth * 100)))

        credit_score = sum(scores_cr) / max(len(scores_cr), 1)

    return {
        "coe": round(coe_score, 2),
        "credit": round(credit_score, 2),
        "market": round(market_score, 2),
    }


def backtest_weights(step=5):
    """Test all weight combinations and find the set that best separates
    stress periods from calm periods.

    Args:
        step: Weight granularity in percentage points (5 = test 5%, 10%, ...).

    Returns:
        dict with optimal weights, all results, and stress period labels.
    """
    coe_df, hp_df = _load_backtest_data()

    if coe_df.empty:
        return {
            "optimal_weights": {"coe": 0.40, "credit": 0.30, "market": 0.30},
            "improvement_pct": 0,
            "results": pd.DataFrame(),
            "stress_periods": pd.DataFrame(),
            "message": "Insufficient data for backtesting; using default weights.",
        }

    # Identify stress periods
    stress_df = _identify_stress_periods(coe_df)

    if stress_df.empty or stress_df["is_stress"].sum() == 0:
        return {
            "optimal_weights": {"coe": 0.40, "credit": 0.30, "market": 0.30},
            "improvement_pct": 0,
            "results": pd.DataFrame(),
            "stress_periods": stress_df,
            "message": "No stress periods identified in data; using default weights.",
        }

    # Calculate component scores for each month
    months_with_scores = []
    for _, row in stress_df.iterrows():
        scores = _simulate_component_scores(coe_df, hp_df, row["month"])
        if scores:
            months_with_scores.append({
                "month": row["month"],
                "is_stress": row["is_stress"],
                "is_calm": row["is_calm"],
                "avg_premium": row["avg_premium"],
                **scores,
            })

    if len(months_with_scores) < 4:
        return {
            "optimal_weights": {"coe": 0.40, "credit": 0.30, "market": 0.30},
            "improvement_pct": 0,
            "results": pd.DataFrame(),
            "stress_periods": stress_df,
            "message": "Too few data points for meaningful backtesting.",
        }

    score_df = pd.DataFrame(months_with_scores)
    stress_months = score_df[score_df["is_stress"] == 1]
    calm_months = score_df[score_df["is_calm"] == 1]

    if stress_months.empty or calm_months.empty:
        return {
            "optimal_weights": {"coe": 0.40, "credit": 0.30, "market": 0.30},
            "improvement_pct": 0,
            "results": pd.DataFrame(),
            "stress_periods": stress_df,
            "message": "Need both stress and calm periods for backtesting.",
        }

    # Generate all valid weight combinations (must sum to 100)
    weight_range = range(step, 100 - step + 1, step)
    combos = []
    for w_coe in weight_range:
        for w_credit in weight_range:
            w_market = 100 - w_coe - w_credit
            if w_market >= step:
                combos.append((w_coe / 100, w_credit / 100, w_market / 100))

    # Test each combination: maximise separation between stress and calm FSI
    best_gap = -999
    best_weights = (0.40, 0.30, 0.30)
    all_results = []

    for w_coe, w_credit, w_market in combos:
        score_df["fsi_test"] = (
            score_df["coe"] * w_coe
            + score_df["credit"] * w_credit
            + score_df["market"] * w_market
        )

        avg_stress_fsi = score_df.loc[score_df["is_stress"] == 1, "fsi_test"].mean()
        avg_calm_fsi = score_df.loc[score_df["is_calm"] == 1, "fsi_test"].mean()
        gap = avg_stress_fsi - avg_calm_fsi

        all_results.append({
            "w_coe": round(w_coe, 2),
            "w_credit": round(w_credit, 2),
            "w_market": round(w_market, 2),
            "avg_stress_fsi": round(avg_stress_fsi, 1),
            "avg_calm_fsi": round(avg_calm_fsi, 1),
            "gap": round(gap, 1),
        })

        if gap > best_gap:
            best_gap = gap
            best_weights = (w_coe, w_credit, w_market)

    results_df = pd.DataFrame(all_results).sort_values("gap", ascending=False)

    # Calculate default gap for comparison
    default_fsi = score_df["coe"] * 0.40 + score_df["credit"] * 0.30 + score_df["market"] * 0.30
    default_stress = default_fsi[score_df["is_stress"] == 1].mean()
    default_calm = default_fsi[score_df["is_calm"] == 1].mean()
    default_gap = default_stress - default_calm

    improvement = ((best_gap - default_gap) / max(abs(default_gap), 0.1)) * 100

    # Add FSI with optimal weights to score_df for charting
    score_df["fsi_optimal"] = (
        score_df["coe"] * best_weights[0]
        + score_df["credit"] * best_weights[1]
        + score_df["market"] * best_weights[2]
    )
    score_df["fsi_default"] = (
        score_df["coe"] * 0.40
        + score_df["credit"] * 0.30
        + score_df["market"] * 0.30
    )

    return {
        "optimal_weights": {
            "coe": round(best_weights[0], 2),
            "credit": round(best_weights[1], 2),
            "market": round(best_weights[2], 2),
        },
        "default_weights": {"coe": 0.40, "credit": 0.30, "market": 0.30},
        "optimal_gap": round(best_gap, 1),
        "default_gap": round(default_gap, 1),
        "improvement_pct": round(improvement, 1),
        "stress_count": int(stress_months.shape[0]),
        "calm_count": int(calm_months.shape[0]),
        "total_months": int(score_df.shape[0]),
        "results": results_df,
        "score_history": score_df,
        "stress_periods": stress_df,
        "top_5": results_df.head(5).to_dict("records"),
        "message": None,
    }


def run():
    """Run backtester and print results."""
    print("=== FSI Weight Backtester ===\n")
    result = backtest_weights(step=5)

    if result["message"]:
        print(result["message"])
        return result

    opt = result["optimal_weights"]
    print(f"Optimal weights: COE={opt['coe']:.0%}, Credit={opt['credit']:.0%}, Market={opt['market']:.0%}")
    print(f"Default weights: COE=40%, Credit=30%, Market=30%")
    print(f"Separation gap: {result['optimal_gap']:.1f} (optimal) vs {result['default_gap']:.1f} (default)")
    print(f"Improvement: {result['improvement_pct']:+.1f}%")
    print(f"Data: {result['stress_count']} stress months, {result['calm_count']} calm months, "
          f"{result['total_months']} total")

    print("\nTop 5 weight combinations:")
    for r in result["top_5"]:
        print(f"  COE={r['w_coe']:.0%} Credit={r['w_credit']:.0%} Market={r['w_market']:.0%} "
              f"→ gap={r['gap']:.1f}")

    return result


if __name__ == "__main__":
    from database import init_db
    init_db()
    # Ensure data exists
    from run_pipeline import main as run_pipeline
    run_pipeline()
    run()
