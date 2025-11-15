import streamlit as st
import pandas as pd

from qra.state import QRAStateEngine, QRAStateConfig
from qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp


st.set_page_config(
    page_title="Revuity QRA Console",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --revuity-green: #004A2C;
        --revuity-orange: #F56E0B;
        --revuity-cream: #F4E7D9;
        --revuity-text: #111827;
    }

    html, body, .stApp {
        background-color: var(--revuity-cream);
        color: var(--revuity-text);
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2 {
        font-family: 'Montserrat', sans-serif;
        color: var(--revuity-green);
    }

    div[data-testid="stSidebar"] {
        background-color: #fff;
        border-right: 1px solid rgba(0, 0, 0, 0.05);
    }

    .stButton>button {
        background-color: var(--revuity-orange);
        color: #fff;
        border: none;
        border-radius: 999px;
        font-weight: 600;
    }

    .stButton>button:hover {
        background-color: #d95f09;
        color: #fff;
    }

    .stDownloadButton>button {
        border-color: var(--revuity-green);
        color: var(--revuity-green);
    }

    .stDownloadButton>button:hover {
        background-color: rgba(0, 74, 44, 0.1);
        color: var(--revuity-green);
    }

    div[data-testid="stInfo"], div[data-testid="stSuccess"] {
        background-color: #FFF5ED;
        color: var(--revuity-text);
        border-left: 4px solid var(--revuity-orange);
    }

    div[data-testid="stTable"] table {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Revuity QRA Console")
st.caption("Powered by the Quantum Revenue Algorithm – the decision engine behind Revuity Analytics.")

st.markdown("""
This console runs Revuity's **Quantum Revenue Algorithm (QRA)** on your data.

**Upload 4 CSVs with the following columns:**

- **Pricing events**: `org_id, old_price, new_price, volume_before, volume_after`
- **Funnel / demand**: `org_id, month, leads`
- **Retention**: `org_id, cohort_month, months_since_acquisition, active_customers`
- **Revenue**: `org_id, month, revenue`

Then choose your assumptions (margin, horizon, ticket/retention changes) and click **Run QRA**.

You'll get:

- A **QRA State** table (health per org/location)
- A **Scenario** table (baseline vs scenario 12-month gross profit and IGP)
""")

st.info(
    "Want to try it quickly? Download sample CSVs from the QRA repo "
    "and upload them here: https://github.com/jayburgessjr/qra/tree/main/examples/sample_restaurant"
)

st.subheader("How to read the results")
interpretation = pd.DataFrame(
    [
        {
            "Metric": "QRA Health Score",
            "Range": "0-100",
            "Meaning": "Holistic score; >70 = strong, 40-70 = watchlist, <40 = critical",
        },
        {
            "Metric": "EPI (Elasticity Performance Index)",
            "Range": "0-100",
            "Meaning": "Sensitivity to price changes; high = resilient demand",
        },
        {
            "Metric": "RSI (Retention Strength Index)",
            "Range": "0-100",
            "Meaning": "Customer stickiness; high = strong cohort retention",
        },
        {
            "Metric": "VRI (Volatility Risk Index)",
            "Range": "0-100",
            "Meaning": "Revenue stability; low volatility pushes VRI toward 100",
        },
        {
            "Metric": "IGP 12M",
            "Range": "Can be negative or positive",
            "Meaning": "Incremental gross profit of the scenario vs baseline over 12 months",
        },
    ]
)
st.table(interpretation)




# ---------- Sidebar for configuration ----------

with st.sidebar:
    st.header("1️⃣ QRA Configuration")

    horizon_months = st.slider(
        "Projection Horizon (months)",
        min_value=6,
        max_value=36,
        value=12,
        step=3,
    )
    gross_margin = st.slider(
        "Gross Margin (%)",
        min_value=10,
        max_value=90,
        value=65,
        step=5,
    ) / 100.0

    st.header("2️⃣ Scenario Configuration")
    delta_ticket_pct = st.slider(
        "Ticket/Price Change (%)",
        min_value=-20,
        max_value=20,
        value=3,
        step=1,
    ) / 100.0
    delta_retention_pct = st.slider(
        "Retention Change (%)",
        min_value=-10,
        max_value=10,
        value=2,
        step=1,
    ) / 100.0


# ---------- 1. File uploads ----------

with st.expander("Upload Data", expanded=True):
    st.header("Upload Your Data")
    col1, col2 = st.columns(2)

    with col1:
        pricing_file = st.file_uploader(
            "Pricing events CSV",
            help="Required columns: org_id, old_price, new_price, volume_before, volume_after",
            type=["csv"],
            key="pricing",
        )
        funnel_file = st.file_uploader(
            "Funnel / demand CSV",
            help="Required columns: org_id, month, leads",
            type=["csv"],
            key="funnel",
        )

    with col2:
        retention_file = st.file_uploader(
            "Retention CSV",
            help="Required columns: org_id, cohort_month, months_since_acquisition, active_customers",
            type=["csv"],
            key="retention",
        )
        revenue_file = st.file_uploader(
            "Revenue CSV",
            help="Required columns: org_id, month, revenue",
            type=["csv"],
            key="revenue",
        )

st.markdown("---")

run_button = st.button("🚀 Run QRA")



def load_csv(file):
    if file is None:
        return None
    return pd.read_csv(file)


# ---------- 3. Run QRA when button is pressed ----------

if run_button:
    if not all([pricing_file, funnel_file, retention_file, revenue_file]):
        st.error("Please upload all four CSV files before running QRA.")
    else:
        with st.spinner("Running QRA engine..."):
            pricing_df = load_csv(pricing_file)
            funnel_df = load_csv(funnel_file)
            retention_df = load_csv(retention_file)
            revenue_df = load_csv(revenue_file)

            # 1) QRA state
            state_engine = QRAStateEngine(QRAStateConfig())
            state_result = state_engine.fit(
                pricing_df,
                funnel_df,
                retention_df,
                revenue_df,
            )
            state_df = state_result.state_df

            # 2) Scenarios per org
            scen_cfg = ScenarioConfig(
                horizon_months=horizon_months,
                gross_margin=gross_margin,
            )

            rows = []
            for org in state_df["org_id"].unique():
                base_gp = project_baseline_gp(revenue_df, org, scen_cfg)
                scen_gp = project_scenario_gp(
                    revenue_df,
                    org,
                    scen_cfg,
                    delta_ticket_pct=delta_ticket_pct,
                    delta_retention_pct=delta_retention_pct,
                )
                rows.append(
                    {
                        "org_id": org,
                        "baseline_gp": base_gp,
                        "scenario_gp": scen_gp,
                        "igp_12m": scen_gp - base_gp,
                    }
                )

            scenarios_df = pd.DataFrame(rows)

        st.success("QRA run complete ✅")

        # ---------- 4. Show results in tabs ----------
        tab1, tab2 = st.tabs(["QRA State", "Scenario Results"])

        with tab1:
            st.header("QRA State (per org)")
            st.caption("Includes EPI, RSI, VRI, and QRA Health Score.")
            st.dataframe(state_df, use_container_width=True)
            st.download_button(
                "⬇️ Download QRA State CSV",
                data=state_df.to_csv(index=False),
                file_name="qra_state.csv",
                mime="text/csv",
            )

        with tab2:
            st.header("Scenario Results (per org)")
            st.caption(
                "Baseline vs scenario discounted 12-month gross profit and incremental gross profit (IGP)."
            )
            st.dataframe(scenarios_df, use_container_width=True)
            st.download_button(
                "⬇️ Download Scenario Results CSV",
                data=scenarios_df.to_csv(index=False),
                file_name="qra_scenarios.csv",
                mime="text/csv",
            )
