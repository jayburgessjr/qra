# Running QRA for Clients

This document explains how to run the Quantum Revenue Algorithm (QRA) for each client in a repeatable way.

The pattern is:

> **New client → standardize data → run QRA → produce state + scenarios → plug into reports/dashboards.**

---

## 1. Conceptual Flow (Per Client)

For every client, the high-level steps are:

1. **Standardize their data**

   Map the client’s data into QRA’s standard shapes:

   - Pricing events  
   - Demand / funnel volumes  
   - Retention / cohorts  
   - Revenue over time  

2. **Run the QRA engine**

   - Generic engine: `QRAStateEngine` (`src/qra/state.py`)
   - Vertical engine (e.g. restaurants): `RestaurantQRAEngine` (`src/qra/restaurant.py`)
   - Scenario / decision layer: `ScenarioConfig`, `project_baseline_gp`, `project_scenario_gp`, `score_actions` (`src/qra/scenario.py`)

3. **Persist outputs**

   - `qra_state` – per-org/location health and component indices.
   - `qra_scenarios` – projected baseline vs scenario GP and IGP (incremental gross profit).
   - (Optional) action rankings using `score_actions`.

4. **Use outputs in products**

   - **Revenue Clear** – one-off audit / report.
   - **RevenueOS / RevBoard** – ongoing dashboards and decision support.

---

## 2. One-Time Setup (Developer Machine)

Do this once per environment:

```bash
# 1) Unzip the repo and cd into it
unzip qra-algorithm.zip
cd qra-algorithm

# 2) Optional: create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Install the package in editable mode + pytest
pip install -e .
pip install pytest

# 4) Run tests
pytest
```

If tests pass, the core QRA engine is wired and stable.

---

## 3. Local Workflow (Per Client, e.g. Revenue Clear)

This is the flow when you’re running QRA locally (e.g. for a 2-week audit) using CSVs or query exports.

### 3.1. Create a client folder

Inside the repo:

```text
clients/
  acme_restaurant/
    pricing.csv
    funnel.csv
    retention.csv
    revenue.csv
```

Example schemas:

- `pricing.csv`  
  `org_id, old_price, new_price, volume_before, volume_after`

- `funnel.csv`  
  `org_id, month, leads`

- `retention.csv`  
  `org_id, cohort_month, months_since_acquisition, active_customers`

- `revenue.csv`  
  `org_id, month, revenue`

You can adapt column names as needed, as long as they match what the engine expects.

### 3.2. Run QRA via a notebook or script

Example: `notebooks/run_qra_acme.ipynb` (or `.py`):

```python
import os
import pandas as pd

from src.qra.state import QRAStateEngine, QRAStateConfig
from src.qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp

# 1) Load client data
base = "clients/acme_restaurant"

pricing_df   = pd.read_csv(f"{base}/pricing.csv")
funnel_df    = pd.read_csv(f"{base}/funnel.csv")
retention_df = pd.read_csv(f"{base}/retention.csv")
revenue_df   = pd.read_csv(f"{base}/revenue.csv")

# 2) Run generic QRA state engine
state_engine = QRAStateEngine(QRAStateConfig())
state_result = state_engine.fit(pricing_df, funnel_df, retention_df, revenue_df)
state_df = state_result.state_df

# 3) Run a simple scenario (e.g. +3% ticket, +2% retention)
scen_cfg = ScenarioConfig(horizon_months=12)

rows = []
for org in state_df["org_id"].unique():
    base_gp = project_baseline_gp(revenue_df, org, scen_cfg)
    scen_gp = project_scenario_gp(
        revenue_df,
        org,
        scen_cfg,
        delta_ticket_pct=0.03,   # +3% ticket
        delta_retention_pct=0.02 # +2% retention
    )
    rows.append({
        "org_id": org,
        "baseline_gp": base_gp,
        "scenario_gp": scen_gp,
        "igp_12m": scen_gp - base_gp,
    })

scenarios_df = pd.DataFrame(rows)

# 4) Save outputs for the client
out_base = f"{base}/output"
os.makedirs(out_base, exist_ok=True)

state_df.to_csv(f"{out_base}/qra_state.csv", index=False)
scenarios_df.to_csv(f"{out_base}/qra_scenarios.csv", index=False)
```

Run this via:

```bash
jupyter lab  # or jupyter notebook
# Open notebooks/run_qra_acme.ipynb and run all cells
```

Outputs (per client):

- `clients/acme_restaurant/output/qra_state.csv`
- `clients/acme_restaurant/output/qra_scenarios.csv`

You can then bring these into:

- Power BI / Looker / Tableau
- PDF / slide decks for Revenue Clear

### 3.3. Restaurant-specific engine

If the client is a restaurant franchise and you’ve prepared restaurant-style tables (price observations, loyalty cohorts, etc.), use:

```python
from src.qra.restaurant import RestaurantQRAEngine, RestaurantQRAConfig

engine = RestaurantQRAEngine(RestaurantQRAConfig())
state_result = engine.build_state(price_obs, funnel_df, retention_df, revenue_df)
state_df = state_result.state_df
```

The rest of the workflow is identical.

---

## 4. Databricks Workflow (RevenueOS / RevBoard)

This is the pattern when the client has a lakehouse and you want QRA running on a schedule.

### 4.1. Install the package in Databricks

Recommended path:

1. Push this repo to a Git provider (GitHub, etc.).
2. In Databricks:
   - Use **Repos** → “Add repo” → point to your Git URL.
3. On the cluster / in a notebook:

```python
# Inside Databricks notebook cell
%pip install -e /Workspace/Repos/<your-user>/<qra-repo-name>
```

Ensure `src/qra/__init__.py` exists so `import qra` works.

### 4.2. Standardize client data into gold tables

Your ETL should populate fact tables like:

- `gold.fact_pricing_events`
- `gold.fact_funnel_monthly`
- `gold.fact_retention_cohorts`
- `gold.fact_revenue_monthly`

If you’re multi-tenant, include a `client_id` column and filter on it within the job.

### 4.3. QRA job notebook (skeleton)

Use the provided `notebooks/databricks_qra_job_example.py` as a starting point, or create a Databricks notebook with logic like this:

```python
from pyspark.sql import SparkSession
import pandas as pd

from qra.state import QRAStateEngine, QRAStateConfig
from qra.scenario import ScenarioConfig, project_baseline_gp, project_scenario_gp

spark = SparkSession.builder.getOrCreate()

# 1) Read fact tables (add client filters if multi-tenant)
pricing_df_spark   = spark.table("gold.fact_pricing_events")
funnel_df_spark    = spark.table("gold.fact_funnel_monthly")
retention_df_spark = spark.table("gold.fact_retention_cohorts")
revenue_df_spark   = spark.table("gold.fact_revenue_monthly")

pricing_pdf   = pricing_df_spark.toPandas()
funnel_pdf    = funnel_df_spark.toPandas()
retention_pdf = retention_df_spark.toPandas()
revenue_pdf   = revenue_df_spark.toPandas()

# 2) Run QRA state
state_engine = QRAStateEngine(QRAStateConfig())
state_df = state_engine.fit(pricing_pdf, funnel_pdf, retention_pdf, revenue_pdf).state_df

state_sdf = spark.createDataFrame(state_df)
state_sdf.write.format("delta").mode("overwrite").saveAsTable("qra.qra_state")

# 3) Simple scenario for all orgs
scen_cfg = ScenarioConfig(horizon_months=12)
rows = []

for org in state_df["org_id"].unique().tolist():
    base_gp = project_baseline_gp(revenue_pdf, org, scen_cfg)
    scen_gp = project_scenario_gp(
        revenue_pdf,
        org,
        scen_cfg,
        delta_ticket_pct=0.03,
        delta_retention_pct=0.02,
    )
    rows.append({
        "org_id": org,
        "baseline_gp": base_gp,
        "scenario_gp": scen_gp,
        "igp_12m": scen_gp - base_gp,
    })

scen_df = pd.DataFrame(rows)
scen_sdf = spark.createDataFrame(scen_df)
scen_sdf.write.format("delta").mode("overwrite").saveAsTable("qra.qra_scenarios")
```

You can adjust:

- Table names
- Filters (e.g. `.where("client_id = 'ACME'")`)
- Scenario assumptions (e.g. different ticket/retention uplifts)

### 4.4. Schedule as a Databricks Job

1. In Databricks UI, go to **Jobs → Create Job**.
2. Select the notebook that contains the QRA job logic.
3. Configure:
   - Cluster
   - Schedule (e.g. daily at 07:00)
   - Parameters (if you parameterize `client_id`, horizon, etc.)

Now `qra.qra_state` and `qra.qra_scenarios` will refresh on schedule and are ready to be used by:

- Power BI / Looker / Tableau
- RevBoard / RevenueOS UI

---

## 5. Optional: Decision Scoring (Action Ranking)

If you want QRA to output a ranked list of actions (plays), you can use `score_actions` from `src/qra/scenario.py`.

Expected input columns:

- `org_id`
- `action_id`
- `igp_12m` – modeled incremental gross profit over 12 months
- `probability` – probability the action behaves as modeled (0–1)
- `cycle_time_months` – time to see value
- `risk_score` – 0–1, higher = riskier

Example:

```python
import pandas as pd
from src.qra.scenario import score_actions, ActionScoringConfig

actions = pd.DataFrame({
    "org_id": ["org_x", "org_x"],
    "action_id": ["raise_prices_3pct", "loyalty_program_v2"],
    "igp_12m": [100_000, 50_000],
    "probability": [0.8, 0.9],
    "cycle_time_months": [6, 3],
    "risk_score": [0.2, 0.5],
})

scored = score_actions(actions, ActionScoringConfig(risk_penalty=1.0))
scored_sorted = scored.sort_values("decision_score", ascending=False)
```

You can persist this as another table (e.g. `qra.qra_actions`) and surface it directly in your RevBoard UI.

---

## 6. Per-Client SOP (Checklist)

For each new client:

1. **Connect and standardize data**

   - Map their pricing, demand, retention, and revenue into either:
     - Local CSVs under `clients/<client>/`
     - Or gold fact tables in the lakehouse.

2. **Choose the engine**

   - Use `QRAStateEngine` for generic.
   - Use `RestaurantQRAEngine` (or other vertical engine) for specialized verticals.

3. **Run QRA**

   - Locally via notebook/script for one-off audits (Revenue Clear).
   - Or via Databricks job for ongoing RevenueOS / RevBoard.

4. **Export / persist outputs**

   - `qra_state` for health + indices.
   - `qra_scenarios` for GP projections and IGP.
   - Optional `qra_actions` for ranked decision plays.

5. **Turn into deliverables**

   - Feed into BI dashboards.
   - Feed into reports, decks, and RevBoard.
   - Use the IGP and health scores to drive recommendations, pricing, and performance/fee conversations.

This gives you a consistent, repeatable way to run the **same QRA brain** for every client.
