# Quantum Revenue Algorithm (QRA)  
**Technical Overview and Architecture**

## 1. Purpose and Role in Revuity

The Quantum Revenue Algorithm (QRA) is the analytical and decision engine behind Revuity Analytics. Its purpose is to:

1. Transform heterogeneous revenue-related data into a **standardized state representation** of a business (per org, unit, or location).
2. Generate **forward-looking scenarios** for gross profit under configurable assumptions.
3. Compute **risk- and time-adjusted decision scores** that rank revenue actions (levers) by expected economic value.

In the Revuity stack, QRA sits between raw data (warehouse / lakehouse / CSV) and operator interfaces (dashboards, RevBoard, reports). It can run locally or inside Databricks/Fabric, and its outputs are consumed by BI tools (Power BI, Looker, Tableau) and Revuity’s own products:

- **Revenue Clear** – diagnostic/clarity audit mode.
- **RevenueOS / RevBoard** – ongoing decision engine and governance.

---

## 2. High-Level Design

QRA is implemented as a modular Python package with three main layers:

1. **State Engine**  
   - Ingests normalized fact tables.
   - Computes a set of primitive metrics and composite indices.
   - Outputs a per-entity “QRA state” with health scores.

2. **Scenario Engine**  
   - Uses historical revenue and configurable assumptions (margin, horizon, uplift) to estimate baseline and scenario 12-month gross profit, including discounting.

3. **Decision Engine**  
   - Consumes modeled incremental gross profit, probability, cycle time, and risk.
   - Computes a **decision_score** used to rank actions.

Each layer can be customized per vertical (e.g., restaurants, SaaS) via configuration and vertical-specific engines.

---

## 3. Data Model (Inputs)

QRA assumes data can be mapped into four conceptual fact tables. Column names can vary as long as semantics are preserved.

1. **Pricing Events**  
   Granular price changes and associated volumes.

   Example schema:

   - `org_id`
   - `old_price`
   - `new_price`
   - `volume_before`
   - `volume_after`

2. **Funnel / Demand**  
   Periodic lead or demand volume by org/location.

   Example schema:

   - `org_id`
   - `month` (or any period identifier)
   - `leads` (or visits, covers, sessions, etc.)

3. **Retention / Cohorts**  
   Cohort-based customer survival over time.

   Example schema:

   - `org_id`
   - `cohort_month`
   - `months_since_acquisition`
   - `active_customers`

4. **Revenue Time Series**  
   Periodic revenue by org/location.

   Example schema:

   - `org_id`
   - `month`
   - `revenue`

These tables can be sourced directly from CSV files or from lakehouse tables in Databricks/Fabric (e.g., `gold.fact_pricing_events`, `gold.fact_funnel_monthly`, etc.).

---

## 4. QRA State Engine

The state engine converts raw facts into a compact representation of the business using four primitive metrics and three composite indices, culminating in a **QRA Health Score**.

### 4.1 Price Elasticity

QRA estimates the **price elasticity of demand** per `org_id`, denoted `ε`.

For simple pricing events:

- Observe price change and volume change before/after.
- Approximate elasticity as:

\[
\varepsilon \approx \frac{\Delta Q / Q}{\Delta P / P}
\]

Where:
- \( Q \) is quantity (volume),
- \( P \) is price.

For richer time series (e.g., restaurant vertical), QRA can use a log–log regression:

\[
\log(Q_t) = \alpha + \varepsilon \cdot \log(P_t) + \epsilon_t
\]

and estimate `ε` via least squares. Negative `ε` indicates demand decreases when price increases.

The elasticity series per `org_id` is aggregated into a single `pricing_elasticity` metric (e.g., mean or robust central tendency over observations).

### 4.2 Demand Velocity

**Demand velocity** captures average lead/demand volume over a defined time window:

\[
\text{demand\_velocity}_{org} = \mathbb{E}[\text{leads}_{org, t}]
\]

Practically:

- Group by `org_id`.
- Compute mean `leads` (or a more robust measure, such as median, if needed).

This is a proxy for demand inflow intensity.

### 4.3 Retention and Churn

From cohort tables, QRA estimates a **churn rate** per org.

A simple formulation:

1. For each `(org_id, cohort_month)`, compute survival over `months_since_acquisition`.
2. Fit an **exponential decay** model:

\[
\text{active}_t = N_0 \cdot e^{-\lambda t}
\]

Taking logs:

\[
\log(\text{active}_t) = \log(N_0) - \lambda t
\]

Estimate `λ` via linear regression on `(t, log(active_t))`. Then convert to a per-period churn:

\[
\text{churn\_rate} = 1 - e^{-\lambda \cdot \Delta t}
\]

Where `Δt` is the base time unit (e.g., one month). The result is a **cohort_churn_rate** per `org_id`. Survival is `1 - churn_rate`.

### 4.4 Revenue Volatility

QRA measures **revenue volatility** using the coefficient of variation (CV):

\[
\text{market\_volatility}_{org} = \frac{\sigma(\text{revenue}_{org, t})}{\mu(\text{revenue}_{org, t})}
\]

where:
- `σ` is standard deviation,
- `μ` is mean revenue over the time window.

Higher volatility implies less predictable revenue.

### 4.5 Normalization and Indices

The raw metrics are transformed into unitless indices on a 0–100 scale via min–max normalization, with ranges configured via `QRAStateConfig` (or vertical-specific configs).

General min–max normalization:

\[
\text{norm}(x) = \frac{x - x_{min}}{x_{max} - x_{min}}
\]

Clamped to `[0, 1]`, then scaled to `[0, 100]`.

Indices:

1. **Elasticity Performance Index (EPI)**

\[
\text{EPI} = 100 \cdot \text{norm}(\text{pricing\_elasticity}; \text{elastic\_min}, \text{elastic\_max})
\]

Configured such that more commercially favorable elasticity (e.g., less sensitive demand) yields higher EPI.

2. **Retention Strength Index (RSI)**

Using survival (`1 - churn`):

\[
\text{RSI} = 100 \cdot \text{norm}(1 - \text{cohort\_churn\_rate}; \text{retention\_min}, \text{retention\_max})
\]

3. **Volatility Resilience Index (VRI)**

First normalize volatility, then invert so lower volatility → higher index:

\[
\text{vol\_norm} = \text{norm}(\text{market\_volatility}; \text{vol\_min}, \text{vol\_max})
\]
\[
\text{VRI} = 100 \cdot (1 - \text{vol\_norm})
\]

### 4.6 QRA Health Score

The **QRA Health Score** is a weighted aggregate of EPI, RSI, and VRI:

\[
\text{Health} = w_{epi} \cdot \text{EPI} + w_{rsi} \cdot \text{RSI} + w_{vri} \cdot \text{VRI}
\]

Weights \( w_{epi}, w_{rsi}, w_{vri} \) are defined in configuration (e.g., QRAStateConfig or RestaurantQRAConfig) and sum to 1.

The state engine produces a `state_df` with one row per `org_id` containing:

- Primitive metrics: `pricing_elasticity`, `demand_velocity`, `cohort_churn_rate`, `market_volatility`
- Indices: `epi`, `rsi`, `vri`
- Composite: `qra_health_score`

This forms the **QRA State** for decision-making and visualization.

---

## 5. QRA Scenario Engine

The scenario engine projects discounted gross profit under baseline and modified assumptions.

### 5.1 Configuration

`ScenarioConfig` includes:

- `horizon_months` – number of months to project (e.g., 12).
- `gross_margin` – assumed gross margin on revenue (0–1).
- `discount_rate_annual` – annual discount rate to reflect time value of money and risk.

Monthly discount rate:

\[
r_{monthly} = (1 + r_{annual})^{1/12} - 1
\]

### 5.2 Baseline 12-Month Gross Profit

For a given `org_id`, compute mean historical monthly revenue:

\[
\bar{R} = \mathbb{E}[\text{revenue}_{org, t}]
\]

Then project discounted gross profit over `H` months:

\[
\text{GP}_{baseline} = \sum_{t=1}^{H} \frac{\bar{R} \cdot \text{gross\_margin}}{(1 + r_{monthly})^{t}}
\]

### 5.3 Scenario 12-Month Gross Profit

Scenario logic introduces multiplicative adjustments:

- `delta_ticket_pct` – relative change in ticket/price.
- `delta_retention_pct` – relative change in retention/demand.

Define:

\[
m_{ticket} = 1 + \Delta_{ticket}
\]
\[
m_{retention} = 1 + \Delta_{retention}
\]

Then:

\[
\text{GP}_{scenario} = \sum_{t=1}^{H} \frac{\bar{R} \cdot m_{ticket} \cdot m_{retention} \cdot \text{gross\_margin}}{(1 + r_{monthly})^{t}}
\]

The **incremental gross profit (IGP)** over the horizon is:

\[
\text{IGP}_{12m} = \text{GP}_{scenario} - \text{GP}_{baseline}
\]

This is computed per `org_id` and surfaced as `baseline_gp`, `scenario_gp`, and `igp_12m`.

---

## 6. QRA Decision Engine

The decision engine translates modeled outcomes into ranked actions.

It expects an **actions table** with:

- `org_id`
- `action_id`
- `igp_12m` – modeled incremental gross profit over the horizon
- `probability` – estimated probability that the modeled outcome is realized (0–1)
- `cycle_time_months` – time to realize impact
- `risk_score` – risk indicator in [0, 1], higher = riskier

An `ActionScoringConfig` defines a `risk_penalty` parameter.

The **decision score** formula:

\[
\text{decision\_score} =
\frac{\text{IGP}_{12m} \cdot \max(\text{probability}, 0)}{
\max(\text{cycle\_time\_months}, \epsilon) \cdot \left(1 + \lambda \cdot \max(\text{risk\_score}, 0)\right)
}
\]

Where:

- \(\lambda\) = `risk_penalty`
- \(\epsilon\) = small positive constant to avoid division by zero

Interpretation:

- Higher **IGP** and **probability** increase the score.
- Longer **cycle time** and higher **risk_score** decrease the score.
- `decision_score` is used to rank actions from most attractive to least attractive.

This gives QRA a clear, programmable way to answer:  
**“Which revenue lever should we pull first, given payback speed and risk?”**

---

## 7. Vertical Specialization

QRA supports vertical-specific engines that reuse the same architecture but adjust:

- Metric estimation methods,
- Normalization ranges,
- Index weights.

Example: **RestaurantQRAEngine**:

- Uses log–log elasticity on `(price, quantity)` observations.
- Uses exponential decay retention on loyalty cohorts.
- Tightens `vol_min` / `vol_max` ranges to reflect typical restaurant volatility.
- Adjusts weights (e.g., more emphasis on retention for casual dining).

The vertical engine exposes the same type of output (`state_df` with indices and health score) but tuned to the specific economics of the industry.

This “pluggable vertical engine” pattern is core to how Revuity can reuse the same QRA framework across different business models while keeping domain-specific behavior.

---

## 8. System Architecture and Deployment

### 8.1 Package Structure

The QRA logic is packaged as a Python module (using `src` layout). Typical structure:

- `qra/metrics.py` – low-level numerical helpers (normalization, elasticity, volatility, churn).
- `qra/state.py` – generic `QRAStateEngine` and configuration.
- `qra/restaurant.py` – `RestaurantQRAEngine` and restaurant-specific logic.
- `qra/scenario.py` – `ScenarioConfig`, profit projection, and `score_actions`.

Tests (with `pytest`) validate:

- Indices are within [0, 100].
- Elasticities and churn estimates are within expected ranges.
- Scenario GP increases under positive uplift.
- Action ranking behavior is consistent with design.

### 8.2 Databricks / Fabric Integration

QRA can be executed as a scheduled job in environments like Databricks or Fabric:

1. Install the QRA package on the workspace / cluster.
2. Create a notebook or script that:
   - Reads fact tables as Spark DataFrames.
   - Converts them to pandas for the current implementation, or re-implements metrics using Spark APIs.
   - Calls `QRAStateEngine` and scenario functions.
   - Writes results back to the lake as Delta tables:
     - `qra.qra_state`
     - `qra.qra_scenarios`
3. Downstream, BI tools or internal applications (RevBoard) consume these tables.

This architecture separates **data platform concerns** (ETL, storage) from **decision logic** (QRA).

---

## 9. Extensibility

QRA is designed to be extended along multiple axes:

- **New metrics**  
  Additional primitives (e.g., unit economics, CAC, LTV) can be integrated into the state and health score.

- **Alternative normalizations**  
  Replace min–max with quantile-based scaling or z-score + logistic transforms as needed for stability.

- **Richer scenarios**  
  Instead of simple multipliers, scenarios can be driven by simulated response functions (e.g., using elasticity to derive demand changes from price changes).

- **Automated action generation**  
  Generate candidate actions programmatically (e.g., price ladders, retention campaigns) and score them using the decision engine.

- **Agentic and AI integrations**  
  QRA outputs can be used to drive agent workflows (e.g., automatically generating playbooks or campaigns) while QRA remains the “governor” for prioritization.

---

## 10. IP-Relevant Characteristics (Conceptual)

The following characteristics may be relevant for intellectual property strategies (subject to legal review):

1. **Specific combination of metrics and indices**  
   - Use of elasticity, retention, and volatility as primitives.
   - Transformation into EPI, RSI, VRI, and a weighted QRA Health Score as a standardized “state” representation for revenue systems.

2. **Unified state → scenario → decision pipeline**  
   - A systematic pipeline that:
     - Normalizes heterogeneous revenue data into a standardized state.
     - Projects discounted gross profit under configurable levers.
     - Ranks actions using a risk- and time-adjusted decision score.

3. **Verticalized QRA engines with a common core**  
   - A pluggable architecture that maintains a consistent core algorithm, while swapping in vertical-specific estimators and configurations.

4. **Decision scoring formulation**  
   - The specific functional form of `decision_score` that encodes expected payoff, probability, cycle time, and risk into a single scalar ranking metric.

Any formal IP filing (patent, trade secret documentation, etc.) would need to build on and possibly extend this technical description, and should be reviewed by qualified legal counsel.

---

**Status:**  
This document reflects the current design and implementation of Revuity’s Quantum Revenue Algorithm (QRA) and can be used as an internal reference, a basis for documentation, and a starting point for IP discussions.
