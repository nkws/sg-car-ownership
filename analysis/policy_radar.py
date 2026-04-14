"""Policy Radar — Tracking upcoming policy changes that affect COE prices.

Signal strength is derived solely from observable evidence, not
subjective probability estimates. Each evidence item carries a
declared weight based on its type. The total determines the signal.

Evidence Weight Methodology
───────────────────────────
The weight assigned to each evidence type reflects how strongly that
type of signal predicts a policy change will actually happen, based
on Singapore's policy-making norms:

  Gazetted / Enacted law .............. 35 pts
    The change is already in force. No ambiguity remains.

  Budget announcement ................. 30 pts
    Announced by Finance Minister during Budget. Near-certain
    to proceed — Budget measures are rarely reversed.

  Parliamentary statement ............. 30 pts
    Minister's public commitment in Parliament. Strong signal
    of intent, though implementation details may shift.

  LTA/agency official release ......... 25 pts
    Formal press release or policy paper from the implementing
    agency. Signals active planning, not just intent.

  Public consultation launched ........ 20 pts
    Agency is gathering feedback. Change is being designed but
    outcome and timeline remain open.

  Statutory / scheduled review ........ 15 pts
    A review is mandated by existing policy cycle (e.g. VGR
    every 3 years). The review will happen; the outcome is open.

  Market / industry signal ............ 10 pts
    Observable market behaviour consistent with the policy
    change (e.g. buyers front-loading, dealers adjusting).

  Media coverage / analyst view ....... 5 pts
    Reporting or speculation without official confirmation.
    Weakest signal — may reflect noise rather than intent.

Signal Strength Thresholds
──────────────────────────
  >= 60 pts  →  Confirmed    Policy is enacted or near-certain
  >= 40 pts  →  Strong       Multiple high-weight signals converge
  >= 20 pts  →  Emerging     Credible signals but outcome uncertain
  <  20 pts  →  Speculative  Mainly media/analyst discussion
"""

import streamlit as st
import plotly.graph_objects as go

# ─── Evidence Weight Definitions ─────────────────────────────────────────────

EVIDENCE_WEIGHTS = {
    "Gazetted": 35,
    "Budget Announcement": 30,
    "Parliamentary": 30,
    "LTA/Agency Release": 25,
    "Public Consultation": 20,
    "Statutory Cycle": 15,
    "Market Signal": 10,
    "Media/Analyst": 5,
}

SIGNAL_THRESHOLDS = [
    (60, "Confirmed", "#59a14f"),
    (40, "Strong", "#4e79a7"),
    (20, "Emerging", "#f28e2b"),
    (0, "Speculative", "#e15759"),
]


def _signal_label(score):
    for threshold, label, color in SIGNAL_THRESHOLDS:
        if score >= threshold:
            return label, color
    return "Speculative", "#e15759"


# ─── Policy Data ─────────────────────────────────────────────────────────────

POLICIES = [
    {
        "id": "coe_recat",
        "name": "COE Category Redefinition",
        "status": "Under Review",
        "status_color": "#f28e2b",
        "summary": (
            "LTA reviewing how cars are categorised for COE bidding. Current system splits "
            "by engine displacement (Cat A <=1600cc, Cat B >1600cc), which is increasingly "
            "irrelevant with EVs (no engine). Potential shift to power-based, price-based, "
            "or weight-based categories."
        ),
        "direction": "up",
        "impact_range": "\\$5K - \\$20K",
        "impact_note": (
            "Short-term upward pressure as uncertainty drives pull-forward demand. "
            "Long-term impact depends on final design — could redistribute demand "
            "between categories rather than raise overall levels."
        ),
        "timeline": "Review concludes end-2026, implementation 2027-2028",
        "evidence": [
            {"type": "Parliamentary", "weight": 30,
             "detail": "Acting Transport Minister Jeffrey Siow announced review during "
                       "Budget 2026 debate (4 Mar 2026)"},
            {"type": "Public Consultation", "weight": 20,
             "detail": "LTA gathering views from motorists, dealers, manufacturers, "
                       "and academics. Public consultation expected mid-2026"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Cat A-Cat B premium gap narrowed to ~\\$3.7K (Feb 2025), "
                       "validating the convergence concern driving the review"},
            {"type": "Media/Analyst", "weight": 5,
             "detail": "Extensive coverage across Straits Times, CNA, Motorist.sg. "
                       "Industry expects changes by 2027-2028"},
        ],
    },
    {
        "id": "parf_cut",
        "name": "PARF Rebate Reduction",
        "status": "Implemented",
        "status_color": "#e15759",
        "summary": (
            "Budget 2026 slashed PARF rebates by ~45 percentage points across all tiers. "
            "Cars scrapped within 5 years now get 30% ARF back (was 75%). Cap halved from "
            "\\$60K to \\$30K. Applies to vehicles registered from 13 Feb 2026 onward."
        ),
        "direction": "up",
        "impact_range": "\\$5K - \\$15K",
        "impact_note": (
            "Less incentive to scrap early means fewer COEs recycled back into the system. "
            "More owners hold to 10 years or renew. Reduces future COE supply velocity. "
            "Effect is delayed — bites hardest from 2028-2031 when current registrations "
            "approach their 5-7 year mark."
        ),
        "timeline": "In effect since 13 Feb 2026 (Budget 2026)",
        "evidence": [
            {"type": "Budget Announcement", "weight": 30,
             "detail": "Announced in Budget 2026 by Finance Minister"},
            {"type": "Gazetted", "weight": 35,
             "detail": "Effective for COEs obtained from Feb 2026 R2 onwards. "
                       "Existing vehicles grandfathered under old rates"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Used car market for pre-Feb 2026 vehicles heating up as "
                       "buyers seek higher PARF retention under old rules"},
        ],
    },
    {
        "id": "eeai_sunset",
        "name": "EEAI Sunset (EV Rebate Phase-Out)",
        "status": "Winding Down",
        "status_color": "#f28e2b",
        "summary": (
            "The EV Early Adoption Incentive reduces from 45% ARF rebate (capped \\$15K) "
            "in 2025 to 45% (capped \\$7,500) in 2026, then ceases entirely after "
            "31 Dec 2026. Combined EV savings drop from ~\\$30K in 2026 to ~\\$20K in 2027."
        ),
        "direction": "up",
        "impact_range": "\\$3K - \\$10K",
        "impact_note": (
            "Creates pull-forward demand in H2 2026 as EV buyers rush to lock in "
            "incentives before the cliff. Post-sunset, EV demand normalises but "
            "total cost of EV ownership rises, potentially cooling one source of "
            "COE bidding pressure."
        ),
        "timeline": "EEAI ends 31 Dec 2026. VES continues through 2027 (rebates taper)",
        "evidence": [
            {"type": "LTA/Agency Release", "weight": 25,
             "detail": "Sep 2025: LTA/NEA joint release — EEAI extended to Dec 2026 "
                       "with reduced cap. VES extended to Dec 2027 with EV-only rebates"},
            {"type": "Budget Announcement", "weight": 30,
             "detail": "Budget 2026 confirmed no further EEAI extension. "
                       "2026 is the final year"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Tesla, BYD dealers reporting accelerated H2 2026 orders "
                       "as buyers front-load before EEAI cliff"},
        ],
    },
    {
        "id": "vgr_review",
        "name": "Vehicle Growth Rate Review (Jan 2028)",
        "status": "Scheduled",
        "status_color": "#4e79a7",
        "summary": (
            "The 0% VGR for cars (Categories A, B, D) expires 31 Jan 2028. "
            "LTA reviews every 3 years. Could maintain 0%, go negative (shrink fleet), "
            "or allow slight positive growth. Category C (goods vehicles) stays at 0.25%."
        ),
        "direction": "uncertain",
        "impact_range": "\\$10K - \\$30K",
        "impact_note": (
            "If VGR stays at 0%: neutral, status quo continues. "
            "If VGR goes negative: significantly bullish for COE (fewer certificates). "
            "If VGR goes slightly positive (e.g. 0.25%): meaningful bearish pressure "
            "as net new supply enters the system for the first time since 2018."
        ),
        "timeline": "Review in late 2027, effective Feb 2028",
        "evidence": [
            {"type": "Statutory Cycle", "weight": 15,
             "detail": "VGR is reviewed every 3 years. Current period: "
                       "Feb 2025 - Jan 2028. Next review due late 2027"},
            {"type": "Market Signal", "weight": 10,
             "detail": "0% VGR maintained since 2018. Government has signalled "
                       "desire to keep vehicle population stable. No hints of change"},
            {"type": "Media/Analyst", "weight": 5,
             "detail": "LTA tied the 20,000 COE injection to ERP 2.0's ability "
                       "to manage congestion. If ERP 2.0 works, slight VGR increase "
                       "becomes more politically feasible"},
        ],
    },
    {
        "id": "erp2",
        "name": "ERP 2.0 Full Rollout",
        "status": "In Progress",
        "status_color": "#59a14f",
        "summary": (
            "Satellite-based (GNSS) road pricing replacing physical gantries. "
            "OBU installation 93% complete as of Jan 2026. Full transition from "
            "1 Jan 2027. Enables distance-based or time-based charging, "
            "more granular congestion management."
        ),
        "direction": "down",
        "impact_range": "\\$0 - \\$5K (indirect)",
        "impact_note": (
            "ERP 2.0 itself doesn't directly affect COE prices. But it gives LTA "
            "better congestion management tools, which could justify a future VGR "
            "increase (more cars manageable with smarter pricing). The 20,000 COE "
            "injection was explicitly tied to ERP 2.0 readiness."
        ),
        "timeline": "Full rollout 1 Jan 2027. Gantry dismantling through 2026-2027",
        "evidence": [
            {"type": "LTA/Agency Release", "weight": 25,
             "detail": "OBU mandatory from 1 Jan 2027. 93% installed as of Jan 2026"},
            {"type": "Gazetted", "weight": 35,
             "detail": "Road Traffic Act amendments passed Feb 2026 to facilitate "
                       "ERP 2.0 transition and enhanced penalties"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Road signs and markings for gantry-free system trialled "
                       "Mar 2026. ERP rates increased at 4 locations from Mar 2026"},
        ],
    },
    {
        "id": "coe_supply_smoothing",
        "name": "COE Supply Smoothing Mechanism",
        "status": "Active",
        "status_color": "#59a14f",
        "summary": (
            "Since Feb 2023, COE quota uses a 4-quarter rolling average of "
            "deregistrations (was 2-quarter). Plus LTA injecting ~20,000 additional "
            "COEs progressively from Feb 2025. Both mechanisms dampen the amplitude "
            "of the feast-famine cycle."
        ),
        "direction": "down",
        "impact_range": "\\$5K - \\$15K",
        "impact_note": (
            "The smoothing prevents sharp COE crashes (good for sellers) but also "
            "prevents sharp spikes (good for buyers). Net effect: the coming "
            "deregistration wave produces a gradual dip rather than a cliff. "
            "The 20,000 injection adds ~3,300-5,000 COEs per year."
        ),
        "timeline": "4-quarter averaging: active since Feb 2023. 20K injection: from Feb 2025",
        "evidence": [
            {"type": "LTA/Agency Release", "weight": 25,
             "detail": "4-quarter rolling average implemented Feb 2023"},
            {"type": "LTA/Agency Release", "weight": 25,
             "detail": "Oct 2024: LTA announced ~20,000 additional COEs from Feb 2025, "
                       "linked to ERP 2.0 and reduced-usage COE scheme"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Feb-Apr 2026 quota at 18,824 — still elevated despite slight "
                       "reduction, showing smoothing in action"},
        ],
    },
]


# ─── Render ──────────────────────────────────────────────────────────────────

def render():
    """Render the Policy Radar section."""

    # Methodology declaration
    with st.expander("Signal Strength Methodology", expanded=False):
        st.markdown(
            "Signal strength is derived from **observable evidence only**, not subjective "
            "probability estimates. Each evidence item carries a weight based on its type:"
        )
        st.markdown("")
        meth_data = []
        for etype, weight in sorted(EVIDENCE_WEIGHTS.items(), key=lambda x: -x[1]):
            meth_data.append({"Evidence Type": etype, "Weight": f"{weight} pts"})
        st.dataframe(meth_data, use_container_width=True, hide_index=True)
        st.markdown("")
        st.markdown("**Signal thresholds** (sum of evidence weights):")
        for threshold, label, color in SIGNAL_THRESHOLDS:
            st.markdown(f"- **{label}** (>= {threshold} pts)")

    st.markdown("")

    # Summary metrics
    for p in POLICIES:
        p["_score"] = sum(e["weight"] for e in p["evidence"])
        p["_signal"], p["_signal_color"] = _signal_label(p["_score"])

    confirmed = sum(1 for p in POLICIES if p["_signal"] == "Confirmed")
    strong = sum(1 for p in POLICIES if p["_signal"] == "Strong")
    emerging = sum(1 for p in POLICIES if p["_signal"] == "Emerging")
    speculative = sum(1 for p in POLICIES if p["_signal"] == "Speculative")

    pm1, pm2, pm3, pm4 = st.columns(4)
    pm1.metric("Policies Tracked", str(len(POLICIES)))
    pm2.metric("Confirmed", str(confirmed))
    pm3.metric("Strong Signals", str(strong))
    pm4.metric("Emerging / Speculative", str(emerging + speculative))

    st.markdown("")

    # Net direction
    up_forces = [p for p in POLICIES if p["direction"] == "up"]
    down_forces = [p for p in POLICIES if p["direction"] == "down"]
    uncertain_forces = [p for p in POLICIES if p["direction"] == "uncertain"]

    st.markdown(
        f"**Net policy direction:** {len(up_forces)} upward, "
        f"{len(down_forces)} downward, {len(uncertain_forces)} uncertain. "
        f"The policy environment is currently **net bullish** for COE prices — "
        f"most confirmed changes (PARF cut, EEAI sunset, COE recat uncertainty) "
        f"push premiums up, while downward forces (supply smoothing, ERP 2.0) "
        f"are structural dampeners rather than price reducers."
    )

    st.markdown("")

    # Evidence Strength vs Impact chart
    fig = go.Figure()

    for p in POLICIES:
        color = "#e15759" if p["direction"] == "up" else (
            "#59a14f" if p["direction"] == "down" else "#f28e2b"
        )

        fig.add_trace(go.Scatter(
            x=[p["_score"]],
            y=[len(p["evidence"])],
            mode="markers+text",
            marker=dict(size=20, color=color, opacity=0.7,
                        line=dict(width=1, color="white")),
            text=[p["name"].split("(")[0].strip()[:25]],
            textposition="top center",
            textfont=dict(size=10),
            name=p["name"],
            hovertemplate=(
                f"<b>{p['name']}</b><br>"
                f"Evidence: {p['_score']} pts ({p['_signal']})<br>"
                f"Sources: {len(p['evidence'])}<br>"
                f"Direction: {p['direction']}<br>"
                f"Impact: {p['impact_range']}<br>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Threshold lines
    for threshold, label, color in SIGNAL_THRESHOLDS:
        if threshold > 0:
            fig.add_vline(x=threshold, line_dash="dot",
                          line_color=color, opacity=0.5,
                          annotation_text=label,
                          annotation_position="top")

    fig.update_layout(
        template="streamlit", height=350,
        xaxis=dict(title="Evidence Strength (pts)", range=[0, 85]),
        yaxis=dict(title="Number of Evidence Sources", dtick=1),
        margin=dict(t=30, b=40, l=60, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bubble color: red = pushes COE up, green = pushes COE down, orange = uncertain. "
               "Vertical lines show signal thresholds.")

    st.markdown("")

    # Detailed policy cards
    for p in POLICIES:
        dir_arrow = "&#x25B2;" if p["direction"] == "up" else (
            "&#x25BC;" if p["direction"] == "down" else "&#x25C6;"
        )
        dir_color = "#e15759" if p["direction"] == "up" else (
            "#59a14f" if p["direction"] == "down" else "#f28e2b"
        )

        st.markdown("---")

        # Header row
        hc1, hc2, hc3 = st.columns([4, 1, 1])
        with hc1:
            st.markdown(f"### {p['name']}")
        with hc2:
            st.markdown(
                f'<span style="background:{p["status_color"]}; color:white; '
                f'padding:2px 10px; border-radius:12px; font-size:0.8rem">'
                f'{p["status"]}</span>',
                unsafe_allow_html=True,
            )
        with hc3:
            st.markdown(
                f'<span style="color:{dir_color}; font-size:1.5rem">{dir_arrow}</span>'
                f' <span style="font-size:0.85rem">{p["impact_range"]}</span>',
                unsafe_allow_html=True,
            )

        st.markdown(p["summary"])

        # Metrics row
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Signal Strength",
                   f"{p['_score']} pts — {p['_signal']}",
                   delta=f"{len(p['evidence'])} evidence sources")
        mc2.metric("COE Direction", p["direction"].title(),
                   delta=p["impact_range"])
        mc3.metric("Timeline", p["timeline"].split(".")[0][:35])

        # Evidence trail — always visible, shows how score is built
        st.markdown("**Evidence Trail**")
        for e in p["evidence"]:
            ec1, ec2, ec3 = st.columns([1.5, 0.5, 5])
            with ec1:
                st.markdown(f"**{e['type']}**")
            with ec2:
                st.markdown(f"`+{e['weight']}pts`")
            with ec3:
                st.caption(e["detail"])

        # Impact analysis
        st.caption(f"**Impact:** {p['impact_note']}")
