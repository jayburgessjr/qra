
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .metrics import (
    minmax_normalize,
    compute_pricing_elasticity,
    compute_demand_velocity,
    compute_retention_churn,
    compute_revenue_volatility,
    compute_qra_health,
)


@dataclass
class QRAStateConfig:
    """Configuration for QRA state normalization and weighting."""

    elastic_min: float = -2.0
    elastic_max: float = 0.5
    retention_min: float = 0.6
    retention_max: float = 1.0
    vol_min: float = 0.0
    vol_max: float = 1.0

    w_epi: float = 0.35
    w_rsi: float = 0.40
    w_vri: float = 0.25


@dataclass
class QRAStateResult:
    """Result of running the QRA state engine."""

    state_df: pd.DataFrame


class QRAStateEngine:
    """Compute QRA state metrics from raw fact tables."""

    def __init__(self, cfg: Optional[QRAStateConfig] = None) -> None:
        self.cfg = cfg or QRAStateConfig()

    def fit(
        self,
        pricing_df: pd.DataFrame,
        funnel_df: pd.DataFrame,
        retention_df: pd.DataFrame,
        revenue_df: pd.DataFrame,
    ) -> QRAStateResult:
        elasticity = compute_pricing_elasticity(pricing_df)
        dv = compute_demand_velocity(funnel_df)
        churn = compute_retention_churn(retention_df)
        mv = compute_revenue_volatility(revenue_df)

        org_ids = sorted(
            set(pricing_df["org_id"])
            | set(funnel_df["org_id"])
            | set(retention_df["org_id"])
            | set(revenue_df["org_id"])
        )
        state = (
            pd.DataFrame({"org_id": org_ids})
            .merge(elasticity.reset_index(), on="org_id", how="left")
            .merge(dv.reset_index(), on="org_id", how="left")
            .merge(churn.reset_index(), on="org_id", how="left")
            .merge(mv.reset_index(), on="org_id", how="left")
        )

        cfg = self.cfg

        state["epi"] = minmax_normalize(
            state["pricing_elasticity"], cfg.elastic_min, cfg.elastic_max
        ) * 100.0

        state["rsi"] = minmax_normalize(
            1.0 - state["cohort_churn_rate"],
            cfg.retention_min,
            cfg.retention_max,
        ) * 100.0

        vol_norm = minmax_normalize(
            state["market_volatility"], cfg.vol_min, cfg.vol_max
        )
        state["vri"] = (1.0 - vol_norm) * 100.0

        state["qra_health_score"] = compute_qra_health(
            state,
            w_epi=cfg.w_epi,
            w_rsi=cfg.w_rsi,
            w_vri=cfg.w_vri,
        )

        return QRAStateResult(state_df=state)
