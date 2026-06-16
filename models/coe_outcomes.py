"""COE Bid Outlook — amalgamating quantitative and qualitative signals.

This module fuses the dashboard's two separate signal families into a single
forward-looking view of the possible outcomes of the next COE bidding:

  Quantitative
    - Reversal state / score      (models.coe_reversal.detect_reversal)
    - Premium trajectory stats    (analysis.coe_market._compute_market_stats:
                                    consecutive rises, correction-from-peak)
  Qualitative
    - Net structural force balance (analysis.coe_market.force_net)
    - Net policy direction         (analysis.policy_radar.policy_net)
    - Curated quarterly price band (analysis.coe_market.quarter_band_for)

Everything here is DETERMINISTIC and traceable: every number comes from a
named input signal under a rule documented as a module constant. There are
NO calibrated probabilities — likelihood is expressed as an ordinal "lean
score" mapped to a qualitative band (the same philosophy as Policy Radar's
evidence weights). The UI shows the band and the raw lean score side by side.

Two horizons are produced per category:
  - "next_exercise": the immediate next bidding round, ranges anchored on the
    current premium and clamped to the current quarter's curated band.
  - "next_quarter": the following quarter, ranges anchored on that quarter's
    curated band (bearish below the floor, base within, bullish above).
"""

from __future__ import annotations

from datetime import datetime

from models.coe_reversal import detect_reversal
from analysis.coe_market import (
    _load_recent_premiums,
    _compute_market_stats,
    _load_coe_freshness,
    force_net,
    quarter_band_for,
)
from analysis.policy_radar import policy_net


# ─── Synthesis constants (shown verbatim in the UI methodology) ───────────────

# Each contribution to the signed tilt score. Negative = bearish (premiums
# expected to ease), positive = bullish (premiums expected to firm).
TILT_RULES = [
    ("Reversal state", "−1 per triggered reversal signal (0 to −5)"),
    ("Momentum", "+1 per consecutive rising round, capped at +3"),
    ("Correction from peak", "+1 if already corrected > 15% from the peak"),
    ("Net force balance", "+1 if up−down > 50; −1 if down−up > 50; else 0"),
    ("Net policy direction", "+1 net-up · −1 net-down · 0 balanced/uncertain"),
]

# tilt_score → (label, color). Checked from the top; first match wins.
TILT_BANDS = [
    (3, "Bullish lean", "#e15759"),
    (1, "Slight bullish lean", "#f28e2b"),
    (0, "Balanced", "#9aa0a6"),
    (-2, "Slight bearish lean", "#edc949"),
    (-99, "Bearish lean", "#59a14f"),
]

# Base lean weights before tilt alignment is applied.
BASE_LEAN = {"Bearish dip": 3, "Base case": 5, "Bullish spike": 3}

# lean_score → (band, color). Checked from the top; first match wins.
LEAN_BANDS = [
    (6, "Most likely", "#59a14f"),
    (3, "Plausible", "#f28e2b"),
    (0, "Unlikely", "#9aa0a6"),
]

# One scenario step = 5% of the current premium — roughly the typical
# round-to-round swing in Cat A/B premiums.
STEP_PCT = 0.05


# ─── Small helpers ────────────────────────────────────────────────────────────

def _round100(x: float) -> int:
    """Round to the nearest $100 — premiums never resolve finer than that."""
    return int(round(x / 100.0) * 100)


def _suffix(category: str) -> str:
    """'Category A' -> 'a', 'Category B' -> 'b' (for _compute_market_stats keys)."""
    return "b" if category.strip().upper().endswith("B") else "a"


def _tilt_band(score: int) -> tuple[str, str]:
    for threshold, label, color in TILT_BANDS:
        if score >= threshold:
            return label, color
    return "Bearish lean", "#59a14f"


def _lean_band(score: int) -> tuple[str, str]:
    for threshold, label, color in LEAN_BANDS:
        if score >= threshold:
            return label, color
    return "Unlikely", "#9aa0a6"


# ─── Tilt: the directional spine ──────────────────────────────────────────────

def _compute_tilt(rev: dict, stats: dict, category: str, has_short_history: bool) -> dict:
    """Sum the five contributions into a signed tilt and a traceable driver list.

    Returns {"score", "label", "color", "drivers"} where each driver is
    {source, detail, direction, weight} and `weight` is its signed contribution.
    """
    suffix = _suffix(category)
    drivers: list[dict] = []
    score = 0

    # 1. Reversal — falling premiums are bearish. Skip if the category has no
    #    reversal data (e.g. running off the bundled snapshot).
    if rev.get("state") not in (None, "NO DATA") and rev.get("score") is not None:
        contrib = -int(rev["score"])
        score += contrib
        drivers.append({
            "source": "Reversal",
            "detail": rev.get("summary", f"{rev['state']} ({rev['score']}/5 signals)"),
            "direction": "down" if contrib < 0 else "neutral",
            "weight": contrib,
        })

    # 2. Momentum — a rising streak is bullish. Suppressed on short history.
    rises = int(stats.get(f"consecutive_rises_{suffix}", 0) or 0)
    if not has_short_history and rises > 0:
        contrib = min(rises, 3)
        score += contrib
        drivers.append({
            "source": "Momentum",
            "detail": f"Cat {suffix.upper()} has risen {rises} consecutive "
                      f"exercise{'s' if rises != 1 else ''}",
            "direction": "up",
            "weight": contrib,
        })

    # 3. Correction from peak — a big correction means less downside left.
    corr = float(stats.get(f"correction_pct_{suffix}", 0.0) or 0.0)
    if corr > 15:
        score += 1
        drivers.append({
            "source": "Correction",
            "detail": f"Already {corr:.0f}% off the window peak — limited "
                      f"further downside",
            "direction": "up",
            "weight": 1,
        })

    # 4. Net structural force balance.
    fn = force_net()
    if fn["lean"] == "up":
        contrib = 1
    elif fn["lean"] == "down":
        contrib = -1
    else:
        contrib = 0
    if contrib:
        score += contrib
        drivers.append({
            "source": "Force Balance",
            "detail": f"Upward forces {fn['up_total']} vs downward {fn['down_total']} "
                      f"(net {fn['net']:+d})",
            "direction": "up" if contrib > 0 else "down",
            "weight": contrib,
        })

    # 5. Net policy direction.
    pn = policy_net()
    if pn["net_direction"] == "up":
        contrib = 1
    elif pn["net_direction"] == "down":
        contrib = -1
    else:
        contrib = 0
    if contrib:
        score += contrib
        drivers.append({
            "source": "Policy",
            "detail": f"Strong policy signals lean {pn['net_direction']} "
                      f"({pn['strong_up']} up vs {pn['strong_down']} down)",
            "direction": "up" if contrib > 0 else "down",
            "weight": contrib,
        })

    label, color = _tilt_band(score)
    return {"score": score, "label": label, "color": color, "drivers": drivers}


# ─── Scenario construction ────────────────────────────────────────────────────

def _lean_scores(tilt_score: int) -> dict:
    """Derive per-scenario ordinal lean scores from the tilt (no probabilities)."""
    bear_add = abs(min(tilt_score, 0))
    bull_add = max(tilt_score, 0)
    scores = {
        "Bearish dip": BASE_LEAN["Bearish dip"] + bear_add - bull_add,
        "Base case": BASE_LEAN["Base case"] + (1 if abs(tilt_score) <= 1 else 0),
        "Bullish spike": BASE_LEAN["Bullish spike"] + bull_add - bear_add,
    }
    return {name: max(0, s) for name, s in scores.items()}


def _attach_likelihood(name: str, leans: dict) -> dict:
    score = leans[name]
    band, color = _lean_band(score)
    return {"lean_score": score, "band": band, "color": color}


def _scenario_drivers(name: str, all_drivers: list[dict]) -> list[dict]:
    """Drivers aligned with a scenario; base case shows the full picture."""
    if name == "Base case":
        return list(all_drivers)
    want = "down" if name == "Bearish dip" else "up"
    aligned = [d for d in all_drivers if d["direction"] == want]
    return aligned or list(all_drivers)


def _make_scenario(name: str, low: float, high: float, anchor: float,
                   leans: dict, all_drivers: list[dict]) -> dict:
    low_i, high_i = _round100(low), _round100(high)
    return {
        "name": name,
        "premium_low": low_i,
        "premium_high": high_i,
        "delta_low": low_i - int(anchor),
        "delta_high": high_i - int(anchor),
        "likelihood": _attach_likelihood(name, leans),
        "drivers": _scenario_drivers(name, all_drivers),
    }


def _pick_most_probable(scenarios: list[dict], horizon: str, category: str,
                        tilt_label: str) -> dict:
    """Argmax lean; ties resolve to Base case."""
    best = max(
        scenarios,
        key=lambda s: (s["likelihood"]["lean_score"], s["name"] == "Base case"),
    )
    call = (
        f"{category}: {best['name']} most probable for the {horizon} — "
        f"${best['premium_low']:,.0f}–${best['premium_high']:,.0f}. {tilt_label}."
    )
    return {
        "scenario": best["name"],
        "premium_low": best["premium_low"],
        "premium_high": best["premium_high"],
        "call": call,
    }


def _next_exercise_horizon(anchor: float, step: int, band: dict | None,
                           leans: dict, drivers: list[dict],
                           category: str, tilt_label: str,
                           notes: list[str]) -> dict:
    """Immediate round: ranges anchored on current premium, clamped to band."""
    bear_low, bear_high = anchor - 2 * step, anchor - step
    base_low, base_high = anchor - step / 2, anchor + step / 2
    bull_low, bull_high = anchor + step, anchor + 2 * step

    # Clamp to the curated band by SHIFTING the range to the band edge (keeping
    # its width), not truncating — truncating can invert low/high. Only clamp
    # when the band edge still brackets the current premium; if the premium has
    # already left the curated band, the band is stale and shouldn't cap us.
    if band and band.get("low") is not None and band["low"] <= anchor and bear_low < band["low"]:
        bear_low = band["low"]
        bear_high = band["low"] + step
        notes.append(
            f"Bearish range clamped up to the curated {band['quarter']} band "
            f"floor (${band['low']:,.0f})."
        )
    if band and band.get("high") is not None and band["high"] >= anchor and bull_high > band["high"]:
        bull_high = band["high"]
        bull_low = band["high"] - step
        notes.append(
            f"Bullish range clamped down to the curated {band['quarter']} band "
            f"ceiling (${band['high']:,.0f})."
        )

    scenarios = [
        _make_scenario("Bearish dip", bear_low, bear_high, anchor, leans, drivers),
        _make_scenario("Base case", base_low, base_high, anchor, leans, drivers),
        _make_scenario("Bullish spike", bull_low, bull_high, anchor, leans, drivers),
    ]
    return {
        "scenarios": scenarios,
        "most_probable": _pick_most_probable(
            scenarios, "next exercise", category, tilt_label),
    }


def _next_quarter_horizon(anchor: float, step: int, band: dict | None,
                          leans: dict, drivers: list[dict],
                          category: str, tilt_label: str,
                          notes: list[str]) -> dict | None:
    """Following quarter: ranges built around that quarter's curated band."""
    if band and band.get("low") is not None and band.get("high") is not None:
        bear_low, bear_high = band["low"] - step, band["low"]
        base_low, base_high = band["low"], band["high"]
        bull_low, bull_high = band["high"], band["high"] + step
        band_out = {
            "quarter": band["quarter"],
            "low": band["low"],
            "high": band["high"],
            "outlook": band["outlook"],
        }
    else:
        # No curated band ahead — widen the signal-derived ranges instead.
        notes.append("No curated band for the next quarter; ranges are "
                     "signal-derived only.")
        qstep = step * 2
        bear_low, bear_high = anchor - 2 * qstep, anchor - qstep
        base_low, base_high = anchor - qstep / 2, anchor + qstep / 2
        bull_low, bull_high = anchor + qstep, anchor + 2 * qstep
        band_out = None

    scenarios = [
        _make_scenario("Bearish dip", bear_low, bear_high, anchor, leans, drivers),
        _make_scenario("Base case", base_low, base_high, anchor, leans, drivers),
        _make_scenario("Bullish spike", bull_low, bull_high, anchor, leans, drivers),
    ]
    return {
        "band": band_out,
        "scenarios": scenarios,
        "most_probable": _pick_most_probable(
            scenarios, "next quarter", category, tilt_label),
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def _empty_result(category: str, reason: str) -> dict:
    """Schema-shaped placeholder when a category has nothing to project."""
    return {
        "category": category,
        "as_of_period": None,
        "premium_current": None,
        "next_exercise": {"scenarios": [], "most_probable": None},
        "next_quarter": None,
        "tilt": {"score": 0, "label": "—", "color": "#9aa0a6"},
        "drivers_summary": [],
        "data_quality": "insufficient",
        "notes": [reason],
    }


def project_outcomes(category: str = "Category A",
                     data: list[dict] | None = None,
                     today: datetime | None = None) -> dict:
    """Project possible outcomes of the next COE bidding for one category.

    `data` and `today` are injectable for testing; both default to live values.
    See the module docstring for the schema and the synthesis rules.
    """
    today = today or datetime.now()
    data = data if data is not None else _load_recent_premiums()
    stats = _compute_market_stats(data)
    if not stats:
        return _empty_result(category, "No premium history available.")

    suffix = _suffix(category)
    latest = stats["latest"]
    anchor = latest.get(f"cat{suffix.upper()}")
    if not anchor:
        return _empty_result(category, "Latest premium unavailable for this category.")

    rev = detect_reversal(category)

    # Data quality: snapshot if the pipeline has never refreshed coe_results.
    if _load_coe_freshness() is None:
        data_quality = "fallback_snapshot"
    else:
        data_quality = "live"

    notes: list[str] = []
    has_short_history = len(data) < 6
    if has_short_history:
        notes.append("Limited history (< 6 rounds) — momentum signal suppressed.")
    if data_quality == "fallback_snapshot":
        notes.append("Projection based on the bundled snapshot — run the "
                     "pipeline for live data.")

    tilt = _compute_tilt(rev, stats, category, has_short_history)
    leans = _lean_scores(tilt["score"])
    drivers = tilt["drivers"]
    step = max(100, _round100(anchor * STEP_PCT))

    this_q = quarter_band_for(today, offset=0)
    next_q = quarter_band_for(today, offset=1)

    next_exercise = _next_exercise_horizon(
        anchor, step, this_q, leans, drivers, category, tilt["label"], notes)
    next_quarter = _next_quarter_horizon(
        anchor, step, next_q, leans, drivers, category, tilt["label"], notes)

    return {
        "category": category,
        "as_of_period": latest.get("period"),
        "premium_current": int(anchor),
        "next_exercise": next_exercise,
        "next_quarter": next_quarter,
        "tilt": {"score": tilt["score"], "label": tilt["label"], "color": tilt["color"]},
        "drivers_summary": drivers,
        "data_quality": data_quality,
        "notes": notes,
    }


def project_all(today: datetime | None = None) -> dict:
    """Run the outcome projection for every tracked category."""
    return {cat: project_outcomes(cat, today=today)
            for cat in ["Category A", "Category B"]}


if __name__ == "__main__":
    from database import init_db
    init_db()

    for cat, result in project_all().items():
        print(f"\n{'=' * 64}")
        print(f"  {cat} — tilt {result['tilt']['score']:+d} "
              f"({result['tilt']['label']})  ·  data: {result['data_quality']}")
        print(f"{'=' * 64}")
        if result["premium_current"] is None:
            print(f"  {result['notes'][0] if result['notes'] else 'No data.'}")
            continue
        print(f"  As of {result['as_of_period']} · current ${result['premium_current']:,.0f}")

        for horizon_key, horizon in (("NEXT EXERCISE", result["next_exercise"]),
                                     ("NEXT QUARTER", result["next_quarter"])):
            if not horizon:
                continue
            print(f"\n  {horizon_key}:")
            for s in horizon["scenarios"]:
                lk = s["likelihood"]
                print(f"    {s['name']:<14} ${s['premium_low']:,.0f}–${s['premium_high']:,.0f} "
                      f"({s['delta_low']:+,} / {s['delta_high']:+,})  "
                      f"[{lk['band']} · lean {lk['lean_score']}]")
            mp = horizon["most_probable"]
            if mp:
                print(f"    -> {mp['call']}")

        if result["notes"]:
            print("\n  Notes:")
            for n in result["notes"]:
                print(f"    · {n}")
