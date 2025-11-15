
import pandas as pd

from src.qra.scenario import (
    ScenarioConfig,
    project_baseline_gp,
    project_scenario_gp,
    score_actions,
    ActionScoringConfig,
)


def make_revenue_df():
    return pd.DataFrame({
        "org_id": ["org_x"] * 6,
        "month": pd.period_range("2024-01", periods=6, freq="M"),
        "revenue": [10_000, 10_500, 9_800, 10_200, 10_400, 10_100],
    })


def test_baseline_vs_scenario_gp_increases():
    revenue_df = make_revenue_df()
    cfg = ScenarioConfig(horizon_months=12)
    base_gp = project_baseline_gp(revenue_df, "org_x", cfg)
    scen_gp = project_scenario_gp(
        revenue_df,
        "org_x",
        cfg,
        delta_ticket_pct=0.05,
        delta_retention_pct=0.02,
    )
    assert scen_gp > base_gp


def test_action_scoring_orders_by_decision_score():
    actions = pd.DataFrame({
        "org_id": ["org_x", "org_x"],
        "action_id": ["a1", "a2"],
        "igp_12m": [100_000, 50_000],
        "probability": [0.8, 0.9],
        "cycle_time_months": [6, 3],
        "risk_score": [0.2, 0.5],
    })
    scored = score_actions(actions, ActionScoringConfig(risk_penalty=1.0))
    scored_sorted = scored.sort_values("decision_score", ascending=False)
    top_action = scored_sorted.iloc[0]["action_id"]
    assert top_action == "a1"
