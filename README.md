
# QRA Algorithm Demo

This repo is a minimal, educational implementation of the Quantum Revenue Algorithm (QRA)
in Python using Jupyter notebooks.

## What this contains

- `notebooks/qra_intro.ipynb` – main notebook that:
  - defines simple input data (funnel, revenue, retention)
  - computes QRA state metrics (elasticity, demand velocity, churn, volatility)
  - builds a basic QRA health score
  - sketches a place to add forecast & action ranking later
- `src/qra/metrics.py` – helper functions for QRA calculations
- `requirements.txt` – minimal dependencies

This is designed to be run on Databricks, Fabric, or local Jupyter as a starting point.

## QRA Algorithm Overview

The QRA (Quantum Revenue Algorithm) is a framework for evaluating the health of a business and scoring potential actions. The algorithm consists of two main parts:

### 1. QRA State Engine

This engine calculates the "state" of a business by computing three key metrics:

*   **EPI (Elasticity-Price Index):** Measures how sensitive demand is to price changes. A higher EPI indicates that demand is more sensitive to price changes.
*   **RSI (Retention-Strength Index):** Measures customer retention. A higher RSI indicates that you are better at retaining your customers.
*   **VRI (Volatility-Risk Index):** Measures the volatility of your revenue. A lower VRI indicates that your revenue is more stable.

These three metrics are then combined into a single **QRA Health Score**, which provides a high-level overview of the health of the business.

### 2. Scenario Projection

This part of the algorithm projects the gross profit (GP) for a baseline and a scenario case. The scenario is defined by a percentage change in ticket price and retention. This allows you to see the potential impact of different actions on your bottom line.

## Usage

To use the Streamlit app, follow these steps:

1.  **Configure the QRA and scenario parameters** in the sidebar on the left.
2.  **Upload your data** using the file uploaders. You will need four CSV files with the following columns:
    -   **Pricing events:** `org_id`, `old_price`, `new_price`, `volume_before`, `volume_after`
    -   **Funnel / demand:** `org_id`, `month`, `leads`
    -   **Retention:** `org_id`, `cohort_month`, `months_since_acquisition`, `active_customers`
    -   **Revenue:** `org_id`, `month`, `revenue`
3.  **Click the 'Run QRA' button** to see the results.

The results will be displayed in two tabs:
-   **QRA State:** A snapshot of the health of each organization/location.
-   **Scenario Results:** The projected gross profit for the baseline and scenario cases.

## Deployment

The Streamlit app is deployed at the following URL:
[https://qrarevu.streamlit.app/](https://qrarevu.streamlit.app/)
