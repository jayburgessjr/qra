
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .metrics import minmax_normalize, compute_revenue_volatility, compute_qra_health


@dataclass
class RestaurantQRAConfig:
    elastic_min: float = -2.0
    elastic_max: float = -0.1
    retention_min: float = 0.6
    retention_max: float = 1.0
    vol_min: float = 0.0
    vol_max: float = 0.5

    w_epi: float = 0.30
    w_rsi: float = 0.45
    w_vri: float = 0.25


@dataclass
class RestaurantQRAState:
    state_df: pd.DataFrame


def estimate_loglog_elasticity(df: pd.DataFrame) -> pd.Series:
    elasticities = {}
    for org, g in df.groupby("org_id"):
        g = g[(g["price"] > 0) & (g["quantity"] > 0)].copy()
        if len(g) < 2:
            elasticities[org] = np.nan
            continue
        x = np.log(g["price"].values)
        y = np.log(g["quantity"].values)
        X = np.vstack([np.ones_like(x), x]).T
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        elasticities[org] = float(beta[1])
    return pd.Series(elasticities, name="pricing_elasticity")


def estimate_exponential_churn(ret_df: pd.DataFrame) -> pd.Series:
    churn_rates = {}
    for org, g in ret_df.groupby("org_id"):
        g = g.sort_values("months_since_acquisition")
        t = g["months_since_acquisition"].values.astype(float)
        y = g["active_customers"].values.astype(float)
        mask = y > 0
        t = t[mask]
        y = y[mask]
        if len(y) < 2:
            churn_rates[org] = np.nan
            continue
        log_y = np.log(y)
        X = np.vstack([np.ones_like(t), -t]).T
        beta, *_ = np.linalg.lstsq(X, log_y, rcond=None)
        lambda_hat = max(beta[1], 0.0)
        churn_rate = 1.0 - np.exp(-lambda_hat * 1.0)
        churn_rates[org] = float(churn_rate)
    return pd.Series(churn_rates, name="cohort_churn_rate")


class RestaurantQRAEngine:
    def __init__(self, cfg: Optional[RestaurantQRAConfig] = None) -> None:
        self.cfg = cfg or RestaurantQRAConfig()

    def build_state(
        self,
        price_obs: pd.DataFrame,
        funnel_df: pd.DataFrame,
        retention_df: pd.DataFrame,
        revenue_df: pd.DataFrame,
    ) -> RestaurantQRAState:
        cfg = self.cfg

        elasticity = estimate_loglog_elasticity(price_obs)

        dv = (
            funnel_df.groupby("org_id")["leads"]
            .mean()
            .rename("demand_velocity")
        )

        churn = estimate_exponential_churn(retention_df)
        mv = compute_revenue_volatility(revenue_df)

        org_ids = sorted(set(price_obs["org_id"]) | set(funnel_df["org_id"]))

        state = (
            pd.DataFrame({"org_id": org_ids})
            .merge(elasticity.reset_index(), on="org_id", how="left")
            .merge(dv.reset_index(), on="org_id", how="left")
            .merge(churn.reset_index(), on="org_id", how="left")
            .merge(mv.reset_index(), on="org_id", how="left")
        )

        state["epi"] = minmax_normalize(
            state["pricing_elasticity"],
            cfg.elastic_min,
            cfg.elastic_max,
        ) * 100.0

        state["rsi"] = minmax_normalize(
            1.0 - state["cohort_churn_rate"],
            cfg.retention_min,
            cfg.retention_max,
        ) * 100.0

        vol_norm = minmax_normalize(
            state["market_volatility"],
            cfg.vol_min,
            cfg.vol_max,
        )
        state["vri"] = (1.0 - vol_norm) * 100.0

        state["qra_health_score"] = compute_qra_health(state)

        return RestaurantQRAState(state_df=state)
