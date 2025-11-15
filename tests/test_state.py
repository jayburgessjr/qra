
import numpy as np
import pandas as pd

from src.qra.state import QRAStateEngine, QRAStateConfig


def make_synthetic_state_data():
    rng = np.random.default_rng(0)
    orgs = ["org_a", "org_b"]
    months = pd.period_range("2025-01", periods=4, freq="M")

    pricing_events = pd.DataFrame([
        {"org_id": "org_a", "old_price": 100.0, "new_price": 110.0, "volume_before": 500, "volume_after": 495},
        {"org_id": "org_b", "old_price": 80.0, "new_price": 85.0, "volume_before": 400, "volume_after": 380},
    ])

    funnel_rows = []
    for org in orgs:
        base = 1000 if org == "org_a" else 800
        for m in months:
            funnel_rows.append({"org_id": org, "month": m, "leads": int(base * rng.normal(1.0, 0.05))})
    funnel = pd.DataFrame(funnel_rows)

    retention_rows = []
    for org in orgs:
        base_customers = 1000 if org == "org_a" else 700
        for months_since in [0, 3, 6]:
            active = int(base_customers * (0.97 ** (months_since / 3)))
            retention_rows.append({
                "org_id": org,
                "cohort_month": "2024-01",
                "months_since_acquisition": months_since,
                "active_customers": active,
            })
    retention = pd.DataFrame(retention_rows)

    revenue_rows = []
    for org in orgs:
        ticket = 25 if org == "org_a" else 22
        for m in months:
            base_rev = ticket * (1000 if org == "org_a" else 800)
            rev = base_rev * rng.normal(1.0, 0.03)
            revenue_rows.append({"org_id": org, "month": m, "revenue": rev})
    revenue = pd.DataFrame(revenue_rows)

    return pricing_events, funnel, retention, revenue


def test_qra_state_basic_ranges():
    pricing, funnel, retention, revenue = make_synthetic_state_data()
    engine = QRAStateEngine(QRAStateConfig())
    result = engine.fit(pricing, funnel, retention, revenue)
    df = result.state_df

    assert set(df["org_id"]) == {"org_a", "org_b"}
    for col in ["epi", "rsi", "vri", "qra_health_score"]:
        assert (df[col] >= 0.0).all()
        assert (df[col] <= 100.0).all()
