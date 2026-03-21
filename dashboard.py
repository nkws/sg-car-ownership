"""Streamlit Dashboard for SG Car Ownership Financial Profiling."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from database import get_conn, init_db
from config import SIGNAL_FILE, DB_PATH, SEGMENT_THRESHOLDS

st.set_page_config(
    page_title="SG Car Ownership — Financial Stress Dashboard",
    page_icon="🚗",
    layout="wide",
)

# ─── Custom Styling ──────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Tighten top padding */
    .block-container {
        padding-top: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    /* Section spacing */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid var(--secondary-background-color);
    }
    /* Metric cards */
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 8px;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 500;
    }
    /* Color-coded metric cards */
    .metric-green [data-testid="stMetric"] {
        border-left: 4px solid #2e7d32;
        background: rgba(46, 125, 50, 0.12);
    }
    .metric-yellow [data-testid="stMetric"] {
        border-left: 4px solid #f9a825;
        background: rgba(249, 168, 37, 0.12);
    }
    .metric-red [data-testid="stMetric"] {
        border-left: 4px solid #c62828;
        background: rgba(198, 40, 40, 0.12);
    }
    /* Alert styling */
    .stAlert {
        margin-bottom: 0.5rem;
    }
    /* Consistent chart margins */
    .stPlotlyChart {
        margin-bottom: 0.5rem;
    }
    /* Term definitions */
    .term-def {
        font-size: 0.82rem;
        color: var(--text-color);
        margin-bottom: 0.3rem;
    }
    .term-label {
        font-weight: 600;
        color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

# ─── Load Data ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def ensure_data():
    """Auto-run pipeline if no data exists (e.g. fresh deployment)."""
    if not SIGNAL_FILE.exists() or not DB_PATH.exists():
        from run_pipeline import main as run_pipeline
        run_pipeline()

@st.cache_data(ttl=300)
def load_signal():
    ensure_data()
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    return None

@st.cache_data(ttl=300)
def load_coe_history():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium
            FROM coe_results
            GROUP BY month, vehicle_class
            ORDER BY month
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=300)
def load_town_profiles():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM town_profile ORDER BY fsi_score DESC").fetchall()
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=300)
def load_income_segments():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT dwelling_type, median_income, income_bracket, percentage
            FROM household_income
            ORDER BY median_income
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=300)
def load_hp_data():
    init_db()
    with get_conn() as conn:
        try:
            rows = conn.execute("SELECT * FROM mas_hire_purchase ORDER BY year, quarter").fetchall()
            return pd.DataFrame([dict(r) for r in rows])
        except Exception:
            return pd.DataFrame()

# ─── Header ──────────────────────────────────────────────────────────────────

signal = load_signal()
car_costs = signal.get("car_costs", {}) if signal else {}

st.markdown("## SG Car Ownership")
st.markdown("**Financial Stress Dashboard**")

if signal:
    ts = signal.get("timestamp", "N/A")[:10]
    st.caption(f"Data as of {ts}")

    st.markdown("")  # spacer

    # ── FSI Score Cards ──────────────────────────────────────────────────────

    def score_color(score):
        if score < 40: return "green"
        if score < 60: return "yellow"
        return "red"

    def stress_label(score):
        if score < 30: return "Low"
        if score < 45: return "Moderate"
        if score < 60: return "Elevated"
        if score < 75: return "High"
        return "Critical"

    col1, col2, col3, col4 = st.columns(4)

    fsi = signal["fsi_score"]
    components = signal.get("fsi_components", {})

    with col1:
        st.markdown(f'<div class="metric-{score_color(fsi)}">', unsafe_allow_html=True)
        st.metric("Composite FSI", f"{fsi:.0f} / 100", delta=stress_label(fsi))
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Weighted average of all three components. Overall stress gauge.")

    coe_aff = components.get('coe_affordability', 0)
    with col2:
        st.markdown(f'<div class="metric-{score_color(coe_aff)}">', unsafe_allow_html=True)
        st.metric("COE Affordability", f"{coe_aff:.0f} / 100", delta=stress_label(coe_aff))
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("How expensive COE premiums are vs historical average. Higher = less affordable.")

    credit = components.get('credit_stress', 0)
    with col3:
        st.markdown(f'<div class="metric-{score_color(credit)}">', unsafe_allow_html=True)
        st.metric("Credit Stress", f"{credit:.0f} / 100", delta=stress_label(credit))
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Hire purchase debt levels and interest rates. Higher = more borrowing pressure.")

    market = components.get('market_signals', 0)
    with col4:
        st.markdown(f'<div class="metric-{score_color(market)}">', unsafe_allow_html=True)
        st.metric("Market Signals", f"{market:.0f} / 100", delta=stress_label(market))
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("COE bidding competition and premium volatility. Higher = more market tension.")

    st.markdown("")  # spacer

    # ── Alerts ───────────────────────────────────────────────────────────────

    alerts = signal.get("alerts", [])
    if alerts:
        with st.expander("Active Alerts", expanded=True):
            for a in alerts:
                st.warning(a)

    st.markdown("")  # spacer

    # ── Monthly Car Costs ────────────────────────────────────────────────────

    st.markdown('<div class="section-header">Monthly Car Ownership Costs</div>',
                unsafe_allow_html=True)

    cc1, cc2, cc3 = st.columns([2, 2, 3])
    if car_costs:
        cat_a = car_costs.get("cat_a", {})
        cat_b = car_costs.get("cat_b", {})
        cc1.metric("Cat A (up to 1600cc)",
                   f"${cat_a.get('monthly_total', 0):,.0f} / mo",
                   delta=f"Vehicle: ${cat_a.get('vehicle_cost', 0):,.0f}")
        cc2.metric("Cat B (above 1600cc)",
                   f"${cat_b.get('monthly_total', 0):,.0f} / mo",
                   delta=f"Vehicle: ${cat_b.get('vehicle_cost', 0):,.0f}")
    with cc3:
        st.caption("Includes loan repayment, insurance, road tax, petrol, parking, maintenance. "
                   "Based on 60% financing over 7 years. "
                   "Loan computed at 2.78% flat rate (≈5.2% EIR) — "
                   "the standard SG dealer-quoted flat rate, not the effective interest rate.")

# ─── COE Premium History ─────────────────────────────────────────────────────

st.markdown('<div class="section-header">COE Premium History</div>',
            unsafe_allow_html=True)

coe_df = load_coe_history()
if not coe_df.empty:
    categories = coe_df["vehicle_class"].unique().tolist()
    selected_cats = st.multiselect(
        "Filter by vehicle class",
        categories,
        default=[c for c in categories if "A" in c or "B" in c],
        label_visibility="collapsed",
    )

    filtered = coe_df[coe_df["vehicle_class"].isin(selected_cats)] if selected_cats else coe_df

    fig = px.line(
        filtered, x="month", y="avg_premium", color="vehicle_class",
        labels={"avg_premium": "Premium ($)", "month": "", "vehicle_class": "Category"},
    )
    fig.update_layout(
        template="streamlit",
        height=380,
        hovermode="x unified",
        margin=dict(t=20, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No COE data available. Run the pipeline first.")

# ─── Income vs Car Cost ──────────────────────────────────────────────────────

st.markdown('<div class="section-header">Income vs Car Cost Segmentation</div>',
            unsafe_allow_html=True)

if signal:
    # Term definitions
    with st.expander("Segment Definitions", expanded=False):
        st.markdown("""
<div class="term-def"><span class="term-label">A — Affluent:</span> Car costs under 15% of household income. Financially comfortable car ownership with no stress.</div>
<div class="term-def"><span class="term-label">B — Comfortable:</span> Car costs 15–25% of income. Manageable commitment, but sensitive to rate increases.</div>
<div class="term-def"><span class="term-label">C — Stretched:</span> Car costs 25–35% of income. Significant financial burden; vulnerable to income shocks or rate hikes.</div>
<div class="term-def"><span class="term-label">D — Stressed:</span> Car costs 35–50% of income. Car ownership is a major financial strain. Risk of default if conditions worsen.</div>
<div class="term-def"><span class="term-label">E — Distressed:</span> Car costs exceed 50% of income. Unsustainable commitment. High risk of forced sale or loan default.</div>
<br>
<div class="term-def"><span class="term-label">FSI (Financial Stress Index):</span> Composite score (0–100) combining COE affordability, credit conditions, and market signals. Higher = more stress.</div>
<div class="term-def"><span class="term-label">Cost / Income Ratio:</span> Total monthly car ownership cost divided by gross monthly household income.</div>
        """, unsafe_allow_html=True)

    st.markdown("")  # spacer

    # Segment table
    segments = signal.get("segments", {})
    if segments:
        seg_data = []
        seg_order = ["A_affluent", "B_comfortable", "C_stretched", "D_stressed", "E_distressed"]
        seg_labels = {
            "A_affluent": "A — Affluent",
            "B_comfortable": "B — Comfortable",
            "C_stretched": "C — Stretched",
            "D_stressed": "D — Stressed",
            "E_distressed": "E — Distressed",
        }
        for seg_name in seg_order:
            seg_info = segments.get(seg_name)
            if not seg_info:
                continue
            seg_data.append({
                "Segment": seg_labels.get(seg_name, seg_name),
                "Stress": seg_info["stress"].title(),
                "Cost / Income": f"{seg_info['avg_cost_to_income_ratio']:.1%}",
                "Dwelling Types": ", ".join(sorted(set(seg_info["dwelling_types"]))),
            })
        st.dataframe(pd.DataFrame(seg_data), use_container_width=True, hide_index=True)

    st.markdown("")  # spacer

    # Bar chart
    income_df = load_income_segments()
    if not income_df.empty and car_costs:
        dwelling_income = income_df.groupby("dwelling_type")["median_income"].first().reset_index()
        dwelling_income = dwelling_income.sort_values("median_income")

        cat_a_cost = car_costs.get("cat_a", {}).get("monthly_total", 2400)
        cat_b_cost = car_costs.get("cat_b", {}).get("monthly_total", 3100)

        dwelling_income["Cat A"] = cat_a_cost / dwelling_income["median_income"]
        dwelling_income["Cat B"] = cat_b_cost / dwelling_income["median_income"]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Cat A", x=dwelling_income["dwelling_type"],
            y=dwelling_income["Cat A"], marker_color="#4e79a7",
        ))
        fig2.add_trace(go.Bar(
            name="Cat B", x=dwelling_income["dwelling_type"],
            y=dwelling_income["Cat B"], marker_color="#e15759",
        ))
        fig2.add_hline(y=0.35, line_dash="dash", line_color="#f28e2b",
                       annotation_text="Stressed threshold (35%)",
                       annotation_position="top left")
        fig2.add_hline(y=0.50, line_dash="dash", line_color="#e15759",
                       annotation_text="Distressed threshold (50%)",
                       annotation_position="top left")

        fig2.update_layout(
            template="streamlit",
            yaxis_title="Car Cost as % of Income",
            yaxis_tickformat=".0%",
            barmode="group",
            height=420,
            margin=dict(t=20, b=40, l=60, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ─── Town-Level Stress ───────────────────────────────────────────────────────

st.markdown('<div class="section-header">Town-Level Financial Stress</div>',
            unsafe_allow_html=True)

town_df = load_town_profiles()
if not town_df.empty:
    col_map, col_table = st.columns([3, 2])

    with col_map:
        fig3 = px.treemap(
            town_df, path=["region", "town"], values="estimated_car_households",
            color="fsi_score", color_continuous_scale="RdYlGn_r",
            range_color=[25, 50],
        )
        fig3.update_layout(
            template="streamlit",
            height=480,
            margin=dict(t=20, b=20, l=10, r=10),
            coloraxis_colorbar=dict(title="FSI", thickness=15),
        )
        fig3.update_traces(
            textinfo="label+value",
            hovertemplate="<b>%{label}</b><br>Est. Cars: %{value:,}<br>FSI: %{color:.1f}<extra></extra>",
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Size = estimated car-owning households | Color = stress level (red = higher)")

    with col_table:
        display_df = town_df[["town", "region", "median_income", "car_cost_ratio",
                               "stress_segment", "fsi_score"]].copy()
        display_df.columns = ["Town", "Region", "Income", "Ratio", "Segment", "FSI"]
        display_df["Income"] = display_df["Income"].apply(lambda x: f"${x:,.0f}")
        display_df["Ratio"] = display_df["Ratio"].apply(lambda x: f"{x:.1%}")
        display_df["FSI"] = display_df["FSI"].apply(lambda x: f"{x:.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=480)

else:
    st.info("No town data available. Run the pipeline first.")

# ─── Hire Purchase & Credit ──────────────────────────────────────────────────

st.markdown('<div class="section-header">Hire Purchase & Credit Trends</div>',
            unsafe_allow_html=True)

hp_df = load_hp_data()
if not hp_df.empty:
    hp1, hp2 = st.columns(2)

    with hp1:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            name="New HP Volume", x=hp_df["period"],
            y=hp_df["new_hp_volume"], marker_color="#4e79a7",
        ))
        fig4.add_trace(go.Scatter(
            name="Outstanding ($M)", x=hp_df["period"],
            y=hp_df["outstanding_m"], yaxis="y2",
            line=dict(color="#e15759", width=2),
        ))
        fig4.update_layout(
            template="streamlit",
            yaxis=dict(title="New HP Volume"),
            yaxis2=dict(title="Outstanding ($M)", overlaying="y", side="right"),
            height=380,
            margin=dict(t=20, b=40, l=60, r=60),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig4, use_container_width=True)

    with hp2:
        fig5 = px.line(
            hp_df, x="period", y="avg_rate",
            labels={"avg_rate": "Rate (%)", "period": ""},
        )
        fig5.update_traces(line_color="#f28e2b", line_width=2.5)
        fig5.update_layout(
            template="streamlit",
            yaxis_title="HP Interest Rate (%)",
            height=380,
            margin=dict(t=20, b=40, l=60, r=20),
        )
        st.plotly_chart(fig5, use_container_width=True)

# ─── Stress Test ─────────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Stress Test Simulator</div>',
            unsafe_allow_html=True)
st.caption("Model the impact of COE premium or interest rate changes on monthly car costs.")

st.markdown("")  # spacer

st1, st2 = st.columns(2)
coe_mult = st1.slider("COE Premium Multiplier", 0.5, 2.0, 1.0, 0.1,
                       help="1.0 = current level, 1.5 = 50% increase")
rate_add = st2.slider("Flat Rate Increase (pp)", 0.0, 3.0, 0.0, 0.25,
                       help="Additional percentage points on the advertised flat rate (not EIR)")

st.caption("Note: SG car loans use **flat rates**, not EIR. "
           "A 2.78% flat rate ≈ 5.2% EIR over 7 years. "
           "The slider adjusts the flat rate — the EIR equivalent is shown below.")

if coe_mult != 1.0 or rate_add != 0.0:
    from models.ratio_model import stress_test
    results = stress_test(coe_mult, rate_add)

    sc1, sc2 = st.columns(2)
    cat_labels = {"cat_a": "Cat A (up to 1600cc)", "cat_b": "Cat B (above 1600cc)"}
    for col_ui, r in zip([sc1, sc2], results):
        label = cat_labels.get(r["category"], r["category"])
        baseline = car_costs.get(r["category"], {}).get("monthly_total", 0)
        delta = r["stressed_monthly_cost"] - baseline
        delta_str = f"+${delta:,.0f}/mo" if delta > 0 else f"-${abs(delta):,.0f}/mo"
        col_ui.metric(label, f"${r['stressed_monthly_cost']:,.0f} / mo",
                      delta=delta_str, delta_color="inverse")
        col_ui.caption(f"Flat: {r['stressed_flat_rate']:.2%} → EIR: {r['stressed_eir']:.2%}")
else:
    st.info("Adjust the sliders above to run a stress scenario.")

# ─── Car Cost Calculator ─────────────────────────────────────────────────────

st.markdown('<div class="section-header">Car Cost Calculator</div>',
            unsafe_allow_html=True)
st.caption("Estimate your total cost of car ownership in Singapore. All inputs use flat rates as quoted by dealers.")

st.markdown("")  # spacer

from models.ratio_model import flat_to_eir

calc1, calc2, calc3 = st.columns(3)

with calc1:
    vehicle_price = st.number_input("Vehicle Price (OMV + dealer)", min_value=30000, max_value=500000,
                                     value=80000, step=5000, format="%d",
                                     help="Open Market Value + dealer markup, before COE")
    coe_premium = st.number_input("COE Premium", min_value=0, max_value=300000,
                                   value=100000, step=5000, format="%d")
    arf_pct = st.slider("ARF (% of OMV)", 100, 220, 100, 10,
                         help="Additional Registration Fee. 100% for first $20k OMV, tiered above that. Use 100% as default estimate.")

with calc2:
    downpayment_pct = st.slider("Downpayment (%)", 30, 100, 40, 5,
                                 help="Minimum 30% for cars in SG (MAS regulation since 2016)")
    loan_tenure = st.selectbox("Loan Tenure", [5, 6, 7], index=2,
                                help="Maximum 7 years in SG",
                                format_func=lambda x: f"{x} years")
    flat_rate = st.number_input("Flat Rate (% p.a.)", min_value=0.0, max_value=10.0,
                                 value=2.78, step=0.1, format="%.2f",
                                 help="Advertised flat rate from dealer/bank. NOT the effective interest rate (EIR).")

with calc3:
    insurance = st.number_input("Insurance ($/yr)", min_value=0, max_value=10000,
                                 value=1800, step=100, format="%d")
    road_tax = st.number_input("Road Tax ($/yr)", min_value=0, max_value=5000,
                                value=742, step=50, format="%d")
    petrol = st.number_input("Petrol ($/mo)", min_value=0, max_value=1500,
                              value=300, step=25, format="%d")
    parking = st.number_input("Parking ($/mo)", min_value=0, max_value=1000,
                               value=110, step=10, format="%d",
                               help="HDB season parking ~$110, condo ~$0 (included), CBD ~$300+")
    maintenance = st.number_input("Maintenance ($/mo)", min_value=0, max_value=1000,
                                   value=150, step=25, format="%d",
                                   help="Servicing, tyres, repairs averaged monthly")

st.markdown("")  # spacer

# Calculate
arf = vehicle_price * (arf_pct / 100)
total_vehicle_cost = vehicle_price + coe_premium + arf
loan_amount = total_vehicle_cost * (1 - downpayment_pct / 100)
downpayment_amount = total_vehicle_cost * (downpayment_pct / 100)
tenure_months = loan_tenure * 12
flat_rate_decimal = flat_rate / 100

# Flat rate loan calculation
total_interest = loan_amount * flat_rate_decimal * loan_tenure
monthly_loan = (loan_amount + total_interest) / tenure_months
eir = flat_to_eir(flat_rate_decimal, loan_tenure)

monthly_insurance = insurance / 12
monthly_road_tax = road_tax / 12
monthly_total = monthly_loan + monthly_insurance + monthly_road_tax + petrol + parking + maintenance

# 10-year total cost (loan period + 3 years of running costs only)
total_loan_period_cost = (monthly_total * tenure_months) + downpayment_amount
running_cost_monthly = monthly_insurance + monthly_road_tax + petrol + parking + maintenance
remaining_months = max(0, 120 - tenure_months)  # rest of 10-year COE
total_10yr = total_loan_period_cost + (running_cost_monthly * remaining_months)

# Display results
st.markdown('<div class="section-header">Cost Breakdown</div>', unsafe_allow_html=True)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Total Vehicle Cost", f"${total_vehicle_cost:,.0f}",
          delta=f"Downpayment: ${downpayment_amount:,.0f}")
r2.metric("Monthly Repayment", f"${monthly_loan:,.0f}",
          delta=f"Flat {flat_rate:.2f}% → EIR {eir:.2%}")
r3.metric("Total Monthly Cost", f"${monthly_total:,.0f}",
          delta=f"${monthly_total * 12:,.0f} / year")
r4.metric("10-Year Total Cost", f"${total_10yr:,.0f}",
          delta=f"${total_10yr / 120:,.0f} / month avg")

st.markdown("")  # spacer

# Detailed breakdown table
breakdown_data = {
    "Component": ["Loan Repayment", "Insurance", "Road Tax", "Petrol", "Parking",
                   "Maintenance", "**Total**"],
    "Monthly": [f"${monthly_loan:,.0f}", f"${monthly_insurance:,.0f}", f"${monthly_road_tax:,.0f}",
                f"${petrol:,.0f}", f"${parking:,.0f}", f"${maintenance:,.0f}",
                f"**${monthly_total:,.0f}**"],
    "Annual": [f"${monthly_loan * 12:,.0f}", f"${insurance:,.0f}", f"${road_tax:,.0f}",
               f"${petrol * 12:,.0f}", f"${parking * 12:,.0f}", f"${maintenance * 12:,.0f}",
               f"**${monthly_total * 12:,.0f}**"],
    "% of Total": [f"{monthly_loan / monthly_total:.0%}", f"{monthly_insurance / monthly_total:.0%}",
                    f"{monthly_road_tax / monthly_total:.0%}", f"{petrol / monthly_total:.0%}",
                    f"{parking / monthly_total:.0%}", f"{maintenance / monthly_total:.0%}",
                    "**100%**"],
}
st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)

st.markdown("")  # spacer

# Affordability check
st.markdown('<div class="section-header">Affordability Check</div>', unsafe_allow_html=True)
st.caption("Enter your household income to see where you fall on the stress scale.")

income_input = st.number_input("Gross Monthly Household Income ($)", min_value=1000,
                                max_value=100000, value=8000, step=500, format="%d")

income_ratio = monthly_total / income_input
if income_ratio < 0.15:
    seg_label, seg_color = "A — Affluent", "green"
elif income_ratio < 0.25:
    seg_label, seg_color = "B — Comfortable", "green"
elif income_ratio < 0.35:
    seg_label, seg_color = "C — Stretched", "yellow"
elif income_ratio < 0.50:
    seg_label, seg_color = "D — Stressed", "red"
else:
    seg_label, seg_color = "E — Distressed", "red"

af1, af2, af3 = st.columns(3)
with af1:
    st.markdown(f'<div class="metric-{seg_color}">', unsafe_allow_html=True)
    st.metric("Your Segment", seg_label)
    st.markdown('</div>', unsafe_allow_html=True)
af2.metric("Cost / Income Ratio", f"{income_ratio:.1%}",
           delta="Healthy" if income_ratio < 0.25 else "Stretched" if income_ratio < 0.35 else "Unsustainable")
af3.metric("Remaining After Car", f"${income_input - monthly_total:,.0f} / mo",
           delta=f"{1 - income_ratio:.0%} of income")

# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown("")  # spacer
st.divider()
st.caption("SG Car Ownership Financial Profiling | Data: LTA, DOS, HDB, MAS, CPF, URA | "
           "Run `python3 run_pipeline.py` to refresh data")
