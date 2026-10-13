"""COE Market Analysis — The Coming COE Dip Cycle.

A structural analysis of supply dynamics, policy shifts, and the
feast-famine rhythm that governs Singapore's COE market.

Published: March 2026. Revised: 13 October 2026 (outlook, strategy, EV incentive figures).
"""

import re
from datetime import datetime, timedelta

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from database import get_conn

# ─── Data ────────────────────────────────────────────────────────────────────

# Hardcoded snapshot used as a fallback when the SQLite cache is empty (e.g.
# fresh checkout, pipeline never run). Live data takes precedence — see
# `_load_recent_premiums` below — so this list does NOT need to be edited each
# bidding round.

CAT_AB_DATA = [
    {"period": "Mar 25 R1", "catA": 94502, "catB": 116890},
    {"period": "Apr 25 R1", "catA": 97724, "catB": 117899},
    {"period": "Apr 25 R2", "catA": 99500, "catB": 117003},
    {"period": "Jul 25 R1", "catA": 101102, "catB": 119600},
    {"period": "Jul 25 R2", "catA": 101102, "catB": 119101},
    {"period": "Oct 25 R1", "catA": 128105, "catB": 141000},
    {"period": "Oct 25 R2", "catA": 122000, "catB": 131889},
    {"period": "Dec 25 R2", "catA": 109501, "catB": 115102},
    {"period": "Jan 26 R1", "catA": 102009, "catB": 119100},
    {"period": "Jan 26 R2", "catA": 109501, "catB": 121634},
    {"period": "Feb 26 R1", "catA": 106320, "catB": 110890},
    {"period": "Mar 26 R1", "catA": 108220, "catB": 114002},
    {"period": "Mar 26 R2", "catA": 111890, "catB": 115568},
    {"period": "Apr 26 R1", "catA": 118000, "catB": 121000},
    {"period": "Apr 26 R2", "catA": 123010, "catB": 121001},
    {"period": "May 26 R1", "catA": 124790, "catB": 126236},
    {"period": "May 26 R2", "catA": 124229, "catB": 129501},
    {"period": "Jun 26 R1", "catA": 126009, "catB": 126989},
    {"period": "Jun 26 R2", "catA": 123847, "catB": 123502},
    {"period": "Jul 26 R1", "catA": 129000, "catB": 130889},
    {"period": "Jul 26 R2", "catA": 126000, "catB": 129890},
    {"period": "Aug 26 R1", "catA": 123890, "catB": 129910},
    {"period": "Aug 26 R2", "catA": 128501, "catB": 131001},
    {"period": "Sep 26 R1", "catA": 133009, "catB": 135001},
    {"period": "Sep 26 R2", "catA": 131890, "catB": 133000},
    {"period": "Oct 26 R1", "catA": 130001, "catB": 130100},
]

CYCLE_DATA = [
    {"year": "2013", "registrations": 95, "coeAvg": 75, "phase": "boom"},
    {"year": "2014", "registrations": 88, "coeAvg": 68, "phase": "boom"},
    {"year": "2015", "registrations": 82, "coeAvg": 62, "phase": "boom"},
    {"year": "2016", "registrations": 92, "coeAvg": 48, "phase": "boom"},
    {"year": "2017", "registrations": 85, "coeAvg": 52, "phase": "boom"},
    {"year": "2018", "registrations": 68, "coeAvg": 35, "phase": "famine"},
    {"year": "2019", "registrations": 62, "coeAvg": 32, "phase": "famine"},
    {"year": "2020", "registrations": 55, "coeAvg": 30, "phase": "famine"},
    {"year": "2021", "registrations": 58, "coeAvg": 52, "phase": "famine"},
    {"year": "2022", "registrations": 60, "coeAvg": 78, "phase": "famine"},
    {"year": "2023", "registrations": 65, "coeAvg": 95, "phase": "famine"},
    {"year": "2024", "registrations": 70, "coeAvg": 105, "phase": "transition"},
    {"year": "2025", "registrations": 78, "coeAvg": 118, "phase": "transition"},
    {"year": "2026E", "registrations": 88, "coeAvg": 105, "phase": "feast"},
    {"year": "2027E", "registrations": 95, "coeAvg": 90, "phase": "feast"},
    {"year": "2028E", "registrations": 80, "coeAvg": 95, "phase": "post"},
]

PHASE_COLORS = {
    "boom": "rgba(80, 200, 120, 0.6)",
    "famine": "rgba(225, 87, 89, 0.5)",
    "transition": "rgba(192, 132, 252, 0.5)",
    "feast": "rgba(74, 158, 255, 0.6)",
    "post": "rgba(192, 132, 252, 0.4)",
}

PHASE_LABELS = {
    "boom": "2013-17 Boom (high reg, low COE)",
    "famine": "2018-23 Famine (low supply, high COE)",
    "transition": "2024-25 Transition",
    "feast": "2026-27E Feast (deregistration wave)",
    "post": "2028E Post-feast",
}

FORCE_DATA = [
    {"name": "Deregistration Wave (2016-17 cars expiring)", "direction": "down", "magnitude": 85,
     "detail": "~20% more COE supply as 2016-17 boom vehicles hit 10-year mark"},
    {"name": "LTA 20,000 COE Injection (from Feb 2025)", "direction": "down", "magnitude": 60,
     "detail": "Progressive injection over several years, smoothing supply"},
    {"name": "Guaranteed Dereg Forward-Starting", "direction": "down", "magnitude": 40,
     "detail": "LTA bringing future peak COEs forward to ease current trough"},
    {"name": "PARF Rebate Cut (Budget 2026)", "direction": "up", "magnitude": 70,
     "detail": "Less incentive to scrap early -> fewer COEs recycled -> tighter future supply"},
    {"name": "Strong Demand (Wealthy Households)", "direction": "up", "magnitude": 75,
     "detail": "20% growth in households earning >\\$20K/month; robust buying power"},
    {"name": "EV / Chinese Brand Surge", "direction": "up", "magnitude": 55,
     "detail": "BYD, Zeekr, Xpeng intensifying competition; more bids per round"},
    {"name": "PHV Fleet Growth", "direction": "up", "magnitude": 45,
     "detail": "Private-hire fleets snap up COEs; some excess capacity risk (Shariot)"},
    {"name": "EEAI Sunset (Jan 2027)", "direction": "up", "magnitude": 40,
     "detail": "EV incentives fall from up to \\$30K (VES \\$22.5K + EEAI ≤\\$7.5K) in 2026 to "
               "\\$20K (VES only) in 2027 — a ~\\$10K cliff; pull-forward demand in Q4 2026"},
    {"name": "COE Category Merger Proposal (Oct 2026)", "direction": "up", "magnitude": 35,
     "detail": "LTA consultation on merging Cat A/B with a ±\\$15K OMV feebate. Not policy yet, "
               "but rule-change uncertainty can pull purchases forward"},
    {"name": "Potential Recession (Global)", "direction": "down", "magnitude": 55,
     "detail": "If US tariffs / slowdown spill over, buyer sentiment weakens"},
    {"name": "0% Vehicle Growth Rate (to Jan 2028)", "direction": "up", "magnitude": 65,
     "detail": "No net addition to vehicle population; pure replacement system"},
]

# Q2-Q3 2026 keep their original Mar 2026 forecast ranges so the miss stays
# visible; the note records the actual outcome. Q4 2026 onward were revised on
# 13 Oct 2026 after Cat A set records and quotas stayed flat.
OUTLOOK_REVISED = "13 Oct 2026"

QUARTERLY_OUTLOOK = [
    {"quarter": "Q2 2026 (Apr-Jun)", "range": "\\$105K - \\$115K", "outlook": "Missed — came in above band",
     "color": "#e15759",
     "note": "Mar 2026 forecast: sideways to slight up. Actual Cat A \\$118K-\\$126K across six "
             "rounds; Cat A closed above Cat B twice (22 Apr, 17 Jun)."},
    {"quarter": "Q3 2026 (Jul-Sep)", "range": "\\$95K - \\$108K", "outlook": "Missed — no dip, new records",
     "color": "#e15759",
     "note": "Mar 2026 forecast: moderate dip begins. Actual Cat A \\$123.9K-\\$133.0K, record "
             "\\$133,009 on 9 Sep. Aug-Oct quota rose only 0.2% QoQ, so the expected "
             "deregistration-driven supply rise has not shown up in quotas."},
    {"quarter": "Q4 2026 (Oct-Dec)", "range": "\\$120K - \\$135K", "outlook": "Elevated plateau",
     "color": "#f28e2b",
     "note": "Revised Oct 2026 (was \\$85K-\\$100K). Oct R1 Cat A \\$130,001 after two rounds "
             "of easing off the Sep peak. Watch the Nov-Jan quota (announced late Oct) — the dip thesis "
             "needs a visible quota increase. EEAI/VES step-down on 1 Jan may lift Dec EV bids."},
    {"quarter": "Q1 2027 (Jan-Mar)", "range": "\\$110K - \\$135K", "outlook": "Wide — policy-driven",
     "color": "#f28e2b",
     "note": "Revised Oct 2026 (was \\$88K-\\$105K). EEAI ends, VES EV rebate drops to \\$20K. "
             "Category-merger findings due H1 2027; uncertainty about feebate bands could "
             "either pull bids forward or freeze them. Low confidence."},
    {"quarter": "Q2-Q3 2027", "range": "\\$100K - \\$130K", "outlook": "Dip only if supply finally rises",
     "color": "#b07aa1",
     "note": "Revised Oct 2026 (was \\$90K-\\$110K). A move toward \\$100K needs quotas to "
             "actually expand from the 2016-17 deregistration echo. PARF cut reduces early "
             "scrapping and works against that. Low confidence."},
]

STRATEGY_ITEMS = [
    {"label": "Primary Window", "value": "Jul - Nov 2026 (did not open)",
     "detail": "The trigger was Cat A below \\$95K in Aug-Oct. Cat A instead ran \\$124K-\\$133K. "
               "The original window has effectively failed; the Nov-Jan quota is the next test."},
    {"label": "Aggressive Target", "value": "\\$80K Cat A",
     "detail": "Was a ~20% scenario in Mar 2026. Now ~\\$50K below market with no supply "
               "signal pointing there — treat as very unlikely in the next two quarters."},
    {"label": "Realistic Target", "value": "\\$88K - \\$95K Cat A (under review)",
     "detail": "Original Mar 2026 trough call. Needs a sustained quota increase to become "
               "live again; not supported by any round since March."},
    {"label": "EV Incentives", "value": "Up to \\$30K in 2026 → \\$20K in 2027",
     "detail": "2026: VES Band A rebate \\$22,500 + EEAI 45% of ARF capped at \\$7,500. "
               "2027: VES Band A \\$20,000 only (EEAI ends 31 Dec 2026). Max loss ~\\$10K."},
    {"label": "Risk of Waiting", "value": "~\\$10K incentive cliff on 1 Jan 2027",
     "detail": "Waiting into 2027 only pays if the COE you'd win falls by more than ~\\$10K "
               "(less if your EV doesn't get the full \\$7,500 EEAI). A possible Cat A/B merger "
               "with a ±\\$15K OMV feebate is a second, larger unknown — not yet policy."},
]

WHY_DIFFERENT = [
    {"title": "LTA Supply Smoothing",
     "desc": "Since Feb 2023, quota is calculated on a 4-quarter rolling average (not 2-quarter). "
             "This dampens the amplitude of the feast — supply rises more gradually, "
             "preventing a sharp COE crash."},
    {"title": "Forward-Starting COEs",
     "desc": "LTA is bringing forward guaranteed future deregistrations to smooth the current "
             "trough. This means some of the coming 'feast' supply has already been partially "
             "front-loaded, reducing the eventual surge."},
    {"title": "The 20,000 Injection",
     "desc": "From Feb 2025, LTA is progressively injecting ~20,000 additional COEs over several "
             "years. This extra supply is being drip-fed, not dumped — by design, to prevent "
             "market disruption."},
    {"title": "PARF Cut -> Slower Turnover",
     "desc": "The Budget 2026 PARF slash makes early deregistration financially irrational. "
             "More owners will hold cars to year 10 or renew — reducing the velocity of COE "
             "recycling in future cycles."},
]


# ─── Live data loaders ───────────────────────────────────────────────────────

# LTA's CSV uses "Mar-2026" but other formats (e.g. "2026-03") have been seen
# in the wild — try a few before giving up and using the raw value.
_MONTH_FORMATS = ("%b-%Y", "%Y-%m", "%B-%Y", "%Y-%m-%d")


def _format_period(month: str, bidding_no) -> str:
    """Render '2026-03' + '2' as 'Mar 26 R2'."""
    if month is None:
        return f"R{bidding_no}"
    for fmt in _MONTH_FORMATS:
        try:
            dt = datetime.strptime(str(month).strip(), fmt)
            return f"{dt.strftime('%b %y')} R{bidding_no}"
        except ValueError:
            continue
    return f"{month} R{bidding_no}"


def _parse_month(month) -> datetime:
    """Best-effort parse of an LTA month string. Returns datetime.min on failure."""
    if month is None:
        return datetime.min
    for fmt in _MONTH_FORMATS:
        try:
            return datetime.strptime(str(month).strip(), fmt)
        except ValueError:
            continue
    return datetime.min


@st.cache_data(ttl=3600)
def _load_recent_premiums(rounds: int = 14) -> list[dict]:
    """Pull the last `rounds` bidding exercises with both Cat A and Cat B set.

    Falls back to the hardcoded CAT_AB_DATA snapshot if the table is missing
    or empty — keeps the dashboard usable on a fresh checkout.

    Sorting happens in Python because LTA uses a non-ISO month format
    ("Mar-2026") that doesn't sort lexicographically.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT month, bidding_no,
                       MAX(CASE WHEN vehicle_class LIKE '%Category A%'
                                THEN premium END) AS catA,
                       MAX(CASE WHEN vehicle_class LIKE '%Category B%'
                                THEN premium END) AS catB
                FROM coe_results
                WHERE vehicle_class LIKE '%Category A%'
                   OR vehicle_class LIKE '%Category B%'
                GROUP BY month, bidding_no
                HAVING catA IS NOT NULL AND catB IS NOT NULL
                """
            ).fetchall()
    except Exception:
        rows = []

    if not rows:
        return list(CAT_AB_DATA)

    rows = sorted(rows, key=lambda r: (_parse_month(r["month"]), str(r["bidding_no"])))
    rows = rows[-rounds:]

    return [
        {
            "period": _format_period(r["month"], r["bidding_no"]),
            "catA": r["catA"],
            "catB": r["catB"],
        }
        for r in rows
    ]


def _compute_market_stats(data: list[dict]) -> dict:
    """Derive every fact the prose anchors against from the premium history.

    Returns a dict with: latest, prior, peak_a/_b/_period (within window),
    correction_pct_a/_b (peak -> latest), current_gap, min_gap/_period,
    consecutive_rises_a/_b. All values are None when data is too short.
    """
    if not data:
        return {}

    latest = data[-1]
    prior = data[-2] if len(data) >= 2 else None

    peak_a = max(data, key=lambda r: r["catA"])
    peak_b = max(data, key=lambda r: r["catB"])

    def _correction(peak_val, curr_val):
        if peak_val <= 0:
            return 0.0
        return (peak_val - curr_val) / peak_val * 100

    gaps = [(r["period"], r["catB"] - r["catA"]) for r in data]
    min_gap_period, min_gap = min(gaps, key=lambda t: t[1])
    current_gap = latest["catB"] - latest["catA"]

    def _consecutive_rises(key: str) -> int:
        n = 0
        for i in range(len(data) - 1, 0, -1):
            if data[i][key] > data[i - 1][key]:
                n += 1
            else:
                break
        return n

    return {
        "latest": latest,
        "prior": prior,
        "peak_a": peak_a["catA"],
        "peak_b": peak_b["catB"],
        "peak_a_period": peak_a["period"],
        "peak_b_period": peak_b["period"],
        "correction_pct_a": _correction(peak_a["catA"], latest["catA"]),
        "correction_pct_b": _correction(peak_b["catB"], latest["catB"]),
        "current_gap": current_gap,
        "min_gap": min_gap,
        "min_gap_period": min_gap_period,
        "consecutive_rises_a": _consecutive_rises("catA"),
        "consecutive_rises_b": _consecutive_rises("catB"),
    }


@st.cache_data(ttl=3600)
def _load_latest_quota(months_back: int = 3) -> dict | None:
    """Sum quota across the latest N distinct months for Cat A and Cat B.

    Returns {"period": "Feb-Apr 26", "total": 18824, "delta": -160} or None.
    Delta compares to the previous N-month window when available.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT month, vehicle_class, SUM(quota) AS q
                FROM coe_results
                WHERE vehicle_class LIKE '%Category A%'
                   OR vehicle_class LIKE '%Category B%'
                GROUP BY month, vehicle_class
                """
            ).fetchall()
    except Exception:
        return None

    if not rows:
        return None

    # Aggregate to month -> total quota across A+B.
    by_month: dict[str, float] = {}
    for r in rows:
        if r["q"] is not None:
            by_month[r["month"]] = by_month.get(r["month"], 0) + r["q"]

    months = sorted(by_month.keys(), key=_parse_month)
    if len(months) < months_back:
        return None

    recent = months[-months_back:]
    total = sum(by_month[m] for m in recent)

    if len(months) >= 2 * months_back:
        prev = months[-2 * months_back:-months_back]
        prev_total = sum(by_month[m] for m in prev)
        delta = int(total - prev_total)
    else:
        delta = None

    def _short(m):
        dt = _parse_month(m)
        return dt.strftime("%b") if dt != datetime.min else m

    period = f"{_short(recent[0])}-{_short(recent[-1])} {_parse_month(recent[-1]).strftime('%y')}"

    return {"period": period, "total": int(total), "delta": delta}


def _pqp_proxy_3mo(data: list[dict], category: str = "catA") -> dict | None:
    """3-bidding-round trailing average — proxy for LTA's PQP (3-month MA)."""
    if len(data) < 6:
        return None
    recent = data[-3:]
    prior = data[-6:-3]
    recent_avg = sum(d[category] for d in recent) / 3
    prior_avg = sum(d[category] for d in prior) / 3
    return {
        "recent": recent_avg,
        "prior": prior_avg,
        "delta": recent_avg - prior_avg,
        "recent_period": data[-1]["period"],
        "prior_period": data[-4]["period"],
    }


@st.cache_data(ttl=3600)
def _load_coe_freshness() -> str | None:
    """ISO timestamp of the last successful coe_results refresh, or None."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT last_updated FROM data_refresh_log WHERE source = ?",
                ("coe_results",),
            ).fetchone()
        return row["last_updated"] if row else None
    except Exception:
        return None


# ─── Shared synthesis helpers ─────────────────────────────────────────────────
#
# These are pure (no Streamlit) so the Bid Outlook engine (models/coe_outcomes)
# can reuse the exact same force balance and quarterly-band logic the render
# functions use — one source of truth.

def force_net() -> dict:
    """Net structural force pressure from FORCE_DATA.

    Sums force magnitudes by direction and returns the totals plus a signed
    net (up − down) and a coarse lean. Shared by the Market Forces tab and the
    outcome engine so both report the same numbers.
    """
    down_total = sum(f["magnitude"] for f in FORCE_DATA if f["direction"] == "down")
    up_total = sum(f["magnitude"] for f in FORCE_DATA if f["direction"] == "up")
    net = up_total - down_total
    if net > 50:
        lean = "up"
    elif net < -50:
        lean = "down"
    else:
        lean = "balanced"
    return {"up_total": up_total, "down_total": down_total, "net": net, "lean": lean}


# Map a quarter number to its (first month, last month).
_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}


def _parse_band(range_str: str) -> tuple[int, int] | None:
    """Parse a QUARTERLY_OUTLOOK range string into (low, high) dollar ints.

    e.g. '\\$105K - \\$115K' -> (105000, 115000). Returns None if it can't
    find two K-suffixed numbers (defensive against format changes).
    """
    if not range_str:
        return None
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*[Kk]", range_str)
    if len(nums) < 2:
        return None
    return int(float(nums[0]) * 1000), int(float(nums[1]) * 1000)


def _band_date_span(quarter_label: str) -> tuple[datetime, datetime] | None:
    """Derive (start, end) datetimes from a quarter label.

    Handles 'Q3 2026 (Jul-Sep)' and range labels like 'Q2-Q3 2027'.
    """
    quarters = [int(q) for q in re.findall(r"Q(\d)", quarter_label)]
    years = [int(y) for y in re.findall(r"(20\d{2})", quarter_label)]
    if not quarters or not years:
        return None
    year = years[0]
    start_month = _QUARTER_MONTHS[quarters[0]][0]
    end_month = _QUARTER_MONTHS[quarters[-1]][1]
    start = datetime(year, start_month, 1)
    if end_month == 12:
        end = datetime(year, 12, 31)
    else:
        end = datetime(year, end_month + 1, 1) - timedelta(days=1)
    return start, end


def _band_index_for(today: datetime) -> int | None:
    """Index of the QUARTERLY_OUTLOOK entry whose span contains `today`."""
    for i, item in enumerate(QUARTERLY_OUTLOOK):
        span = _band_date_span(item["quarter"])
        if span and span[0] <= today <= span[1]:
            return i
    return None


def quarter_band_for(today: datetime | None = None, offset: int = 0) -> dict | None:
    """The curated outlook band for `today`'s quarter, or `offset` quarters on.

    offset=0 → the quarter containing today; offset=1 → the next listed quarter.
    Returns {quarter, low, high, outlook, note} with low/high parsed from the
    range string (None if the range couldn't be parsed), or None if there's no
    matching entry (e.g. today is past QUARTERLY_OUTLOOK's coverage).
    """
    today = today or datetime.now()
    idx = _band_index_for(today)
    if idx is None:
        return None
    j = idx + offset
    if not (0 <= j < len(QUARTERLY_OUTLOOK)):
        return None
    item = QUARTERLY_OUTLOOK[j]
    parsed = _parse_band(item["range"])
    return {
        "quarter": item["quarter"],
        "low": parsed[0] if parsed else None,
        "high": parsed[1] if parsed else None,
        "outlook": item["outlook"],
        "note": item["note"],
    }


# ─── Thesis audit ────────────────────────────────────────────────────────────

# When the analyst-written prose was authored. Surface this date so readers
# know the structural narrative is a snapshot, not a live document.
# Originally authored Mar 2026; revised 13 Oct 2026 after Cat A set records
# instead of dipping (see QUARTERLY_OUTLOOK notes for the original calls).
THESIS_DATE = datetime(2026, 10, 13)

# Each anchor encodes one numeric/temporal claim from the prose. The audit
# function checks each against current data and tags it OK / WATCH / STALE so
# we know when to revisit the narrative.
THESIS_ANCHORS: list[dict] = [
    {
        "claim": "Cat A 'currently around $130K'",
        "tab": "Big Picture",
        "kind": "price_band",
        "anchor": 130000,
        "tolerance_pct": 8,
    },
    {
        "claim": "Revised: possible ease toward $100K–$120K by Q3 2027",
        "tab": "Big Picture / Forces",
        "kind": "trough",
        "low": 100000,
        "high": 120000,
        "trough_by": datetime(2027, 9, 30),
    },
    {
        "claim": "Reference peak: Cat A $133,009 (9 Sep 2026 record)",
        "tab": "Trajectory",
        "kind": "peak_reference",
        "peak_value": 133009,
        "peak_period_match": "Sep 26",
    },
    {
        "claim": "Cat A–B gap near zero (Cat A above B twice in Q2 2026)",
        "tab": "Trajectory",
        "kind": "gap_band",
        "anchor": 1000,
        "tolerance_pct": 200,
    },
    {
        "claim": "Original buying window: Oct–Nov 2026 (conditional on a dip)",
        "tab": "Buying Window",
        "kind": "date_window",
        "start": datetime(2026, 10, 1),
        "end": datetime(2026, 11, 30),
    },
    {
        "claim": "EEAI rebate sunsets Jan 2027",
        "tab": "Buying Window",
        "kind": "date_deadline",
        "deadline": datetime(2027, 1, 1),
    },
    {
        "claim": "Budget 2026 PARF cuts framed as 'recent'",
        "tab": "Forces",
        "kind": "policy_recency",
        "policy_date": datetime(2026, 2, 1),
        "stale_after_months": 12,
    },
]


def _check_anchor(anchor: dict, stats: dict, today: datetime) -> tuple[str, str]:
    """Return (status, explanation). Status ∈ {OK, WATCH, STALE, UNKNOWN}."""
    kind = anchor["kind"]
    latest = stats.get("latest")

    if kind == "price_band":
        if not latest:
            return ("UNKNOWN", "no premium data available")
        val = latest["catA"]
        drift = abs(val - anchor["anchor"]) / anchor["anchor"] * 100
        if drift <= anchor["tolerance_pct"]:
            return ("OK",
                    f"Latest Cat A ${val:,.0f} within {drift:.0f}% of "
                    f"${anchor['anchor']:,.0f} anchor.")
        if drift <= anchor["tolerance_pct"] * 2:
            return ("WATCH",
                    f"Cat A ${val:,.0f} has drifted {drift:.0f}% from the "
                    f"${anchor['anchor']:,.0f} anchor — phrasing starting to age.")
        return ("STALE",
                f"Cat A ${val:,.0f} is {drift:.0f}% off the "
                f"${anchor['anchor']:,.0f} anchor — 'current range' phrasing no "
                f"longer fits.")

    if kind == "trough":
        if not latest:
            return ("UNKNOWN", "no premium data available")
        val = latest["catA"]
        if val < anchor["low"]:
            return ("STALE",
                    f"Cat A already at ${val:,.0f}, below the forecast trough "
                    f"floor of ${anchor['low']:,.0f}. Forecast may have been "
                    f"overshot.")
        if val > anchor["high"] * 1.4:
            return ("WATCH",
                    f"Cat A ${val:,.0f} is well above the forecast trough range. "
                    f"Either the trough hasn't started or the forecast was too low.")
        if today > anchor["trough_by"]:
            return ("STALE",
                    f"Forecast trough date ({anchor['trough_by']:%b %Y}) has "
                    f"passed; Cat A still at ${val:,.0f}.")
        return ("OK",
                f"Cat A ${val:,.0f} consistent with a not-yet-arrived trough at "
                f"${anchor['low']:,.0f}–${anchor['high']:,.0f}.")

    if kind == "peak_reference":
        peak_now = stats.get("peak_a") or 0
        peak_period = stats.get("peak_a_period", "—")
        # Anchor stays valid as long as the current peak still falls within
        # the referenced period (small numeric drift from rounding is fine).
        period_match = anchor.get("peak_period_match", "")
        if period_match and period_match in peak_period:
            return ("OK",
                    f"${peak_now:,.0f} ({peak_period}) remains the window peak.")
        if peak_now > anchor["peak_value"] * 1.02:
            return ("STALE",
                    f"A newer round (${peak_now:,.0f} on {peak_period}) has "
                    f"exceeded the ${anchor['peak_value']:,.0f} reference peak. "
                    f"The 'Oct 2025 spike' anchor is no longer the high water mark.")
        return ("OK",
                f"${anchor['peak_value']:,.0f} remains the window peak.")

    if kind == "gap_band":
        gap = stats.get("current_gap")
        if gap is None:
            return ("UNKNOWN", "no premium data available")
        drift = abs(gap - anchor["anchor"]) / anchor["anchor"] * 100
        if drift <= anchor["tolerance_pct"]:
            return ("OK",
                    f"Current gap ${gap:,.0f} within {drift:.0f}% of "
                    f"${anchor['anchor']:,.0f} anchor.")
        if drift <= anchor["tolerance_pct"] * 2:
            return ("WATCH",
                    f"Current gap ${gap:,.0f} drifted {drift:.0f}% from anchor.")
        return ("STALE",
                f"Current gap ${gap:,.0f} no longer matches the "
                f"${anchor['anchor']:,.0f} anchor.")

    if kind == "date_window":
        if today < anchor["start"]:
            days = (anchor["start"] - today).days
            return ("OK",
                    f"Window opens in {days} days "
                    f"({anchor['start']:%b %Y}).")
        if anchor["start"] <= today <= anchor["end"]:
            return ("WATCH",
                    f"Currently inside the buying window "
                    f"({anchor['start']:%b}–{anchor['end']:%b %Y}). "
                    f"Verify the trough thesis still holds.")
        days_past = (today - anchor["end"]).days
        return ("STALE",
                f"Window closed {days_past} days ago — was the trough hit? "
                f"Strategy section needs a post-mortem.")

    if kind == "date_deadline":
        if today < anchor["deadline"]:
            days = (anchor["deadline"] - today).days
            return ("OK",
                    f"{days} days until {anchor['deadline']:%b %Y} deadline.")
        return ("STALE",
                f"Deadline ({anchor['deadline']:%b %Y}) has passed.")

    if kind == "policy_recency":
        months_old = ((today.year - anchor["policy_date"].year) * 12
                      + (today.month - anchor["policy_date"].month))
        if months_old <= anchor["stale_after_months"]:
            return ("OK",
                    f"{months_old} months since policy enacted — still recent.")
        return ("WATCH",
                f"{months_old} months since policy — 'recent' framing aging.")

    return ("UNKNOWN", "unknown anchor kind")


def _audit_thesis(stats: dict, today: datetime | None = None) -> list[tuple[dict, str, str]]:
    today = today or datetime.now()
    return [(a, *_check_anchor(a, stats, today)) for a in THESIS_ANCHORS]


# ─── Render Functions ────────────────────────────────────────────────────────

def _render_overview():
    st.caption(
        "Where Cat A and Cat B are now, and the analyst's call on where they're heading."
    )
    st.markdown(
        "The March 2026 thesis was that the 10-year deregistration wave from the 2016-2017 "
        "registration boom would produce a moderated dip through H2 2026. **As of Oct 2026 "
        "that dip has not happened.** Cat A set a record \\$133,009 on 9 Sep, Cat A and B "
        "have converged to within \\$99, and the Aug-Oct quota rose only 0.2% — the supply "
        "expansion is not yet visible in quotas. Demand (affluent buyers, the Q4 EV-incentive "
        "rush, PARF-driven holding) has outrun supply smoothing. LTA's 8 Oct consultation on "
        "merging Cat A and B adds a policy unknown on top."
    )
    st.caption(f"Narrative and outlook revised {OUTLOOK_REVISED}; originally published Mar 2026.")
    st.markdown("")

    data = _load_recent_premiums()
    stats = _compute_market_stats(data)
    latest = stats.get("latest")

    # Round latest Cat A to nearest $5K to feel like a "range" anchor.
    if latest:
        anchor_k = round(latest["catA"] / 5000) * 5000 // 1000
        outlook_line = (
            f"**Revised outlook (low confidence):** Cat A holds around the current "
            f"~\\${anchor_k}K range through Q4 2026. Any meaningful ease toward "
            f"\\$100K-\\$120K needs quotas to actually rise and is unlikely before "
            f"mid-2027. The old \\$85K-\\$95K trough call is not supported by any round "
            f"since March."
        )
    else:
        outlook_line = (
            "**Revised outlook (low confidence):** Cat A holds near recent highs through "
            "Q4 2026; an ease toward \\$100K-\\$120K needs quotas to rise and is unlikely "
            "before mid-2027."
        )
    st.markdown(outlook_line)

    st.markdown("")
    m1, m2, m3, m4 = st.columns(4)

    prior = stats.get("prior")

    def _delta(curr, prev):
        if curr is None or prev is None:
            return None
        diff = curr - prev
        sign = "+" if diff >= 0 else "−"
        return f"{sign}${abs(diff):,.0f} from prev round"

    if latest:
        m1.metric(
            f"Cat A ({latest['period']})",
            f"${latest['catA']:,.0f}",
            delta=_delta(latest["catA"], prior["catA"] if prior else None),
            delta_color="inverse",
        )
        m2.metric(
            f"Cat B ({latest['period']})",
            f"${latest['catB']:,.0f}",
            delta=_delta(latest["catB"], prior["catB"] if prior else None),
            delta_color="inverse",
        )
    else:
        m1.metric("Cat A", "—")
        m2.metric("Cat B", "—")

    quota = _load_latest_quota()
    if quota:
        delta_label = (
            f"{quota['delta']:+,} from prev qtr" if quota["delta"] is not None else None
        )
        m3.metric(f"{quota['period']} Quota", f"{quota['total']:,}", delta=delta_label)
    else:
        m3.metric("Quota", "—")

    # PQP not yet sourced from LTA — show a 3-round trailing avg as a proxy.
    pqp = _pqp_proxy_3mo(data, "catA")
    if pqp:
        delta = f"{'+' if pqp['delta'] >= 0 else '−'}${abs(pqp['delta']):,.0f}"
        m4.metric(
            f"Cat A 3-round avg (proxy PQP)",
            f"${pqp['recent']:,.0f}",
            delta=f"{delta} vs prior 3 rounds",
            delta_color="inverse",
        )
    else:
        m4.metric("Cat A 3-round avg (proxy PQP)", "—")


def _render_trajectory():
    st.caption(
        "Round-by-round premiums since the last record peak, and what the 3-round "
        "trailing average says about direction."
    )
    data = _load_recent_premiums()
    stats = _compute_market_stats(data)

    if stats:
        # Peak narrative — only describe a "spike" if both peaks aren't the
        # latest round (which would mean we're at the peak, not past it).
        peak_a = stats["peak_a"]
        peak_b = stats["peak_b"]
        peak_period_a = stats["peak_a_period"]
        corr_a = stats["correction_pct_a"]
        corr_b = stats["correction_pct_b"]
        rises_a = stats["consecutive_rises_a"]

        if corr_a > 1 or corr_b > 1:
            spike_line = (
                f"The recent peak was **{peak_period_a}** (Cat A hit \\${peak_a:,.0f}, "
                f"Cat B hit \\${peak_b:,.0f}). Since then, premiums have moved "
                f"{corr_a:+.1f}% on Cat A and {corr_b:+.1f}% on Cat B."
            )
        else:
            spike_line = (
                f"Cat A and Cat B are at or near their window peak "
                f"(\\${peak_a:,.0f} / \\${peak_b:,.0f}, {peak_period_a}) — "
                f"no meaningful correction yet."
            )

        if rises_a >= 2:
            trend_line = (
                f" The recent direction has been upward — Cat A has risen across "
                f"**{rises_a} consecutive exercise{'s' if rises_a != 1 else ''}**."
            )
        else:
            trend_line = ""

        st.markdown(spike_line + trend_line)
    else:
        st.markdown("Premium history unavailable.")

    st.markdown("")

    if stats:
        gap_line = (
            f"The Cat A-Cat B gap narrowed to as little as **\\${stats['min_gap']:,.0f}** "
            f"in {stats['min_gap_period']}, making Cat B a near-no-brainer upgrade in that "
            f"window. That gap is now **\\${stats['current_gap']:,.0f}**."
        )
        st.markdown(gap_line)

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["catA"], name="Cat A (<1600cc)",
        line=dict(color="#4e79a7", width=2.5), mode="lines+markers",
        marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["catB"], name="Cat B (>1600cc)",
        line=dict(color="#e15759", width=2.5), mode="lines+markers",
        marker=dict(size=6),
    ))
    fig.add_hline(y=100000, line_dash="dot", line_color="rgba(242,142,43,0.4)",
                  annotation_text="$100K", annotation_position="left")
    fig.update_layout(
        template="streamlit", height=400,
        yaxis_title="COE Premium ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        margin=dict(t=20, b=60, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Key Observation: Where the post-peak floor is forming**")

    # Compute "post-peak" range from rounds AFTER the Cat A peak.
    if stats and len(data) >= 3:
        peak_idx = max(range(len(data)), key=lambda i: data[i]["catA"])
        post_peak = data[peak_idx + 1 :]
        if post_peak:
            lo = min(r["catA"] for r in post_peak)
            hi = max(r["catA"] for r in post_peak)
            st.markdown(
                f"After the **{stats['peak_a_period']}** Cat A peak "
                f"(\\${stats['peak_a']:,.0f}), subsequent rounds have ranged "
                f"\\${lo:,.0f}–\\${hi:,.0f}. If this floor holds higher than the "
                f"prior cycle's, we're seeing the plateau pattern — each correction "
                f"lands at a higher base than the previous one."
            )
        else:
            st.markdown(
                f"Cat A is currently at its window peak (\\${stats['peak_a']:,.0f}) — "
                f"the post-peak floor hasn't formed yet."
            )
    st.markdown("")

    # PQP block — using a 3-round trailing avg as a proxy until LTA's actual
    # PQP feed is wired into SQLite.
    pqp = _pqp_proxy_3mo(data, "catA")
    if pqp:
        direction = "declined" if pqp["delta"] < 0 else "risen"
        st.markdown(
            f"The 3-round trailing average for Cat A (a proxy for LTA's "
            f"3-month PQP) has **{direction}** from \\${pqp['prior']:,.0f} in the "
            f"previous 3-round window to \\${pqp['recent']:,.0f} now — "
            f"a {'positive' if pqp['delta'] < 0 else 'cautionary'} signal for "
            f"prospective buyers."
        )

        pq1, pq2 = st.columns(2)
        pq1.metric(f"3-round avg (prior window)", f"${pqp['prior']:,.0f}")
        pq2.metric(
            f"3-round avg (current window)",
            f"${pqp['recent']:,.0f}",
            delta=f"{'+' if pqp['delta'] >= 0 else '−'}${abs(pqp['delta']):,.0f}",
            delta_color="inverse",
        )
        st.caption(
            "Proxy for LTA's PQP (Prevailing Quota Premium), which is the official "
            "3-month moving average — wired here from `coe_results` until the "
            "official PQP feed is added."
        )


def _render_cycle():
    st.caption(
        "Why supply swings every decade — boom → famine → feast — and why this "
        "cycle won't replay the last one cleanly."
    )
    st.markdown(
        "The COE system creates an inherent ~10-year cycle. When many cars are registered in a "
        "boom period, those COEs expire a decade later, flooding supply and depressing prices — "
        "the \"feast.\" When few cars were registered (because COEs were expensive), fewer expire "
        "later, creating scarcity — the \"famine.\""
    )
    st.markdown("")
    st.markdown(
        "We're currently transitioning from famine to feast. The 2016-2017 registration boom "
        "(fuelled by low COE prices of \\$40K-\\$55K for Cat A) means a large wave of "
        "deregistrations from 2026 onward. LTA projects about 20% more car COE supply as "
        "these vehicles reach their 10-year mark."
    )

    # Build chart with phase-colored bars
    fig = go.Figure()
    for phase, color in PHASE_COLORS.items():
        phase_data = [d for d in CYCLE_DATA if d["phase"] == phase]
        if phase_data:
            fig.add_trace(go.Bar(
                x=[d["year"] for d in phase_data],
                y=[d["registrations"] for d in phase_data],
                name=PHASE_LABELS.get(phase, phase),
                marker_color=color,
                yaxis="y",
            ))

    fig.add_trace(go.Scatter(
        x=[d["year"] for d in CYCLE_DATA],
        y=[d["coeAvg"] for d in CYCLE_DATA],
        name="Avg Cat A COE ($K)",
        line=dict(color="#f28e2b", width=2.5),
        marker=dict(size=5),
        yaxis="y2",
    ))

    fig.update_layout(
        template="streamlit", height=420,
        yaxis=dict(title="New Registrations (K)"),
        yaxis2=dict(title="Avg COE Premium ($K)", overlaying="y", side="right"),
        barmode="stack",
        hovermode="x unified",
        margin=dict(t=20, b=40, l=60, r=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Why this cycle is different
    st.markdown("**Why This Cycle Is Different**")
    st.markdown("")
    c1, c2 = st.columns(2)
    for i, item in enumerate(WHY_DIFFERENT):
        col = c1 if i % 2 == 0 else c2
        with col:
            st.markdown(f"**{item['title']}**")
            st.caption(item["desc"])
            st.markdown("")


def _render_forces():
    st.caption(
        "Tug-of-war between forces pushing premiums down (more supply, recession risk) "
        "and forces pushing them up (demand, policy)."
    )
    st.markdown(
        "The dip cycle isn't a single narrative. It's a tug of war between structural supply "
        "tailwinds and persistent demand headwinds."
    )
    st.markdown("")

    for force in FORCE_DATA:
        is_down = force["direction"] == "down"
        arrow = "&#x25BC;" if is_down else "&#x25B2;"
        color = "#59a14f" if is_down else "#e15759"

        col_arrow, col_text, col_bar = st.columns([0.5, 5, 2])
        with col_arrow:
            st.markdown(
                f'<span style="color:{color}; font-size:1.2rem">{arrow}</span>',
                unsafe_allow_html=True,
            )
        with col_text:
            st.markdown(f"**{force['name']}**")
            st.caption(force["detail"])
        with col_bar:
            st.markdown(
                f'<div style="background:var(--secondary-background-color); '
                f'border-radius:4px; height:12px; margin-top:8px">'
                f'<div style="background:{color}; width:{force["magnitude"]}%; '
                f'height:100%; border-radius:4px"></div></div>'
                f'<div style="font-size:0.75rem; text-align:right; '
                f'color:var(--text-color); opacity:0.6; margin-top:2px">'
                f'Impact: {force["magnitude"]}%</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.markdown("**Net Assessment**")
    st.markdown("")

    net = force_net()
    down_total = net["down_total"]
    up_total = net["up_total"]

    na1, na2 = st.columns(2)
    na1.metric("Downward Pressure", str(down_total),
               delta="Supply relief + macro risk")
    na2.metric("Upward Pressure", str(up_total),
               delta="Demand + policy headwinds", delta_color="inverse")

    st.markdown("")
    st.info(
        "Upward forces currently outweigh downward ones, and 2026 data confirms it: instead "
        "of a moderate dip to \\$85K-\\$95K, Cat A climbed to a \\$133K record. The supply-side "
        "forces are real but have not reached quotas yet. Until they do, expect Cat A to "
        "stay in the \\$120K-\\$135K band."
    )


def _render_buying_window():
    st.caption(
        "Quarter-by-quarter projection plus a tactical strategy for prospective buyers, "
        "anchored around the EEAI Jan 2027 deadline."
    )
    st.markdown(
        "Based on the supply cycle, PARF dynamics, EEAI sunset, and demand signals, "
        "here's a quarter-by-quarter projection. Elapsed quarters keep their original "
        "Mar 2026 ranges with the actual outcome noted; later quarters were revised "
        f"{OUTLOOK_REVISED}."
    )
    st.markdown("")

    for item in QUARTERLY_OUTLOOK:
        col_bar, col_text = st.columns([0.3, 6])
        with col_bar:
            st.markdown(
                f'<div style="width:4px; height:60px; border-radius:4px; '
                f'background:{item["color"]}; margin-top:4px"></div>',
                unsafe_allow_html=True,
            )
        with col_text:
            st.markdown(f"**{item['quarter']}** — `{item['range']}`")
            st.markdown(f"*{item['outlook']}*")
            st.caption(item["note"])
        st.markdown("")

    # Strategy section
    st.markdown("---")
    st.markdown("**Strategy: Cat A — Tesla Model Y RWD**")
    st.markdown("")
    st.markdown(
        "Given a target of Cat A COE ~\\$80K and annual depreciation of ~\\$15K over 10 years, "
        "here's the tactical picture:"
    )
    st.markdown("")

    for item in STRATEGY_ITEMS:
        s1, s2 = st.columns([1, 3])
        with s1:
            st.markdown(f"**{item['label']}**")
        with s2:
            st.markdown(f"**{item['value']}**")
            st.caption(item["detail"])

    # Critical insight
    st.markdown("")
    st.warning(
        "**The Critical Insight (corrected Oct 2026):** The earlier version said waiting cost a "
        "\\$30K EEAI rebate. That was wrong — EEAI is capped at \\$7,500 in 2026; the \\$30K was "
        "the *combined* EV incentive. The real 1 Jan 2027 cliff is ~\\$10K (EEAI \\$7.5K + VES "
        "rebate stepping from \\$22.5K to \\$20K). So waiting into 2027 pays if the COE you'd "
        "win falls by more than ~\\$10K. With Cat A at ~\\$130K and no quota increase yet, "
        "neither outcome is clear — the Nov-Jan quota (late Oct) and the category-merger "
        "findings (H1 2027) are the two things to watch before committing."
    )


# ─── Bid Outlook (qualitative + quantitative synthesis) ───────────────────────

def _render_scenario_card(scenario: dict) -> None:
    """One scenario column: range, delta vs current, band + lean, driver list."""
    lk = scenario["likelihood"]
    st.markdown(f"**{scenario['name']}**")
    st.markdown(
        f"\\${scenario['premium_low']:,.0f} – \\${scenario['premium_high']:,.0f}"
    )
    st.caption(
        f"vs current: {scenario['delta_low']:+,} to {scenario['delta_high']:+,}"
    )
    st.markdown(
        f'<span style="background:{lk["color"]}; color:white; padding:2px 10px; '
        f'border-radius:12px; font-size:0.8rem">{lk["band"]}</span> '
        f'<span style="opacity:0.6; font-size:0.85rem">· lean {lk["lean_score"]}</span>',
        unsafe_allow_html=True,
    )
    with st.expander("Why", expanded=False):
        if not scenario["drivers"]:
            st.caption("No directional signal — default base expectation.")
        for d in scenario["drivers"]:
            arrow = ("&#x25B2;" if d["direction"] == "up"
                     else "&#x25BC;" if d["direction"] == "down" else "&#x25C6;")
            st.caption(f"{arrow} **{d['source']}** ({d['weight']:+d}) — {d['detail']}")


def _render_bid_outlook() -> None:
    """Synthesis tab: fuse every signal into possible outcomes per category."""
    from models.coe_outcomes import (
        project_all, TILT_RULES, LEAN_BANDS, STEP_PCT,
    )

    st.caption(
        "One deterministic view that fuses the technical reversal signals, price "
        "momentum, the structural force balance, the policy radar, and the curated "
        "quarterly bands into possible outcomes — for the next bidding exercise and "
        "the next quarter, per category."
    )

    with st.expander("How these outcomes are derived (methodology)", expanded=False):
        st.markdown(
            "**Tilt score** — a signed directional lean. Each signal adds a documented "
            "amount; negative = premiums expected to ease, positive = premiums expected "
            "to firm:"
        )
        st.dataframe(
            [{"Signal": s, "Contribution to tilt": rule} for s, rule in TILT_RULES],
            use_container_width=True, hide_index=True,
        )
        st.markdown(
            f"**Scenario ranges** anchor on the current premium; one scenario step is "
            f"{STEP_PCT:.0%} of it (the typical round-to-round swing). Immediate-round "
            f"ranges are clamped to the curated quarterly band so the engine never "
            f"contradicts the published outlook; next-quarter ranges are built around "
            f"that quarter's curated band."
        )
        st.markdown(
            "**Likelihood** is an ordinal *lean score*, not a probability. The base case "
            "starts highest (markets mean-revert most rounds); the tilt then shifts "
            "weight toward the aligned scenario. Bands:"
        )
        for threshold, label, _ in LEAN_BANDS:
            st.markdown(f"- **{label}** (lean ≥ {threshold})")
        st.caption(
            "Lean scores are ordinal weights from the rule above, shown next to the "
            "band — they are deliberately NOT calibrated probabilities."
        )

    outlook = project_all()

    for category, result in outlook.items():
        st.markdown("---")
        st.markdown(f"### {category}")

        if result["data_quality"] == "insufficient":
            st.info(result["notes"][0] if result["notes"] else "No data available.")
            continue

        if result["data_quality"] == "fallback_snapshot":
            st.caption(
                "Based on the bundled snapshot — click **Refresh Data** at the top "
                "of the dashboard for live figures."
            )

        tilt = result["tilt"]
        st.markdown(
            f'As of **{result["as_of_period"]}** · current '
            f'**\\${result["premium_current"]:,.0f}** &nbsp; '
            f'<span style="background:{tilt["color"]}; color:white; padding:2px 10px; '
            f'border-radius:12px; font-size:0.85rem">Tilt {tilt["score"]:+d} · '
            f'{tilt["label"]}</span>',
            unsafe_allow_html=True,
        )

        st.markdown("")
        st.markdown("**Next bidding exercise**")
        for col, scenario in zip(st.columns(3), result["next_exercise"]["scenarios"]):
            with col:
                _render_scenario_card(scenario)
        mp = result["next_exercise"]["most_probable"]
        if mp:
            st.success(mp["call"])

        nq = result["next_quarter"]
        if nq:
            st.markdown("")
            band = nq["band"]
            if band:
                st.markdown(
                    f"**Next quarter — {band['quarter']}** "
                    f"(curated band \\${band['low']:,.0f}–\\${band['high']:,.0f}, "
                    f"*{band['outlook']}*)"
                )
            else:
                st.markdown("**Next quarter** (signal-derived)")
            for col, scenario in zip(st.columns(3), nq["scenarios"]):
                with col:
                    _render_scenario_card(scenario)
            mpq = nq["most_probable"]
            if mpq:
                st.info(mpq["call"])

        if result["notes"]:
            with st.expander("Notes & caveats", expanded=False):
                for n in result["notes"]:
                    st.caption(f"· {n}")


# ─── Glossary ────────────────────────────────────────────────────────────────

GLOSSARY: list[tuple[str, str]] = [
    ("COE",
     "Certificate of Entitlement — the right to register a car for 10 years. "
     "LTA auctions a fixed quota twice a month; the clearing price is the "
     "premium you pay on top of the car's price."),
    ("Cat A / Cat B",
     "Cat A: cars ≤1600cc and ≤130bhp (mass-market). "
     "Cat B: cars >1600cc or >130bhp (larger / luxury / most EVs). "
     "Each category has its own quota and clearing price."),
    ("Bidding round (R1 / R2)",
     "Each month has two bidding exercises. R1 closes 1st-2nd week, "
     "R2 closes 3rd-4th week. Premium changes between rounds are the "
     "highest-frequency signal of where the market is heading."),
    ("Quota",
     "How many COEs LTA releases per quarter, set on a 4-quarter rolling "
     "average of deregistrations + a small policy adjustment. Tighter quota "
     "→ higher premiums."),
    ("Deregistration",
     "When an owner scraps or exports a car. Frees up a COE that LTA can "
     "re-issue. The 10-year cycle creates waves of deregistrations a decade "
     "after each registration boom."),
    ("Feast / Famine",
     "The cyclic supply pattern this section tracks. **Feast**: many cars "
     "bought 10 years ago hit deregistration → COE supply rises → premiums "
     "ease. **Famine**: few cars were registered a decade ago → tight supply "
     "→ premiums climb."),
    ("PARF",
     "Preferential Additional Registration Fee — a partial rebate paid back "
     "when you scrap a car within 10 years. Cut in Budget 2026, weakening "
     "the incentive to scrap early and so reducing future COE recycling."),
    ("PQP",
     "Prevailing Quota Premium — the 3-month moving average of COE prices, "
     "used as the renewal price if you keep a car past 10 years. Tracks the "
     "trend more smoothly than round-by-round premiums."),
    ("OMV",
     "Open Market Value — the LTA-assessed import cost of a car (CIF + "
     "incidental costs), the basis for ARF and other vehicle taxes."),
    ("EEAI",
     "EV Early Adoption Incentive — 45% off the ARF, capped at S$7,500 in "
     "2026 (S$15,000 in 2025). Ends 31 Dec 2026."),
    ("VES",
     "Vehicle Emissions Scheme — surcharge or rebate at registration based "
     "on the car's emissions band. From 2026 only EVs get rebates: Band A "
     "S$22,500 in 2026, S$20,000 in 2027. Stacks with EEAI in 2026."),
    ("VGR",
     "Vehicle Growth Rate — the policy cap on net growth of Singapore's "
     "vehicle population. Currently 0%, meaning every new COE has to come "
     "from a deregistration."),
]


def _render_glossary() -> None:
    """Compact two-column glossary, collapsed by default."""
    with st.expander("📖 Glossary — terms you'll see in this section", expanded=False):
        c1, c2 = st.columns(2)
        midpoint = (len(GLOSSARY) + 1) // 2
        for term, definition in GLOSSARY[:midpoint]:
            with c1:
                st.markdown(f"**{term}** — {definition}")
        for term, definition in GLOSSARY[midpoint:]:
            with c2:
                st.markdown(f"**{term}** — {definition}")


_STATUS_DOTS = {
    "OK": ("🟢", "OK"),
    "WATCH": ("🟡", "WATCH"),
    "STALE": ("🔴", "STALE"),
    "UNKNOWN": ("⚪", "?"),
}


def _render_thesis_health(stats: dict) -> None:
    """Surface each thesis claim with a status dot so authors know what to revisit."""
    audit = _audit_thesis(stats)

    counts = {"OK": 0, "WATCH": 0, "STALE": 0, "UNKNOWN": 0}
    for _, status, _ in audit:
        counts[status] = counts.get(status, 0) + 1

    summary = (
        f"🟢 {counts['OK']}  ·  🟡 {counts['WATCH']}  ·  🔴 {counts['STALE']}"
        f"{'  ·  ⚪ ' + str(counts['UNKNOWN']) if counts['UNKNOWN'] else ''}"
    )

    expand = counts["STALE"] > 0 or counts["WATCH"] > 0
    label = (
        f"Thesis health  ·  {summary}  ·  authored {THESIS_DATE:%b %Y}"
    )
    with st.expander(label, expanded=expand):
        st.caption(
            "Each row checks one numeric or temporal claim from the prose against "
            "current data. 🔴 means the claim's anchor no longer holds — the "
            "narrative section needs a rewrite. 🟡 means it's drifting."
        )
        for anchor, status, explanation in audit:
            dot, status_label = _STATUS_DOTS.get(status, _STATUS_DOTS["UNKNOWN"])
            st.markdown(
                f"{dot} **{anchor['claim']}** "
                f"<span style='opacity:0.6; font-size:0.85rem'>· "
                f"{anchor['tab']} · {status_label}</span>",
                unsafe_allow_html=True,
            )
            st.caption(explanation)


# ─── Main Render ─────────────────────────────────────────────────────────────

def render():
    """Render the COE Market Analysis section."""
    st.markdown('<div class="section-header">COE Market Analysis</div>',
                unsafe_allow_html=True)
    st.caption(
        "Where Singapore's COE premiums — the price of the right to own a car "
        "for 10 years — are heading, and why. All figures in SGD."
    )

    _render_glossary()

    # Freshness badge — shows the latest bidding round in the cache and when
    # the underlying coe_results table was last refreshed.
    data = _load_recent_premiums()
    latest_period = data[-1]["period"] if data else "—"
    refreshed = _load_coe_freshness()
    if refreshed:
        try:
            refreshed_label = datetime.fromisoformat(refreshed).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            refreshed_label = refreshed[:16]
    else:
        refreshed_label = "never (run `python3 run_pipeline.py`)"
    st.caption(
        f"Latest bidding round: **{latest_period}** · "
        f"Data refreshed: {refreshed_label} · "
        f"_Stale? Click **Refresh Data** at the top of the dashboard._"
    )

    # Thesis health audit — one row per claim, expanded if anything is amber/red.
    stats = _compute_market_stats(data)
    _render_thesis_health(stats)

    st.markdown("")

    tabs = st.tabs([
        "The Big Picture",
        "Price Trajectory",
        "10-Year Cycle",
        "Market Forces",
        "Buying Window",
        "Policy Radar",
    ])

    with tabs[0]:
        _render_overview()
    with tabs[1]:
        _render_trajectory()
    with tabs[2]:
        _render_cycle()
    with tabs[3]:
        _render_forces()
    with tabs[4]:
        _render_buying_window()
    with tabs[5]:
        from analysis.policy_radar import render as render_radar
        render_radar()


def render_outlook():
    """Render the standalone, top-level COE Bid Outlook tab.

    The synthesis view used to live as a sub-tab under COE Market Analysis;
    it is now surfaced as its own top-level tab for discoverability.
    """
    st.markdown('<div class="section-header">COE Bid Outlook</div>',
                unsafe_allow_html=True)
    _render_bid_outlook()
