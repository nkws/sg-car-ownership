"""COE Market Analysis — The Coming COE Dip Cycle.

A structural analysis of supply dynamics, policy shifts, and the
feast-famine rhythm that governs Singapore's COE market.

Published: March 2026
"""

from datetime import datetime

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
    {"name": "EEAI Sunset (Jan 2027)", "direction": "up", "magnitude": 50,
     "detail": "EV rebate drops from \\$40K to \\$30K to \\$0; pull-forward demand in 2026"},
    {"name": "Potential Recession (Global)", "direction": "down", "magnitude": 55,
     "detail": "If US tariffs / slowdown spill over, buyer sentiment weakens"},
    {"name": "0% Vehicle Growth Rate (to Jan 2028)", "direction": "up", "magnitude": 65,
     "detail": "No net addition to vehicle population; pure replacement system"},
]

QUARTERLY_OUTLOOK = [
    {"quarter": "Q2 2026 (Apr-Jun)", "range": "\\$105K - \\$115K", "outlook": "Sideways to slight up",
     "color": "#f28e2b",
     "note": "3-week gap before Apr R1 may cause a spike. Feb-Apr quota slightly reduced. "
             "EEAI pull-forward demand still active."},
    {"quarter": "Q3 2026 (Jul-Sep)", "range": "\\$95K - \\$108K", "outlook": "Moderate dip begins",
     "color": "#edc949",
     "note": "New May-Jul quota should reflect rising deregistrations. Market sentiment may soften "
             "if global recession materialises. This is the start of the window."},
    {"quarter": "Q4 2026 (Oct-Dec)", "range": "\\$85K - \\$100K", "outlook": "Best window (if recession hits)",
     "color": "#59a14f",
     "note": "Peak supply from deregistration wave coincides with year-end budget tightening. "
             "If recession sentiment deepens, expect the lowest point. EEAI ends Jan 2027 -> "
             "last rush for EV incentives could spike Dec."},
    {"quarter": "Q1 2027 (Jan-Mar)", "range": "\\$88K - \\$105K", "outlook": "Rebound risk",
     "color": "#f28e2b",
     "note": "Post-EEAI demand normalisation. CNY rush. If economy recovers, pent-up demand "
             "floods back. The window may already be closing."},
    {"quarter": "Q2-Q3 2027", "range": "\\$90K - \\$110K", "outlook": "Stabilisation at new floor",
     "color": "#b07aa1",
     "note": "PARF cut effect starts biting — fewer early deregistrations reducing COE recycling. "
             "Supply growth decelerates."},
]

STRATEGY_ITEMS = [
    {"label": "Primary Window", "value": "Jul - Nov 2026",
     "detail": "Wait for the Q3 quota reset and potential recession softening. "
               "Bid in Aug-Oct if Cat A dips below \\$95K."},
    {"label": "Aggressive Target", "value": "\\$80K Cat A",
     "detail": "Achievable only if a meaningful recession hits + deregistration wave fully "
               "materialises. Low-probability scenario (~20%)."},
    {"label": "Realistic Target", "value": "\\$88K - \\$95K Cat A",
     "detail": "More probable range at the trough (~50% probability). Still delivers "
               "~\\$13K-\\$15K annual depreciation if held 10 years."},
    {"label": "EV Insulation", "value": "EEAI + VES still active in 2026",
     "detail": "Tesla Model Y still qualifies for ~\\$25K in combined incentives "
               "(EEAI \\$30K + VES). After Jan 2027, EEAI drops to \\$0. Act before Dec 2026."},
    {"label": "Risk of Waiting", "value": "Jan 2027 EEAI Cliff",
     "detail": "If you wait past Dec 2026 for a lower COE, you lose \\$30K in EEAI rebate. "
               "The maths strongly favours bidding in H2 2026 even at slightly higher COE."},
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


# ─── Thesis audit ────────────────────────────────────────────────────────────

# When the analyst-written prose was authored. Surface this date so readers
# know the structural narrative is a snapshot, not a live document.
THESIS_DATE = datetime(2026, 3, 1)

# Each anchor encodes one numeric/temporal claim from the prose. The audit
# function checks each against current data and tags it OK / WATCH / STALE so
# we know when to revisit the narrative.
THESIS_ANCHORS: list[dict] = [
    {
        "claim": "Cat A 'currently in the ~$110K range'",
        "tab": "Big Picture",
        "kind": "price_band",
        "anchor": 110000,
        "tolerance_pct": 15,
    },
    {
        "claim": "Forecasted Cat A trough: $85K–$95K by mid-2027",
        "tab": "Big Picture / Forces",
        "kind": "trough",
        "low": 85000,
        "high": 95000,
        "trough_by": datetime(2027, 6, 30),
    },
    {
        "claim": "Reference peak: Cat A $128K (Oct 2025 spike)",
        "tab": "Trajectory",
        "kind": "peak_reference",
        "peak_value": 128000,
        "peak_period_match": "Oct 25",
    },
    {
        "claim": "Cat A–B gap is unusually narrow (~$3.7K)",
        "tab": "Trajectory",
        "kind": "gap_band",
        "anchor": 3700,
        "tolerance_pct": 50,
    },
    {
        "claim": "Optimal buying window: Oct–Nov 2026",
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
    st.markdown(
        "Singapore's COE market is entering the early stages of a structural supply expansion "
        "driven by the 10-year deregistration wave from the 2016-2017 registration boom. "
        "However, this isn't a straightforward \"prices will crash\" story. Multiple "
        "countervailing forces — the Budget 2026 PARF cuts, persistent affluent demand, "
        "EV adoption dynamics, and LTA's own supply-smoothing mechanisms — are creating a "
        "**moderated, drawn-out dip** rather than a sharp correction."
    )
    st.markdown("")

    data = _load_recent_premiums()
    stats = _compute_market_stats(data)
    latest = stats.get("latest")

    # Round latest Cat A to nearest $5K to feel like a "range" anchor.
    if latest:
        anchor_k = round(latest["catA"] / 5000) * 5000 // 1000
        outlook_line = (
            f"**Most probable outcome:** Cat A premiums ease from the current "
            f"~\\${anchor_k}K range toward \\$85K-\\$95K by late 2026 to mid-2027, "
            f"then stabilise or rebound. The window is real but narrower than the "
            f"market expects."
        )
    else:
        outlook_line = (
            "**Most probable outcome:** Cat A premiums ease toward \\$85K-\\$95K by "
            "late 2026 to mid-2027, then stabilise or rebound."
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

    down_total = sum(f["magnitude"] for f in FORCE_DATA if f["direction"] == "down")
    up_total = sum(f["magnitude"] for f in FORCE_DATA if f["direction"] == "up")

    na1, na2 = st.columns(2)
    na1.metric("Downward Pressure", str(down_total),
               delta="Supply relief + macro risk")
    na2.metric("Upward Pressure", str(up_total),
               delta="Demand + policy headwinds", delta_color="inverse")

    st.markdown("")
    st.info(
        "Upward forces currently outweigh downward ones. This is why the \"dip\" will be "
        "moderate — expect **\\$85K-\\$95K** for Cat A at the trough, not \\$60K-\\$70K. "
        "The market has structurally repriced car ownership in Singapore."
    )


def _render_buying_window():
    st.markdown(
        "Based on the supply cycle, PARF dynamics, EEAI sunset, and demand signals, "
        "here's a quarter-by-quarter projection:"
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
        "**The Critical Insight:** The \\$30K EEAI rebate you'd lose after Dec 2026 dwarfs any "
        "plausible COE savings from waiting into 2027. Even if COE drops \\$15K further in "
        "Q1 2027 (optimistic), you'd be net \\$15K worse off after losing EEAI. The optimal "
        "play is to bid aggressively in **Oct-Nov 2026** when deregistration supply peaks "
        "and year-end sentiment is weakest, while EEAI is still intact. That's your "
        "convergence point — maximum supply, softened demand, and full incentive stack."
    )


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
        "A structural analysis of supply dynamics, policy shifts, and the "
        "feast-famine rhythm that governs Singapore's COE market."
    )

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
        f"Data refreshed: {refreshed_label}"
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
