"""Main entry point for the SG Car Ownership Financial Profiling Pipeline."""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db
from config import SIGNAL_FILE, DATA_DIR


def run_collectors():
    """Run all data collectors."""
    results = {}
    collectors = [
        ("coe", "collectors.coe_premium"),
        ("dos", "collectors.dos_income"),
        ("hdb", "collectors.hdb_carpark"),
        ("mas", "collectors.mas_credit"),
        ("cpf", "collectors.cpf_wages"),
        ("lta", "collectors.lta_vehicles"),
        ("ura", "collectors.ura_carpark"),
    ]

    for name, module_path in collectors:
        print("\n" + "=" * 50)
        try:
            mod = __import__(module_path, fromlist=["run"])
            results[name] = mod.run()
        except Exception as e:
            print(f"{name} collector error: {e}")
            results[name] = 0

    return results


def run_models():
    """Run all financial models."""
    print("\n" + "=" * 50)
    from models.ratio_model import run as run_ratio
    costs, segments_df = run_ratio()

    print("\n" + "=" * 50)
    from models.fsi import calculate_segment_fsi
    fsi_result, fsi_segments = calculate_segment_fsi()

    print("\n" + "=" * 50)
    from models.town_profile import run as run_towns
    town_df = run_towns()

    return costs, segments_df, fsi_result, fsi_segments, town_df


def generate_signal_file(costs, segments_df, fsi_result, town_df):
    """Generate the JSON signal file for WhatsApp bot consumption."""
    DATA_DIR.mkdir(exist_ok=True)

    # Build segment summary
    segment_summary = {}
    if segments_df is not None and not segments_df.empty:
        for seg in segments_df["segment"].unique():
            seg_data = segments_df[segments_df["segment"] == seg]
            avg_ratio = seg_data["cost_to_income_ratio"].mean()
            stress_map = {"A_affluent": "low", "B_comfortable": "low",
                          "C_stretched": "moderate", "D_stressed": "high",
                          "E_distressed": "critical"}
            segment_summary[seg] = {
                "stress": stress_map.get(seg, "unknown"),
                "avg_cost_to_income_ratio": round(avg_ratio, 4),
                "dwelling_types": list(seg_data["dwelling_type"].unique()),
            }

    # Top stressed towns
    stressed_towns = []
    if town_df is not None and not town_df.empty:
        top = town_df.sort_values("fsi_score", ascending=False).head(5)
        stressed_towns = [
            {"town": r["town"], "fsi": r["fsi_score"], "ratio": r["car_cost_ratio"]}
            for _, r in top.iterrows()
        ]

    cat_labels = {"cat_a": "Cat A", "cat_b": "Cat B"}

    signal = {
        "timestamp": datetime.now().isoformat(),
        "fsi_score": fsi_result["fsi_score"],
        "fsi_components": {
            "coe_affordability": fsi_result["coe_component"],
            "credit_stress": fsi_result["credit_component"],
            "market_signals": fsi_result["market_component"],
        },
        "fsi_trend": "stable",
        "car_costs": {
            cat: {"monthly_total": d["monthly_total"], "vehicle_cost": d["total_vehicle_cost"],
                   "label": cat_labels.get(cat, cat)}
            for cat, d in costs.items()
        },
        "segments": segment_summary,
        "top_stressed_towns": stressed_towns,
        "alerts": _generate_alerts(costs, segments_df, fsi_result, town_df),
    }

    with open(SIGNAL_FILE, "w") as f:
        json.dump(signal, f, indent=2)

    print(f"\nSignal file written to {SIGNAL_FILE}")
    return signal


def _generate_alerts(costs, segments_df, fsi_result, town_df):
    """Generate alert messages."""
    alerts = []

    # FSI level alerts
    fsi = fsi_result["fsi_score"]
    if fsi >= 70:
        alerts.append(f"FSI at {fsi:.0f}/100 — HIGH stress level")
    elif fsi >= 55:
        alerts.append(f"FSI at {fsi:.0f}/100 — elevated stress")

    # Car cost alerts
    cat_labels = {"cat_a": "Cat A", "cat_b": "Cat B"}
    for cat, data in costs.items():
        if data["monthly_total"] > 2500:
            alerts.append(f"{cat_labels.get(cat, cat)} monthly cost: ${data['monthly_total']:,.0f}")

    # Distressed segments
    if segments_df is not None and not segments_df.empty:
        distressed = segments_df[segments_df["segment"] == "E_distressed"]
        if not distressed.empty:
            dwellings = list(distressed["dwelling_type"].unique())
            alerts.append(f"Distressed: {', '.join(dwellings)}")

    # Stressed towns
    if town_df is not None and not town_df.empty:
        high_stress = town_df[town_df["fsi_score"] >= 45]
        if not high_stress.empty:
            towns = list(high_stress.sort_values("fsi_score", ascending=False)["town"].head(3))
            alerts.append(f"Top stressed towns: {', '.join(towns)}")

    if not alerts:
        alerts.append("No stress alerts at current levels")

    return alerts


def main():
    """Run the full pipeline."""
    print("SG Car Ownership Financial Profiling Pipeline")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    init_db()
    print("Database initialized")

    collector_results = run_collectors()
    print(f"\nCollector results: {collector_results}")

    costs, segments_df, fsi_result, fsi_segments, town_df = run_models()

    signal = generate_signal_file(costs, segments_df, fsi_result, town_df)

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE")
    print(f"FSI Score: {signal['fsi_score']}")
    print(f"Components: COE={fsi_result['coe_component']:.0f} | "
          f"Credit={fsi_result['credit_component']:.0f} | "
          f"Market={fsi_result['market_component']:.0f}")
    for alert in signal["alerts"]:
        print(f"  ⚠ {alert}")

    return signal


if __name__ == "__main__":
    main()
