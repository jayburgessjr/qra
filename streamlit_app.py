import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import streamlit as st
import pandas as pd

from qra.state import QRAStateEngine, QRAStateConfig
from qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp


st.set_page_config(
    page_title="QRA Console",
    layout="wide",
)

st.title("🧠 QRA Console")
st.write(
    "Upload your revenue data, run the Quantum Revenue Algorithm (QRA), "
    "and get health scores and profit scenarios per org/location."
)


# ---------- 1. File uploads ----------

st.header("1️⃣ Upload data")

col1, col2 = st.columns(2)

with col1:
    pricing_file = st.file_uploader(
        "Pricing events CSV\n\nRequired columns: org_id, old_price, new_price, volume_before, volume_after",
        type=["csv"],
        key="pricing",
    )
    funnel_file = st.file_uploader(
        "Funnel / demand CSV\n\nRequired columns: org_id, month, leads",
        type=["csv"],
        key="funnel",
    )

with col2:
    retention_file = st.file_uploader(
        "Retention CSV\n\nRequired columns: org_id, cohort_month, months_since_acquisition, active_customers",
        type=["csv"],
        key="retention",
    )
    revenue_file = st.file_uploader(
        "Revenue CSV\n\nRequired columns: org_id, month, revenue",
        type=["csv"],
        key="revenue",
    )

st.markdown("---")

# ---------- 2. QRA config ----------

st.header("2️⃣ QRA configuration")

col_cfg1, col_cfg2 = st.columns(2)

with col_cfg1:
    horizon_months = st.slider(
        "Projection horizon (months)",
        min_value=6,
        max_value=36,
        value=12,
        step=3,
    )
    gross_margin = st.slider(
        "Gross margin (%)",
        min_value=10,
        max_value=90,
        value=65,
        step=5,
    ) / 100.0

with col_cfg2:
    delta_ticket_pct = st.slider(
        "Scenario: ticket / price change (%)",
        min_value=-20,
        max_value=20,
        value=3,
        step=1,
    ) / 100.0
    delta_retention_pct = st.slider(
        "Scenario: retention change (%)",
        min_value=-10,
        max_value=10,
        value=2,
        step=1,
    ) / 100.0

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

        # ---------- 4. Show state ----------
        st.header("3️⃣ QRA State (per org)")
        st.caption("Includes EPI, RSI, VRI, and QRA Health Score.")
        st.dataframe(state_df, use_container_width=True)

        st.download_button(
            "⬇️ Download qra_state.csv",
            data=state_df.to_csv(index=False),
            file_name="qra_state.csv",
            mime="text/csv",
        )

        # ---------- 5. Show scenarios ----------
        st.header("4️⃣ Scenario results (per org)")
        st.caption(
            "Baseline vs scenario discounted 12-month gross profit and incremental gross profit (IGP)."
        )
        st.dataframe(scenarios_df, use_container_width=True)

        st.download_button(
            "⬇️ Download qra_scenarios.csv",
            data=scenarios_df.to_csv(index=False),
            file_name="qra_scenarios.csv",
            mime="text/csv",
        )
