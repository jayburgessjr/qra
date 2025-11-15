import streamlit as st
import pandas as pd

from qra.state import QRAStateEngine, QRAStateConfig
from qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp


st.set_page_config(
    page_title="QRA Console",
    layout="wide",
)

st.title("QRA Console")
st.write(
    "This application allows you to run the Quantum Revenue Algorithm (QRA) "
    "to get health scores and profit scenarios for your organizations/locations."
)
st.info(
    "**How to use the app:**\n"
    "1. Configure the QRA and scenario parameters in the sidebar on the left.\n"
    "2. Upload your data using the file uploaders below.\n"
    "3. Click the 'Run QRA' button to see the results."
)



# ---------- Sidebar for configuration ----------

with st.sidebar:
    st.header("1️⃣ QRA Configuration")
    st.info(
        "These parameters control the QRA state calculation."
    )

    horizon_months = st.slider(
        "Projection Horizon (months)",
        min_value=6,
        max_value=36,
        value=12,
        step=3,
        help="The number of months to project for the scenarios."
    )
    gross_margin = st.slider(
        "Gross Margin (%)",
        min_value=10,
        max_value=90,
        value=65,
        step=5,
        help="The gross margin of your business."
    ) / 100.0

    st.header("2️⃣ Scenario Configuration")
    st.info(
        "These parameters control the scenario projections."
    )
    delta_ticket_pct = st.slider(
        "Ticket/Price Change (%)",
        min_value=-20,
        max_value=20,
        value=3,
        step=1,
        help="The percentage change in ticket price for the scenario."
    ) / 100.0
    delta_retention_pct = st.slider(
        "Retention Change (%)",
        min_value=-10,
        max_value=10,
        value=2,
        step=1,
        help="The percentage change in retention for the scenario."
    ) / 100.0


# ---------- 1. File uploads ----------

with st.expander("Upload Data", expanded=True):
    st.header("Upload Your Data")
    st.info(
        "Please upload four CSV files with the following columns:\n"
        "- **Pricing events:** `org_id`, `old_price`, `new_price`, `volume_before`, `volume_after`\n"
        "- **Funnel / demand:** `org_id`, `month`, `leads`\n"
        "- **Retention:** `org_id`, `cohort_month`, `months_since_acquisition`, `active_customers`\n"
        "- **Revenue:** `org_id`, `month`, `revenue`"
    )
    col1, col2 = st.columns(2)

    with col1:
        pricing_file = st.file_uploader(
            "Pricing events CSV",
            type=["csv"],
            key="pricing",
        )
        funnel_file = st.file_uploader(
            "Funnel / demand CSV",
            type=["csv"],
            key="funnel",
        )

    with col2:
        retention_file = st.file_uploader(
            "Retention CSV",
            type=["csv"],
            key="retention",
        )
        revenue_file = st.file_uploader(
            "Revenue CSV",
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
            st.info(
                "The QRA State is a snapshot of the health of each organization/location. "
                "It includes the following metrics:\n"
                "- **EPI (Elasticity-Price Index):** A measure of how sensitive demand is to price changes.\n"
                "- **RSI (Retention-Strength Index):** A measure of how well you are retaining your customers.\n"
                "- **VRI (Volatility-Risk Index):** A measure of the volatility of your revenue.\n"
                "- **QRA Health Score:** A weighted average of the EPI, RSI, and VRI."
            )
            st.dataframe(state_df, use_container_width=True)
            st.download_button(
                "⬇️ Download QRA State CSV",
                data=state_df.to_csv(index=False),
                file_name="qra_state.csv",
                mime="text/csv",
            )

        with tab2:
            st.header("Scenario Results (per org)")
            st.info(
                "This tab shows the projected gross profit for the baseline and scenario cases, "
                "as well as the incremental gross profit (IGP) over the next 12 months."
            )
            st.dataframe(scenarios_df, use_container_width=True)
            st.download_button(
                "⬇️ Download Scenario Results CSV",
                data=scenarios_df.to_csv(index=False),
                file_name="qra_scenarios.csv",
                mime="text/csv",
            )

