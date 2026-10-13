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


def policy_net() -> dict:
    """Net policy direction across all tracked policies, weighted by signal.

    Counts policies by their COE direction (up/down/uncertain) and, separately,
    counts only those whose evidence clears the "Strong" threshold (>= 40 pts).
    The net direction is decided on the strong-signal tally so that speculative
    chatter can't swing it. Pure — no Streamlit, safe to import anywhere.
    """
    up = down = uncertain = 0
    strong_up = strong_down = 0
    for p in POLICIES:
        score = sum(e["weight"] for e in p["evidence"])
        direction = p["direction"]
        if direction == "up":
            up += 1
            if score >= 40:
                strong_up += 1
        elif direction == "down":
            down += 1
            if score >= 40:
                strong_down += 1
        else:
            uncertain += 1

    if strong_up > strong_down:
        net_direction = "up"
    elif strong_down > strong_up:
        net_direction = "down"
    else:
        net_direction = "balanced"

    return {
        "up": up,
        "down": down,
        "uncertain": uncertain,
        "strong_up": strong_up,
        "strong_down": strong_down,
        "net_direction": net_direction,
    }


# ─── Policy Data ─────────────────────────────────────────────────────────────

RADAR_REVIEWED = "13 Oct 2026"

_NET_LABEL = {"up": "net bullish", "down": "net bearish", "balanced": "balanced"}

POLICIES = [
    {
        "id": "coe_recat",
        "name": "COE Cat A/B Merger + OMV Feebate",
        "status": "Public Consultation",
        "status_color": "#f28e2b",
        "summary": (
            "LTA's 8 Oct 2026 consultation proposes merging Cat A and B into one car category "
            "with a single COE price, then applying a rebate or surcharge by the model's median "
            "OMV. Three-band option: bottom 35% get -\\$15K, 35-50th pct \\$0, above median "
            "+\\$15K. Five-band option: -\\$15K / -\\$7.5K / \\$0 / +\\$7.5K / +\\$15K. Cat E may "
            "be removed or limited to cars. Feedback closes 2 Nov 2026. Not yet policy."
        ),
        "direction": "uncertain",
        "impact_range": "±\\$7.5K - \\$15K per car",
        "impact_note": (
            "LTA says the merger is not meant to change the overall COE level — it "
            "redistributes cost by car value. Cheaper cars could net up to \\$15K less, "
            "above-median OMV cars up to \\$15K more. Short-term, uncertainty may pull purchases "
            "forward. Renewals (PQP) may be exempt from the feebate; transition terms are open."
        ),
        "timeline": "Consultation to 2 Nov 2026; review ends 2026; findings H1 2027",
        "evidence": [
            {"type": "Parliamentary", "weight": 30,
             "detail": "Acting Transport Minister Jeffrey Siow announced review during "
                       "Budget 2026 debate (4 Mar 2026)"},
            {"type": "Public Consultation", "weight": 20,
             "detail": "LTA consultation launched 8 Oct 2026 with two concrete feebate designs; "
                       "closes 2 Nov 2026. Pay-as-you-bid, family-needs allocation, a PHV "
                       "category and a multi-car surcharge were set aside"},
            {"type": "Market Signal", "weight": 10,
             "detail": "Cat A closed above Cat B on 22 Apr and 17 Jun 2026; gap just \\$99 on "
                       "7 Oct (\\$130,001 vs \\$130,100). LTA cites EVs tuned to fit Cat A limits"},
            {"type": "Media/Analyst", "weight": 5,
             "detail": "NUS (Timothy Wong) and SUSS (Walter Theseira) academics broadly "
                       "supportive; Dollars and Sense and a Motorist guest column argue it "
                       "won't lower prices. Reported examples put the Tesla Model Y RWD in the "
                       "surcharge band under both options"},
        ],
        "debate": {
            "reviewed": "13 Oct 2026",
            "pros": [
                ("LTA", "Engine/power no longer separates cars by value — EVs can be tuned "
                        "under the Cat A limit. Cat A beat Cat B three times Feb-Jun 2026."),
                ("Walter Theseira, SUSS", "OMV is harder to game than specs: you can't evade "
                        "the dollar cost of the car. Closes the EV loophole."),
                ("Timothy Wong, NUS", "Feebate should give mass-market buyers cheaper "
                        "effective COEs; middle-income households likely benefit."),
                ("Dollars and Sense", "Overdue: CLA180 variants with the same engine and "
                        "price sit in different categories over a 5 bhp difference."),
                ("LTA", "Bands published yearly, so buyers know a model's rebate or "
                        "surcharge before buying; retailers can appeal a band."),
            ],
            "cons": [
                ("Walter Theseira, SUSS", "Hard to predict whether COE prices fall at all. "
                        "The only guarantee is that pricier cars pay more."),
                ("Timothy Wong, NUS", "Small, low-power cars with a high OMV could end up "
                        "paying more than today."),
                ("Dollars and Sense", "One pool still treats a PHV earning income all day the "
                        "same as a family car, and a third car the same as a first car. If the "
                        "common premium rises by more than the rebate, families pay more."),
                ("Motorist guest column (Sep, pre-consultation)", "Merging spreads Cat A's EV "
                        "demand into Cat B. Chinese EV and luxury brands bidding in one pool "
                        "favour high-margin models; mass-market cars get deprioritised."),
                ("Open in the consultation", "Three bands means big jumps between similar "
                        "cars; five is fairer but more complex. Renewal treatment, transition "
                        "terms and Cat E's fate are undecided."),
            ],
            "takeaway": (
                "Supporters and critics largely agree on one point: this fixes *who pays "
                "what*, not *how much COEs cost overall*. Nobody quoted expects it to lower "
                "the headline premium. For an above-median-OMV car like a Tesla Model Y, "
                "the likely effect is a surcharge of \\$7.5K-\\$15K on top of the merged price."
            ),
        },
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
            "31 Dec 2026. VES Band A EV rebate also steps from \\$22,500 (2026) to \\$20,000 "
            "(2027). Combined EV savings drop from up to \\$30K to \\$20K — a ~\\$10K cliff."
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
            "Over 98% of eligible vehicles fitted with OBUs (Sep 2026). Gantry charging "
            "stops 31 Dec 2026; ERP 2 launches 1 Jan 2027. Enables distance-based or "
            "time-based charging, more granular congestion management."
        ),
        "direction": "down",
        "impact_range": "\\$0 - \\$5K (indirect)",
        "impact_note": (
            "ERP 2.0 itself doesn't directly affect COE prices. But it gives LTA "
            "better congestion management tools, which could justify a future VGR "
            "increase (more cars manageable with smarter pricing). The 20,000 COE "
            "injection was explicitly tied to ERP 2.0 readiness."
        ),
        "timeline": "Launch 1 Jan 2027. Gantry removal Oct 2026 - Jun 2027",
        "evidence": [
            {"type": "LTA/Agency Release", "weight": 25,
             "detail": "Sep 2026: new road markings/signs from Oct 2026; 62 idle gantries "
                       "removed from Oct, 33 live gantries after 31 Dec. >98% OBUs fitted. "
                       "Next ERP rate review mid-Nov 2026"},
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
             "detail": "Aug-Oct 2026 quota 19,085 (+0.2% QoQ): Cat A 7,134 (-300), "
                       "Cat B 5,527 (+322). Smoothing is holding supply flat — no visible "
                       "deregistration surge yet, and premiums hit records regardless"},
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
    net = policy_net()

    st.markdown(
        f"**Net policy direction:** {net['up']} upward, "
        f"{net['down']} downward, {net['uncertain']} uncertain. "
        f"On strong signals (>= 40 pts) it is {net['strong_up']} up vs "
        f"{net['strong_down']} down, so the policy environment reads "
        f"**{_NET_LABEL[net['net_direction']]}** for COE prices. The confirmed upward "
        f"changes (PARF cut, EEAI sunset) raise ownership cost, while the downward "
        f"forces (supply smoothing, ERP 2.0) are structural dampeners rather than price "
        f"reducers. The proposed Cat A/B merger is designed to be level-neutral and "
        f"mainly redistributes cost by car value."
    )
    st.caption(f"Policy evidence last reviewed {RADAR_REVIEWED}.")

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

        # Public debate — attributed pros and cons, where tracked
        debate = p.get("debate")
        if debate:
            with st.expander(f"Public debate: pros & cons (reviewed {debate['reviewed']})"):
                dc1, dc2 = st.columns(2)
                with dc1:
                    st.markdown("**For**")
                    for who, point in debate["pros"]:
                        st.markdown(f"- **{who}:** {point}")
                with dc2:
                    st.markdown("**Against / open questions**")
                    for who, point in debate["cons"]:
                        st.markdown(f"- **{who}:** {point}")
                st.info(debate["takeaway"])
