
# QRA Restaurant Franchise Case – Summary & Findings

This document summarizes the **restaurant franchise case study** implemented in
`notebooks/qra_restaurant_case.ipynb`.

## Scenario

We modeled a mid-sized **casual dining restaurant franchise** with three locations:

- `loc_downtown`
- `loc_mall`
- `loc_suburb`

For each location we simulated 12 months of data:

- Monthly reservations / covers (treated as demand/leads)
- Monthly revenue (ticket size × covers with noise and seasonality)
- Menu pricing events (two small price increases)
- Loyalty program retention (active members over 0, 3, 6, 9 months)

The data is synthetic but constructed to look realistic for a restaurant business
with mild seasonality and modest price changes.

## QRA Metrics Computed

Using the shared QRA helpers in `src/qra/metrics.py`, the notebook computes for each location:

1. **Pricing Elasticity** – how sensitive demand is to menu price changes.
2. **Demand Velocity** – average monthly covers/reservations.
3. **Cohort Churn Rate** – decay in active loyalty members over time.
4. **Revenue Volatility** – coefficient of variation of monthly revenue.
5. **Indices:**

   - **EPI (Elasticity & Pricing Index)** – higher means price changes are well tolerated.
   - **RSI (Retention Strength Index)** – higher means stronger loyalty retention.
   - **VRI (Volatility Risk Index)** – higher means more stable, less volatile revenue.

6. **QRA Health Score (0–100)** – a weighted combination of EPI, RSI, and VRI.

These values are displayed in the final `state_rest` table in the notebook.

## High-Level Findings (Qualitative)

Because the data is synthetic, the exact numbers are not tied to a real chain,
but the **relative patterns** are illustrative:

- Locations with **higher demand velocity** (more covers per month) tend to have
  slightly higher revenue volatility due to seasonality and promotions.
- Locations with **stronger loyalty retention** (higher RSI) score better on the
  overall **QRA Health Score**, since repeat guests stabilize revenue.
- Locations whose revenue is **more stable month-to-month** earn a higher
  **VRI**, boosting their QRA Health Score even if their raw demand is a bit lower.
- Small price increases with limited volume loss produce **favorable elasticity**
  values, which translate into a stronger **EPI** and higher QRA Health.

In short, the restaurant franchise with strong loyalty retention, tolerable price
elasticity, and relatively stable revenue will rank highest on QRA Health and is
best positioned for more aggressive pricing and retention experiments.

## How to Use This Case

This case study is meant to be:

- A **template** for plugging in real restaurant data.
- A **clear example** for operators and revenue leaders who want to see how
  QRA behaves on a tangible business model.
- A stepping stone toward a full implementation that layers on 12-month
  forecast scenarios and action ranking.

In a production setup on Databricks or Fabric, the same logic would operate on
tables fed from POS, reservation systems, and loyalty/CRM data, with the results
pushed into BI tools (Power BI, Looker, Tableau) as `qra_state` views.
