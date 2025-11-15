
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class ScenarioConfig:
    horizon_months: int = 12
    gross_margin: float = 0.65
    discount_rate_annual: float = 0.10


def _monthly_discount_rate(annual_rate: float) -> float:
    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


def project_baseline_gp(
    revenue_df: pd.DataFrame,
    org_id: str,
    scen_cfg: ScenarioConfig,
) -> float:
    df = revenue_df[revenue_df["org_id"] == org_id]
    if df.empty:
        return 0.0
    mean_rev = float(df["revenue"].mean())
    r = scen_cfg.discount_rate_annual
    monthly_disc = _monthly_discount_rate(r)

    gp = 0.0
    for t in range(1, scen_cfg.horizon_months + 1):
        gp_t = mean_rev * scen_cfg.gross_margin
        gp += gp_t / ((1.0 + monthly_disc) ** t)
    return gp


def project_scenario_gp(
    revenue_df: pd.DataFrame,
    org_id: str,
    scen_cfg: ScenarioConfig,
    delta_ticket_pct: float = 0.0,
    delta_retention_pct: float = 0.0,
) -> float:
    df = revenue_df[revenue_df["org_id"] == org_id]
    if df.empty:
        return 0.0
    mean_rev = float(df["revenue"].mean())

    ticket_multiplier = 1.0 + delta_ticket_pct
    retention_multiplier = 1.0 + delta_retention_pct

    r = scen_cfg.discount_rate_annual
    monthly_disc = _monthly_discount_rate(r)

    gp = 0.0
    for t in range(1, scen_cfg.horizon_months + 1):
        gp_t = (
            mean_rev
            * ticket_multiplier
            * retention_multiplier
            * scen_cfg.gross_margin
        )
        gp += gp_t / ((1.0 + monthly_disc) ** t)
    return gp


@dataclass
class ActionScoringConfig:
    risk_penalty: float = 1.0


def score_actions(actions_df: pd.DataFrame, cfg: Optional[ActionScoringConfig] = None) -> pd.DataFrame:
    if cfg is None:
        cfg = ActionScoringConfig()

    df = actions_df.copy()
    eps = 1e-6
    denom = (df["cycle_time_months"].clip(lower=eps)) * (
        1.0 + cfg.risk_penalty * df["risk_score"].clip(lower=0.0)
    )
    df["decision_score"] = (df["igp_12m"] * df["probability"].clip(lower=0.0)) / denom
    return df
