
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
