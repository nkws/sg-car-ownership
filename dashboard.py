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
    /* Section spacing — uses Streamlit theme variables that auto-switch */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid var(--secondary-background-color);
        color: var(--text-color);
    }
    /* Metric cards — Streamlit variables adapt to light/dark automatically */
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 8px;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-color) !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-color) !important;
    }
    /* Color-coded metric cards — rgba tints work on any background */
    .metric-green [data-testid="stMetric"] {
        border-left: 4px solid #4caf50;
        background: rgba(76, 175, 80, 0.15);
    }
    .metric-yellow [data-testid="stMetric"] {
        border-left: 4px solid #ffca28;
        background: rgba(255, 202, 40, 0.15);
    }
    .metric-red [data-testid="stMetric"] {
        border-left: 4px solid #ef5350;
        background: rgba(239, 83, 80, 0.15);
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

def run_pipeline_refresh():
    """Run the full data pipeline and clear caches."""
    from run_pipeline import main as run_pipeline
    run_pipeline()
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def load_signal():
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    return None

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=3600)
def load_town_profiles():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM town_profile ORDER BY fsi_score DESC").fetchall()
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=3600)
def load_income_segments():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT dwelling_type, median_income, income_bracket, percentage
            FROM household_income
            ORDER BY median_income
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=3600)
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

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown("## SG Car Ownership")
    st.markdown("**Financial Stress Dashboard**")
with col_refresh:
    st.markdown("")  # vertical align
    if st.button("Refresh Data", help="Run the data pipeline to fetch latest data from LTA, DOS, MAS, etc."):
        with st.spinner("Running data pipeline..."):
            run_pipeline_refresh()
        st.rerun()

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
                       help="1.0 = current level, 1.5 = 50% increase",
                       key="calc_coe_mult")
rate_add = st2.slider("Flat Rate Increase (pp)", 0.0, 3.0, 0.0, 0.25,
                       help="Additional percentage points on the advertised flat rate (not EIR)",
                       key="calc_rate_add")

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

# Default values for calculator
CALC_DEFAULTS = {
    "calc_vehicle_price": 80000, "calc_coe_premium": 100000, "calc_arf_pct": 100,
    "calc_downpayment_pct": 40, "calc_loan_tenure": 2, "calc_flat_rate": 2.78,
    "calc_insurance": 1800, "calc_road_tax": 742, "calc_petrol": 300,
    "calc_parking": 110, "calc_maintenance": 150, "calc_income": 8000,
    "calc_coe_mult": 1.0, "calc_rate_add": 0.0,
}

def reset_calculator():
    for key, val in CALC_DEFAULTS.items():
        st.session_state[key] = val

col_calc_title, col_calc_reset = st.columns([6, 1])
with col_calc_title:
    pass
with col_calc_reset:
    st.button("Reset to Defaults", on_click=reset_calculator, key="reset_calc_btn")

calc1, calc2, calc3 = st.columns(3)

with calc1:
    vehicle_price = st.number_input("Vehicle Price (OMV + dealer)", min_value=30000, max_value=500000,
                                     value=80000, step=5000, format="%d",
                                     help="Open Market Value + dealer markup, before COE",
                                     key="calc_vehicle_price")
    coe_premium = st.number_input("COE Premium", min_value=0, max_value=300000,
                                   value=100000, step=5000, format="%d",
                                   key="calc_coe_premium")
    arf_pct = st.slider("ARF (% of OMV)", 100, 220, 100, 10,
                         help="Additional Registration Fee. 100% for first $20k OMV, tiered above that. Use 100% as default estimate.",
                         key="calc_arf_pct")

with calc2:
    downpayment_pct = st.slider("Downpayment (%)", 30, 100, 40, 5,
                                 help="Minimum 30% for cars in SG (MAS regulation since 2016)",
                                 key="calc_downpayment_pct")
    loan_tenure = st.selectbox("Loan Tenure", [5, 6, 7], index=2,
                                help="Maximum 7 years in SG",
                                format_func=lambda x: f"{x} years",
                                key="calc_loan_tenure")
    flat_rate = st.number_input("Flat Rate (% p.a.)", min_value=0.0, max_value=10.0,
                                 value=2.78, step=0.1, format="%.2f",
                                 help="Advertised flat rate from dealer/bank. NOT the effective interest rate (EIR).",
                                 key="calc_flat_rate")

with calc3:
    insurance = st.number_input("Insurance ($/yr)", min_value=0, max_value=10000,
                                 value=1800, step=100, format="%d",
                                 key="calc_insurance")
    road_tax = st.number_input("Road Tax ($/yr)", min_value=0, max_value=5000,
                                value=742, step=50, format="%d",
                                key="calc_road_tax")
    petrol = st.number_input("Petrol ($/mo)", min_value=0, max_value=1500,
                              value=300, step=25, format="%d",
                              key="calc_petrol")
    parking = st.number_input("Parking ($/mo)", min_value=0, max_value=1000,
                               value=110, step=10, format="%d",
                               help="HDB season parking ~$110, condo ~$0 (included), CBD ~$300+",
                               key="calc_parking")
    maintenance = st.number_input("Maintenance ($/mo)", min_value=0, max_value=1000,
                                   value=150, step=25, format="%d",
                                   help="Servicing, tyres, repairs averaged monthly",
                                   key="calc_maintenance")

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
                                max_value=100000, value=8000, step=500, format="%d",
                                key="calc_income")

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

# ─── 10-Year Total Cost Waterfall ────────────────────────────────────────────

st.markdown('<div class="section-header">10-Year Cost of Ownership Waterfall</div>',
            unsafe_allow_html=True)
st.caption("Cumulative cost breakdown over the full 10-year COE cycle, based on your calculator inputs above.")

# Use calculator values already computed above
depreciation = total_vehicle_cost  # car is worth $0 at end of 10-year COE
total_loan_payments = monthly_loan * tenure_months
total_interest_paid = total_interest
total_insurance_10yr = insurance * 10
total_road_tax_10yr = road_tax * 10
total_petrol_10yr = petrol * 12 * 10
total_parking_10yr = parking * 12 * 10

# Maintenance: $0 during years 1-3 (warranty + free servicing),
# then gradually increasing from year 4 as the car ages.
# Multipliers sum to 10.0 so total ≈ same as 10 years of flat base rate.
maint_multipliers = {
    1: 0.0, 2: 0.0, 3: 0.0,       # warranty + free servicing
    4: 0.8, 5: 1.0, 6: 1.2,       # post-warranty ramp-up
    7: 1.4, 8: 1.6, 9: 1.8,       # aging wear parts
    10: 2.2,                        # final year
}
maint_yr1_3 = sum(maintenance * maint_multipliers[y] * 12 for y in range(1, 4))   # $0
maint_yr4_10 = sum(maintenance * maint_multipliers[y] * 12 for y in range(4, 11))
total_maintenance_10yr = maint_yr1_3 + maint_yr4_10

waterfall_items = [
    ("Vehicle + COE + ARF", total_vehicle_cost, "#4e79a7"),
    ("Loan Interest", total_interest_paid, "#76b7b2"),
    ("Insurance (10yr)", total_insurance_10yr, "#59a14f"),
    ("Road Tax (10yr)", total_road_tax_10yr, "#edc949"),
    ("Petrol (10yr)", total_petrol_10yr, "#f28e2b"),
    ("Parking (10yr)", total_parking_10yr, "#e15759"),
    ("Maint (Yr 1-3 warranty)", maint_yr1_3, "#b07aa1"),
    ("Maint (Yr 4-10 post-warranty)", maint_yr4_10, "#ff9da7"),
]

grand_total = sum(v for _, v, _ in waterfall_items)

fig_wf = go.Figure(go.Waterfall(
    x=[name for name, _, _ in waterfall_items] + ["TOTAL (10yr)"],
    y=[val for _, val, _ in waterfall_items] + [0],
    measure=["relative"] * len(waterfall_items) + ["total"],
    text=[f"${v:,.0f}" for _, v, _ in waterfall_items] + [f"${grand_total:,.0f}"],
    textposition="outside",
    connector=dict(line=dict(color="rgba(128,128,128,0.3)")),
    increasing=dict(marker=dict(color="#4e79a7")),
    totals=dict(marker=dict(color="#e15759")),
))
fig_wf.update_layout(
    template="streamlit",
    height=420,
    margin=dict(t=20, b=60, l=60, r=20),
    yaxis_title="Cumulative Cost ($)",
    showlegend=False,
)
st.plotly_chart(fig_wf, use_container_width=True)

wf_top1, wf_top2, wf_top3 = st.columns(3)
wf_top1.metric("10-Year Grand Total", f"${grand_total:,.0f}")
wf_top2.metric("Effective Monthly Cost", f"${grand_total / 120:,.0f}",
               delta=f"${grand_total / 120 / 30:,.0f} / day")
wf_top3.metric("Vehicle Depreciation", f"${total_vehicle_cost:,.0f}",
               delta=f"{total_vehicle_cost / grand_total:.0%} of total cost")

# Year-by-year maintenance breakdown
maint_yearly = [{"Year": y, "Annual Cost": maintenance * maint_multipliers[y] * 12,
                 "Phase": "Warranty" if y <= 3 else "Post-Warranty"}
                for y in range(1, 11)]
maint_yr_df = pd.DataFrame(maint_yearly)

wf_m1, wf_m2 = st.columns([3, 2])
with wf_m1:
    fig_maint = go.Figure(go.Bar(
        x=maint_yr_df["Year"], y=maint_yr_df["Annual Cost"],
        marker_color=["#b07aa1" if y <= 3 else "#ff9da7" for y in range(1, 11)],
        text=[f"${v:,.0f}" for v in maint_yr_df["Annual Cost"]],
        textposition="outside",
    ))
    fig_maint.update_layout(
        template="streamlit", height=300,
        xaxis=dict(title="Year", dtick=1),
        yaxis_title="Maintenance Cost ($)",
        margin=dict(t=20, b=40, l=60, r=20),
        showlegend=False,
    )
    st.plotly_chart(fig_maint, use_container_width=True)
with wf_m2:
    st.caption("**Maintenance cost profile**")
    st.caption("Years 1-3: $0 — covered by manufacturer warranty and free servicing package.")
    st.caption(f"Years 4-10: Gradual increase from "
               f"${maintenance * maint_multipliers[4] * 12:,.0f}/yr to "
               f"${maintenance * maint_multipliers[10] * 12:,.0f}/yr as wear parts, "
               f"battery, suspension, and electronics age.")
    st.metric("Total Maintenance (10yr)", f"${total_maintenance_10yr:,.0f}")

# ─── Affordability Cliff Analysis ────────────────────────────────────────────

st.markdown('<div class="section-header">Affordability Cliff Analysis</div>',
            unsafe_allow_html=True)
st.caption("At what COE level does each dwelling type tip into a worse stress segment? "
           "Shows the breaking points where car ownership becomes unaffordable.")

if signal and car_costs:
    from models.ratio_model import calculate_monthly_car_cost

    income_df_cliff = load_income_segments()
    if not income_df_cliff.empty:
        dwelling_incomes = income_df_cliff.groupby("dwelling_type")["median_income"].first()
        dwelling_incomes = dwelling_incomes[dwelling_incomes > 0].sort_values()

        # Test COE range from 50k to 200k
        coe_range = list(range(50000, 205000, 5000))
        cliff_data = []

        for dwelling, income in dwelling_incomes.items():
            for coe_val in coe_range:
                cost = calculate_monthly_car_cost("cat_a", coe_override=coe_val)
                ratio = cost["monthly_total"] / income
                cliff_data.append({
                    "Dwelling Type": dwelling,
                    "COE Premium": coe_val,
                    "Monthly Cost": cost["monthly_total"],
                    "Cost/Income Ratio": ratio,
                    "Income": income,
                })

        cliff_df = pd.DataFrame(cliff_data)

        fig_cliff = go.Figure()
        colors = ["#4e79a7", "#59a14f", "#76b7b2", "#f28e2b", "#e15759", "#b07aa1"]
        for i, dwelling in enumerate(dwelling_incomes.index):
            dw_data = cliff_df[cliff_df["Dwelling Type"] == dwelling]
            fig_cliff.add_trace(go.Scatter(
                x=dw_data["COE Premium"], y=dw_data["Cost/Income Ratio"],
                name=dwelling, mode="lines",
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate=(
                    f"<b>{dwelling}</b><br>"
                    "COE: $%{x:,.0f}<br>"
                    "Ratio: %{y:.0%}<br>"
                    "<extra></extra>"
                ),
            ))

        # Threshold lines
        fig_cliff.add_hline(y=0.25, line_dash="dot", line_color="gray",
                            annotation_text="Stretched (25%)", annotation_position="top left")
        fig_cliff.add_hline(y=0.35, line_dash="dash", line_color="#f28e2b",
                            annotation_text="Stressed (35%)", annotation_position="top left")
        fig_cliff.add_hline(y=0.50, line_dash="dash", line_color="#e15759",
                            annotation_text="Distressed (50%)", annotation_position="top left")

        fig_cliff.update_layout(
            template="streamlit",
            height=450,
            xaxis_title="COE Premium ($)",
            yaxis_title="Car Cost as % of Income",
            yaxis_tickformat=".0%",
            hovermode="x unified",
            margin=dict(t=20, b=40, l=60, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig_cliff, use_container_width=True)

        # Show cliff points table
        st.markdown("**Breaking points** — COE level where each dwelling type crosses thresholds:")
        cliff_table = []
        thresholds = [("Stretched (25%)", 0.25), ("Stressed (35%)", 0.35), ("Distressed (50%)", 0.50)]
        for dwelling, income in dwelling_incomes.items():
            row = {"Dwelling Type": dwelling, "Median Income": f"${income:,.0f}"}
            dw_data = cliff_df[cliff_df["Dwelling Type"] == dwelling].sort_values("COE Premium")
            for label, thresh in thresholds:
                crossing = dw_data[dw_data["Cost/Income Ratio"] >= thresh]
                if not crossing.empty:
                    row[label] = f"${crossing.iloc[0]['COE Premium']:,.0f}"
                else:
                    row[label] = "Above $200k"
            cliff_table.append(row)
        st.dataframe(pd.DataFrame(cliff_table), use_container_width=True, hide_index=True)

# ─── Forced-Sale / Default Risk Proxy ────────────────────────────────────────

st.markdown('<div class="section-header">Forced-Sale / Default Risk Proxy</div>',
            unsafe_allow_html=True)
st.caption("When HP outstanding rises but new HP volume falls, existing borrowers may be "
           "struggling while new buyers are priced out — a leading indicator of distressed car sales.")

hp_df_risk = load_hp_data()
if not hp_df_risk.empty and len(hp_df_risk) >= 4:
    hp_df_risk = hp_df_risk.sort_values(["year", "quarter"]).reset_index(drop=True)

    # Calculate quarter-over-quarter changes
    hp_df_risk["vol_change"] = hp_df_risk["new_hp_volume"].pct_change()
    hp_df_risk["outstanding_change"] = hp_df_risk["outstanding_m"].pct_change()

    # Risk signal: outstanding growing while volume shrinking
    hp_df_risk["risk_signal"] = (
        (hp_df_risk["outstanding_change"] > 0) & (hp_df_risk["vol_change"] < 0)
    ).astype(int)

    # Divergence metric (positive = risk divergence)
    hp_df_risk["divergence"] = hp_df_risk["outstanding_change"] - hp_df_risk["vol_change"]

    fig_risk = go.Figure()

    # Volume change bars
    colors_vol = ["#e15759" if v < 0 else "#59a14f" for v in hp_df_risk["vol_change"].fillna(0)]
    fig_risk.add_trace(go.Bar(
        name="New HP Volume Change",
        x=hp_df_risk["period"], y=hp_df_risk["vol_change"],
        marker_color=colors_vol,
        yaxis="y",
    ))

    # Outstanding change line
    fig_risk.add_trace(go.Scatter(
        name="Outstanding HP Change",
        x=hp_df_risk["period"], y=hp_df_risk["outstanding_change"],
        line=dict(color="#4e79a7", width=2.5),
        yaxis="y",
    ))

    # Risk markers
    risk_periods = hp_df_risk[hp_df_risk["risk_signal"] == 1]
    if not risk_periods.empty:
        fig_risk.add_trace(go.Scatter(
            name="Risk Signal",
            x=risk_periods["period"], y=risk_periods["outstanding_change"],
            mode="markers",
            marker=dict(color="#e15759", size=12, symbol="triangle-up",
                        line=dict(width=1, color="white")),
        ))

    fig_risk.update_layout(
        template="streamlit",
        height=380,
        yaxis=dict(title="Quarter-over-Quarter Change", tickformat=".0%"),
        margin=dict(t=20, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig_risk, use_container_width=True)

    # Summary metrics
    latest = hp_df_risk.iloc[-1]
    dr1, dr2, dr3 = st.columns(3)
    dr1.metric("Latest HP Volume Trend",
               f"{latest['vol_change']:+.1%}" if pd.notna(latest['vol_change']) else "N/A")
    dr2.metric("Outstanding HP Trend",
               f"{latest['outstanding_change']:+.1%}" if pd.notna(latest['outstanding_change']) else "N/A")
    risk_count = int(hp_df_risk["risk_signal"].sum())
    dr3.metric("Risk Signals (total)", f"{risk_count} / {len(hp_df_risk)}",
               delta="Divergence detected" if latest.get("risk_signal", 0) == 1 else "No current divergence")
else:
    st.info("Insufficient hire purchase data for risk analysis.")

# ─── Real Income Erosion Over Time ───────────────────────────────────────────

st.markdown('<div class="section-header">Real Income Erosion — COE Growth vs Wage Growth</div>',
            unsafe_allow_html=True)
st.caption("Compares COE premium growth against wage growth. A widening gap means car ownership "
           "is becoming structurally less affordable over time, regardless of current levels.")

coe_erosion_df = load_coe_history()
if not coe_erosion_df.empty:
    # Annual average COE premium (Cat A)
    coe_annual = coe_erosion_df[coe_erosion_df["vehicle_class"] == "Category A"].copy()
    coe_annual["year"] = coe_annual["month"].str[:4].astype(int)
    coe_yearly = coe_annual.groupby("year")["avg_premium"].mean().reset_index()
    coe_yearly.columns = ["year", "avg_coe"]

    # Wage data: CPF median wage proxy + vehicle population for normalisation
    # Use hardcoded SG median wage trend (DOS data)
    wage_trend = pd.DataFrame({
        "year": [2020, 2021, 2022, 2023, 2024],
        "median_wage": [4534, 4680, 5070, 5197, 5500],  # DOS median gross monthly income
    })

    # Merge and index to first available year
    erosion = coe_yearly.merge(wage_trend, on="year", how="inner")
    if len(erosion) >= 2:
        base_coe = erosion.iloc[0]["avg_coe"]
        base_wage = erosion.iloc[0]["median_wage"]
        erosion["coe_index"] = (erosion["avg_coe"] / base_coe) * 100
        erosion["wage_index"] = (erosion["median_wage"] / base_wage) * 100
        erosion["gap"] = erosion["coe_index"] - erosion["wage_index"]

        fig_erosion = go.Figure()
        fig_erosion.add_trace(go.Scatter(
            name="COE Premium (Cat A)", x=erosion["year"], y=erosion["coe_index"],
            line=dict(color="#e15759", width=2.5),
            fill="tonexty" if len(erosion) > 2 else None,
        ))
        fig_erosion.add_trace(go.Scatter(
            name="Median Wage", x=erosion["year"], y=erosion["wage_index"],
            line=dict(color="#4e79a7", width=2.5),
        ))
        fig_erosion.add_trace(go.Bar(
            name="Affordability Gap", x=erosion["year"], y=erosion["gap"],
            marker_color="rgba(225, 87, 89, 0.3)",
            yaxis="y2",
        ))

        fig_erosion.update_layout(
            template="streamlit",
            height=400,
            yaxis=dict(title="Index (base year = 100)"),
            yaxis2=dict(title="Gap (index pts)", overlaying="y", side="right"),
            margin=dict(t=20, b=40, l=60, r=60),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_erosion, use_container_width=True)

        # Summary
        latest_gap = erosion.iloc[-1]
        coe_cagr = ((erosion.iloc[-1]["avg_coe"] / base_coe) ** (1 / max(len(erosion) - 1, 1)) - 1)
        wage_cagr = ((erosion.iloc[-1]["median_wage"] / base_wage) ** (1 / max(len(erosion) - 1, 1)) - 1)

        er1, er2, er3 = st.columns(3)
        er1.metric("COE CAGR", f"{coe_cagr:.1%}", delta=f"Since {int(erosion.iloc[0]['year'])}")
        er2.metric("Wage CAGR", f"{wage_cagr:.1%}", delta=f"Since {int(erosion.iloc[0]['year'])}")
        er3.metric("Erosion Rate", f"{coe_cagr - wage_cagr:+.1%} p.a.",
                   delta="COE outpacing wages" if coe_cagr > wage_cagr else "Wages catching up")
    else:
        st.info("Need at least 2 years of overlapping COE and wage data.")
else:
    st.info("No COE history data available.")

# ─── Regional Inequality Score ───────────────────────────────────────────────

st.markdown('<div class="section-header">Regional Inequality — Car Ownership Burden</div>',
            unsafe_allow_html=True)
st.caption("Measures how unevenly the financial burden of car ownership falls across towns. "
           "A higher Gini coefficient means greater inequality.")

town_df_ineq = load_town_profiles()
if not town_df_ineq.empty and "car_cost_ratio" in town_df_ineq.columns:
    ratios = town_df_ineq["car_cost_ratio"].dropna().sort_values().values

    # Calculate Gini coefficient
    n = len(ratios)
    if n >= 2:
        cumulative = ratios.cumsum()
        gini = (2 * sum((i + 1) * ratios[i] for i in range(n)) - (n + 1) * ratios.sum()) / (n * ratios.sum())
        gini = round(abs(gini), 3)

        # Lorenz curve data
        lorenz_x = [0] + [(i + 1) / n for i in range(n)]
        lorenz_y = [0] + list(cumulative / cumulative[-1])

        gi1, gi2 = st.columns([3, 2])

        with gi1:
            fig_lorenz = go.Figure()
            fig_lorenz.add_trace(go.Scatter(
                x=lorenz_x, y=lorenz_y, name="Actual Distribution",
                fill="toself", fillcolor="rgba(78, 121, 167, 0.2)",
                line=dict(color="#4e79a7", width=2),
            ))
            fig_lorenz.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1], name="Perfect Equality",
                line=dict(color="gray", width=1, dash="dash"),
            ))
            fig_lorenz.update_layout(
                template="streamlit",
                height=380,
                xaxis_title="Cumulative Share of Towns",
                yaxis_title="Cumulative Share of Cost/Income Burden",
                margin=dict(t=20, b=40, l=60, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            )
            st.plotly_chart(fig_lorenz, use_container_width=True)

        with gi2:
            st.metric("Gini Coefficient", f"{gini:.3f}",
                      delta="Higher = more unequal")

            # Range stats
            st.metric("Most Affordable Town",
                      town_df_ineq.loc[town_df_ineq["car_cost_ratio"].idxmin(), "town"],
                      delta=f"Ratio: {ratios[0]:.1%}")
            st.metric("Least Affordable Town",
                      town_df_ineq.loc[town_df_ineq["car_cost_ratio"].idxmax(), "town"],
                      delta=f"Ratio: {ratios[-1]:.1%}")

            spread = ratios[-1] / max(ratios[0], 0.01)
            st.metric("Spread (max / min)", f"{spread:.1f}x",
                      delta=f"{ratios[-1]:.0%} vs {ratios[0]:.0%}")
    else:
        st.info("Need at least 2 towns for inequality analysis.")
else:
    st.info("No town profile data available.")

# ─── Own vs Ride-Hail Break-Even ─────────────────────────────────────────────

st.markdown('<div class="section-header">Own vs Ride-Hail Break-Even</div>',
            unsafe_allow_html=True)
st.caption("At what monthly ride-hail spend does owning a car become cheaper? "
           "Based on your calculator inputs above.")

# Average ride-hail cost assumptions for SG
ride_cost_per_trip = st.slider(
    "Average ride-hail cost per trip ($)", 10.0, 30.0, 15.0, 1.0,
    help="Average Grab/taxi fare for a typical trip in Singapore"
)

# Monthly car cost already calculated: monthly_total
# Break-even: monthly_total / ride_cost_per_trip = trips per month
breakeven_trips = monthly_total / ride_cost_per_trip
breakeven_daily = breakeven_trips / 30

# Generate comparison data
trips_range = list(range(0, 201, 5))
comparison_data = []
for trips in trips_range:
    ride_cost = trips * ride_cost_per_trip
    comparison_data.append({
        "Trips / Month": trips,
        "Ride-Hail Cost": ride_cost,
        "Car Ownership Cost": monthly_total,
    })
comp_df = pd.DataFrame(comparison_data)

rh1, rh2 = st.columns([3, 2])

with rh1:
    fig_rh = go.Figure()
    fig_rh.add_trace(go.Scatter(
        x=comp_df["Trips / Month"], y=comp_df["Ride-Hail Cost"],
        name="Ride-Hail (Grab/Taxi)", line=dict(color="#59a14f", width=2.5),
    ))
    fig_rh.add_trace(go.Scatter(
        x=comp_df["Trips / Month"], y=comp_df["Car Ownership Cost"],
        name="Car Ownership", line=dict(color="#e15759", width=2.5),
    ))
    fig_rh.add_vline(x=breakeven_trips, line_dash="dash", line_color="#f28e2b",
                     annotation_text=f"Break-even: {breakeven_trips:.0f} trips/mo",
                     annotation_position="top left")
    fig_rh.update_layout(
        template="streamlit",
        height=380,
        xaxis_title="Trips per Month",
        yaxis_title="Monthly Cost ($)",
        margin=dict(t=20, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig_rh, use_container_width=True)

with rh2:
    st.metric("Break-Even Point", f"{breakeven_trips:.0f} trips / month",
              delta=f"~{breakeven_daily:.1f} trips / day")
    st.metric("Your Car Cost", f"${monthly_total:,.0f} / mo")
    st.metric("Equivalent Ride-Hail", f"{breakeven_trips:.0f} × ${ride_cost_per_trip:.0f}",
              delta=f"= ${breakeven_trips * ride_cost_per_trip:,.0f}/mo")

    if breakeven_daily > 4:
        st.success("Ride-hail is likely more cost-effective for most people.")
    elif breakeven_daily > 2:
        st.warning("Car ownership is only cheaper if you drive frequently (3-4+ trips/day).")
    else:
        st.info("Car ownership is competitive at typical usage levels.")

# ─── FSI Weight Backtester ───────────────────────────────────────────────────

st.markdown('<div class="section-header">FSI Weight Backtester</div>',
            unsafe_allow_html=True)
st.caption("Tests all weight combinations against historical stress periods to find "
           "the most predictive composite. Stress months are identified by premiums "
           "exceeding 1 standard deviation above rolling mean.")

@st.cache_data(ttl=600)
def run_backtest():
    from models.fsi_backtest import backtest_weights
    return backtest_weights(step=5)

backtest = run_backtest()

if backtest.get("message"):
    st.info(backtest["message"])
else:
    opt_w = backtest["optimal_weights"]
    def_w = backtest["default_weights"]

    bt1, bt2, bt3, bt4 = st.columns(4)
    bt1.metric("Optimal COE Weight", f"{opt_w['coe']:.0%}",
               delta=f"vs default {def_w['coe']:.0%}")
    bt2.metric("Optimal Credit Weight", f"{opt_w['credit']:.0%}",
               delta=f"vs default {def_w['credit']:.0%}")
    bt3.metric("Optimal Market Weight", f"{opt_w['market']:.0%}",
               delta=f"vs default {def_w['market']:.0%}")
    bt4.metric("Separation Improvement", f"{backtest['improvement_pct']:+.1f}%",
               delta=f"Gap: {backtest['optimal_gap']:.1f} vs {backtest['default_gap']:.1f}")

    # Chart: FSI over time with optimal vs default weights
    score_hist = backtest.get("score_history")
    if score_hist is not None and not score_hist.empty:
        bt_chart, bt_table = st.columns([3, 2])

        with bt_chart:
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=score_hist["month"], y=score_hist["fsi_optimal"],
                name=f"Optimal ({opt_w['coe']:.0%}/{opt_w['credit']:.0%}/{opt_w['market']:.0%})",
                line=dict(color="#4e79a7", width=2),
            ))
            fig_bt.add_trace(go.Scatter(
                x=score_hist["month"], y=score_hist["fsi_default"],
                name="Default (40/30/30)",
                line=dict(color="gray", width=1.5, dash="dot"),
            ))
            # Shade stress periods
            stress_months_bt = score_hist[score_hist["is_stress"] == 1]
            if not stress_months_bt.empty:
                fig_bt.add_trace(go.Scatter(
                    x=stress_months_bt["month"], y=stress_months_bt["fsi_optimal"],
                    name="Stress Period", mode="markers",
                    marker=dict(color="#e15759", size=8, symbol="diamond"),
                ))

            fig_bt.update_layout(
                template="streamlit",
                height=380,
                yaxis_title="FSI Score",
                margin=dict(t=20, b=40, l=60, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                hovermode="x unified",
            )
            st.plotly_chart(fig_bt, use_container_width=True)

        with bt_table:
            st.markdown("**Top 5 Weight Combinations**")
            top5 = backtest.get("top_5", [])
            if top5:
                top5_df = pd.DataFrame(top5)
                top5_df.columns = ["COE", "Credit", "Market", "Stress FSI", "Calm FSI", "Gap"]
                top5_df["COE"] = top5_df["COE"].apply(lambda x: f"{x:.0%}")
                top5_df["Credit"] = top5_df["Credit"].apply(lambda x: f"{x:.0%}")
                top5_df["Market"] = top5_df["Market"].apply(lambda x: f"{x:.0%}")
                st.dataframe(top5_df, use_container_width=True, hide_index=True)

            st.caption(f"Tested {backtest['total_months']} months: "
                       f"{backtest['stress_count']} stress, {backtest['calm_count']} calm")

# ─── COE Market Analysis ────────────────────────────────────────────────────

from analysis.coe_market import render as render_coe_analysis
render_coe_analysis()

# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown("")  # spacer
st.divider()
st.caption("SG Car Ownership Financial Profiling | Data: LTA, DOS, HDB, MAS, CPF, URA | "
           "Run `python3 run_pipeline.py` to refresh data")
