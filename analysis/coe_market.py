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
    st.markdown(
        "**Most probable outcome:** Cat A premiums ease from the current ~\\$110K range toward "
        "\\$85K-\\$95K by late 2026 to mid-2027, then stabilise or rebound. "
        "The window is real but narrower than the market expects."
    )

    st.markdown("")
    m1, m2, m3, m4 = st.columns(4)

    data = _load_recent_premiums()
    latest = data[-1] if data else None
    prior = data[-2] if len(data) >= 2 else None

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

    # Quota and PQP come from separate sources not yet wired to SQLite —
    # leave hardcoded for now.
    m3.metric("Feb-Apr 26 Quota", "18,824", delta="-160 from prev qtr")
    m4.metric("PQP Cat A (Apr 26)", "$107,407", delta="-$6,597 from Jan")


def _render_trajectory():
    st.markdown(
        "Since the Oct 2025 spike (Cat A hit \\$128K, Cat B hit \\$141K), premiums have corrected "
        "meaningfully — roughly 13% for Cat A and 18% for Cat B. But the trend since Jan 2026 "
        "has been a steady grind upward again, with both categories climbing across four "
        "consecutive exercises."
    )
    st.markdown("")
    st.markdown(
        "The Cat A-Cat B gap narrowed to as little as ~\\$5K in late 2025, making Cat B a "
        "\"no-brainer\" upgrade. That gap has now widened slightly to ~\\$3.7K, but remains "
        "unusually tight by historical standards."
    )

    df = pd.DataFrame(_load_recent_premiums())
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

    st.markdown("**Key Observation: The \"Post-Spike Plateau\"**")
    st.markdown(
        "After the Oct 2025 record spike, premiums corrected but have not returned to mid-2025 "
        "levels (~\\$95K-\\$101K for Cat A). Instead they've formed a new elevated floor around "
        "\\$106K-\\$112K. This is the plateau pattern — each cycle's correction lands at a higher "
        "base than the previous one."
    )
    st.markdown("")
    st.markdown(
        "The PQP (Prevailing Quota Premium) for Cat A has declined from \\$114K in January to "
        "\\$107K in April — a positive sign for prospective buyers, since PQP represents the "
        "3-month moving average and signals the directional trend."
    )

    pq1, pq2 = st.columns(2)
    pq1.metric("PQP Cat A (Jan 26)", "$114,004")
    pq2.metric("PQP Cat A (Apr 26)", "$107,407", delta="-$6,597", delta_color="normal")


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
