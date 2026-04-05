"""COE Tipping Point / Reversal Detection Module.

Detects whether COE premiums are in a confirmed reversal using multiple
technical and fundamental signals from bidding data.

Signals used:
1. Price trend — 3 consecutive lower highs = downtrend
2. Overbidding ratio — bids_received / quota falling = weakening demand
3. Moving averages — price crossing below 3-month MA
4. Rate of change — month-on-month premium change accelerating/decelerating
5. Quota pressure — deregistrations and quota announcements

Reversal states:
- STABLE      — no reversal signals
- WATCH       — 1 signal triggered
- POSSIBLE    — 2 signals triggered
- LIKELY      — 3 signals triggered
- CONFIRMED   — 4+ signals triggered
"""

import pandas as pd
import numpy as np
from database import get_conn


def get_coe_series(category="Category A"):
    """Get monthly COE premium series for a category."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, premium, quota, bids_received, bids_success
            FROM coe_results
            WHERE vehicle_class LIKE ?
            ORDER BY month, bidding_no
        """, (f"%{category}%",)).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])

    # Aggregate to monthly (there are typically 2 bidding exercises per month)
    monthly = df.groupby("month").agg({
        "premium": "mean",
        "quota": "sum",
        "bids_received": "sum",
        "bids_success": "sum",
    }).reset_index()

    monthly = monthly.sort_values("month").reset_index(drop=True)
    return monthly


def signal_lower_highs(series, lookback=6):
    """Check for consecutive lower highs in premium.

    Returns:
        (triggered: bool, detail: str, consecutive_lower: int)
    """
    if len(series) < lookback:
        return False, "Insufficient data", 0

    recent = series["premium"].tail(lookback).values
    consecutive_lower = 0

    for i in range(len(recent) - 1, 0, -1):
        if recent[i] < recent[i - 1]:
            consecutive_lower += 1
        else:
            break

    triggered = consecutive_lower >= 3
    detail = f"{consecutive_lower} consecutive lower periods"
    return triggered, detail, consecutive_lower


def signal_overbidding_ratio(series, lookback=4):
    """Check if overbidding ratio (bids/quota) is declining.

    A falling ratio means demand is weakening relative to supply.
    """
    if len(series) < lookback or "bids_received" not in series.columns:
        return False, "Insufficient data", None

    series = series.copy()
    series["overbid_ratio"] = series["bids_received"] / series["quota"].replace(0, np.nan)

    recent_ratios = series["overbid_ratio"].tail(lookback).values
    if len(recent_ratios) < 2:
        return False, "Insufficient data", None

    # Check if trending down
    declining_count = sum(1 for i in range(1, len(recent_ratios))
                          if recent_ratios[i] < recent_ratios[i - 1])

    ratio_now = recent_ratios[-1]
    triggered = declining_count >= (lookback - 2) and ratio_now < 2.0
    detail = f"Overbid ratio: {ratio_now:.2f}x ({declining_count}/{lookback - 1} periods declining)"
    return triggered, detail, ratio_now


def signal_ma_crossover(series, short_window=3, long_window=6):
    """Check if premium crossed below its moving average.

    Short MA crossing below long MA = bearish signal.
    """
    if len(series) < long_window:
        return False, "Insufficient data", None

    series = series.copy()
    series["ma_short"] = series["premium"].rolling(short_window).mean()
    series["ma_long"] = series["premium"].rolling(long_window).mean()

    latest = series.iloc[-1]
    if pd.isna(latest["ma_short"]) or pd.isna(latest["ma_long"]):
        return False, "Insufficient data for MA", None

    crossed_below = latest["ma_short"] < latest["ma_long"]
    spread_pct = (latest["ma_short"] - latest["ma_long"]) / latest["ma_long"] * 100

    detail = f"{short_window}mo MA ${latest['ma_short']:,.0f} vs {long_window}mo MA ${latest['ma_long']:,.0f} ({spread_pct:+.1f}%)"
    return crossed_below, detail, spread_pct


def signal_rate_of_change(series, lookback=3):
    """Check if rate of premium change is accelerating downward."""
    if len(series) < lookback + 1:
        return False, "Insufficient data", None

    series = series.copy()
    series["pct_change"] = series["premium"].pct_change() * 100

    recent_changes = series["pct_change"].tail(lookback).values
    recent_changes = recent_changes[~np.isnan(recent_changes)]

    if len(recent_changes) < 2:
        return False, "Insufficient data", None

    avg_change = np.mean(recent_changes)
    latest_change = recent_changes[-1]

    # Triggered if average recent change is negative and accelerating
    triggered = avg_change < -2.0  # more than 2% average decline
    detail = f"Avg change: {avg_change:+.1f}%, latest: {latest_change:+.1f}%"
    return triggered, detail, avg_change


def signal_quota_pressure(series):
    """Check if quota is increasing (supply expanding = downward pressure)."""
    if len(series) < 4:
        return False, "Insufficient data", None

    recent_quota = series["quota"].tail(4).values
    quota_trend = np.polyfit(range(len(recent_quota)), recent_quota, 1)[0]

    triggered = quota_trend > 50  # quota growing by >50 per period
    detail = f"Quota trend: {quota_trend:+.0f}/period, latest: {recent_quota[-1]:,.0f}"
    return triggered, detail, quota_trend


def detect_reversal(category="Category A"):
    """Run all reversal signals for a COE category.

    Returns dict with:
        - state: STABLE / WATCH / POSSIBLE / LIKELY / CONFIRMED
        - score: 0-5 (number of signals triggered)
        - signals: list of signal results
        - summary: human-readable summary
    """
    series = get_coe_series(category)

    if series.empty:
        return {
            "category": category,
            "state": "NO DATA",
            "score": 0,
            "signals": [],
            "summary": "No COE data available for analysis.",
            "premium_current": None,
            "premium_3mo_avg": None,
            "premium_6mo_avg": None,
        }

    signals = []

    # Signal 1: Lower highs
    triggered, detail, consecutive = signal_lower_highs(series)
    signals.append({
        "name": "Consecutive Lower Premiums",
        "triggered": triggered,
        "detail": detail,
        "description": "3+ consecutive periods of falling COE premiums",
    })

    # Signal 2: Overbidding ratio
    triggered, detail, ratio = signal_overbidding_ratio(series)
    signals.append({
        "name": "Overbidding Ratio Declining",
        "triggered": triggered,
        "detail": detail,
        "description": "Bid-to-quota ratio falling (demand weakening)",
    })

    # Signal 3: MA crossover
    triggered, detail, spread = signal_ma_crossover(series)
    signals.append({
        "name": "Moving Average Crossover",
        "triggered": triggered,
        "detail": detail,
        "description": "3-month MA below 6-month MA (bearish crossover)",
    })

    # Signal 4: Rate of change
    triggered, detail, roc = signal_rate_of_change(series)
    signals.append({
        "name": "Accelerating Decline",
        "triggered": triggered,
        "detail": detail,
        "description": "Average premium change worse than -2% per period",
    })

    # Signal 5: Quota pressure
    triggered, detail, qt = signal_quota_pressure(series)
    signals.append({
        "name": "Quota Expansion",
        "triggered": triggered,
        "detail": detail,
        "description": "COE quota increasing (supply rising)",
    })

    # Score and state
    score = sum(1 for s in signals if s["triggered"])
    states = {0: "STABLE", 1: "WATCH", 2: "POSSIBLE", 3: "LIKELY", 4: "CONFIRMED", 5: "CONFIRMED"}
    state = states.get(score, "CONFIRMED")

    # Premium stats
    premium_current = series["premium"].iloc[-1] if len(series) > 0 else None
    premium_3mo = series["premium"].tail(3).mean() if len(series) >= 3 else premium_current
    premium_6mo = series["premium"].tail(6).mean() if len(series) >= 6 else premium_current

    # Summary
    triggered_names = [s["name"] for s in signals if s["triggered"]]
    if score == 0:
        summary = f"{category}: No reversal signals. Market appears stable."
    elif score <= 2:
        summary = f"{category}: Early warning — {', '.join(triggered_names)}."
    else:
        summary = f"{category}: Reversal {'likely' if score == 3 else 'confirmed'} — {', '.join(triggered_names)}."

    return {
        "category": category,
        "state": state,
        "score": score,
        "signals": signals,
        "summary": summary,
        "premium_current": premium_current,
        "premium_3mo_avg": premium_3mo,
        "premium_6mo_avg": premium_6mo,
    }


def detect_all():
    """Run reversal detection for all COE categories."""
    results = {}
    for cat in ["Category A", "Category B"]:
        results[cat] = detect_reversal(cat)
    return results


if __name__ == "__main__":
    from database import init_db
    init_db()

    for cat, result in detect_all().items():
        print(f"\n{'=' * 60}")
        print(f"  {cat} — {result['state']} (score: {result['score']}/5)")
        print(f"{'=' * 60}")
        print(f"  {result['summary']}")
        if result["premium_current"]:
            print(f"  Current: ${result['premium_current']:,.0f} | "
                  f"3mo avg: ${result['premium_3mo_avg']:,.0f} | "
                  f"6mo avg: ${result['premium_6mo_avg']:,.0f}")
        print()
        for s in result["signals"]:
            icon = "🔴" if s["triggered"] else "⚪"
            print(f"  {icon} {s['name']}: {s['detail']}")
