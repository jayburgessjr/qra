
# Databricks QRA Job Example (Python script-style notebook)
# Adjust table names and database/catalog for your environment.

from pyspark.sql import SparkSession
import pandas as pd

from qra.state import QRAStateEngine, QRAStateConfig
from qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp

spark = SparkSession.builder.getOrCreate()

pricing_df_spark = spark.table("gold.fact_pricing_events")
funnel_df_spark = spark.table("gold.fact_funnel_monthly")
retention_df_spark = spark.table("gold.fact_retention_cohorts")
revenue_df_spark = spark.table("gold.fact_revenue_monthly")

pricing_pdf = pricing_df_spark.toPandas()
funnel_pdf = funnel_df_spark.toPandas()
retention_pdf = retention_df_spark.toPandas()
revenue_pdf = revenue_df_spark.toPandas()

state_engine = QRAStateEngine(QRAStateConfig())
state_result = state_engine.fit(pricing_pdf, funnel_pdf, retention_pdf, revenue_pdf)
state_df = state_result.state_df

state_sdf = spark.createDataFrame(state_df)
state_sdf.write.format("delta").mode("overwrite").saveAsTable("qra.qra_state")

scen_cfg = ScenarioConfig(horizon_months=12)
org_ids = state_df["org_id"].unique().tolist()

rows = []
for org in org_ids:
    base_gp = project_baseline_gp(revenue_pdf, org, scen_cfg)
    scen_gp = project_scenario_gp(
        revenue_pdf,
        org,
        scen_cfg,
        delta_ticket_pct=0.03,
        delta_retention_pct=0.02,
    )
    igp = scen_gp - base_gp
    rows.append({
        "org_id": org,
        "baseline_gp": base_gp,
        "scenario_gp": scen_gp,
        "igp_12m": igp,
    })

scen_df = pd.DataFrame(rows)
scen_sdf = spark.createDataFrame(scen_df)
scen_sdf.write.format("delta").mode("overwrite").saveAsTable("qra.qra_scenarios")
