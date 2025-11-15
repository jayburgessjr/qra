from __future__ import annotations

import numpy as np
import pandas as pd


def compute_pricing_elasticity(df: pd.DataFrame) -> pd.Series:
    """Estimate price elasticity from pricing event data."""
    elasticities = {}
    for org, g in df.groupby("org_id"):
        g = g[(g["old_price"] > 0) & (g["new_price"] > 0) & (g["volume_before"] > 0) & (g["volume_after"] > 0)].copy()
        if len(g) < 1:
            elasticities[org] = np.nan
            continue
        
        # Using the midpoint formula for elasticity
        q1, q2 = g["volume_before"].mean(), g["volume_after"].mean()
        p1, p2 = g["old_price"].mean(), g["new_price"].mean()
        
        if (q2 - q1) == 0 or (p2 - p1) == 0:
            elasticity = 0.0
        else:
            elasticity = ((q2 - q1) / ((q1 + q2) / 2)) / ((p2 - p1) / ((p1 + p2) / 2))
        elasticities[org] = elasticity
        
    return pd.Series(elasticities, name="pricing_elasticity").rename_axis("org_id")


def compute_demand_velocity(df: pd.DataFrame) -> pd.Series:
    """Compute demand velocity from funnel data."""
    return df.groupby("org_id")["leads"].mean().rename("demand_velocity")


def compute_retention_churn(df: pd.DataFrame) -> pd.Series:
    """Estimate cohort churn rate from retention data."""
    churn_rates = {}
    for org, g in df.groupby("org_id"):
        g = g.sort_values("months_since_acquisition")
        
        if len(g) < 2:
            churn_rates[org] = np.nan
            continue
            
        # Simple churn calculation: (lost_customers / initial_customers)
        initial_customers = g["active_customers"].iloc[0]
        final_customers = g["active_customers"].iloc[-1]
        
        if initial_customers == 0:
            churn_rates[org] = np.nan
            continue
            
        churn_rate = (initial_customers - final_customers) / initial_customers
        churn_rates[org] = churn_rate
        
    return pd.Series(churn_rates, name="cohort_churn_rate").rename_axis("org_id")


def compute_revenue_volatility(df: pd.DataFrame) -> pd.Series:
    """Compute revenue volatility from monthly revenue data."""
    return df.groupby("org_id")["revenue"].std().rename("market_volatility")


def minmax_normalize(
    s: pd.Series, min_val: float, max_val: float, clip: bool = True
) -> pd.Series:
    """Min-max normalize a series to a 0-1 range."""
    s_norm = (s - min_val) / (max_val - min_val)
    if clip:
        s_norm = s_norm.clip(0, 1)
    return s_norm


def compute_qra_health(
    state_df: pd.DataFrame,
    *,
    w_epi: float,
    w_rsi: float,
    w_vri: float,
) -> pd.Series:
    """Compute the QRA health score from normalized state metrics."""
    health_score = (
        state_df["epi"] * w_epi
        + state_df["rsi"] * w_rsi
        + state_df["vri"] * w_vri
    )
    return health_score
