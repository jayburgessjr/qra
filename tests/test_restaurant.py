
import numpy as np
import pandas as pd

from src.qra.restaurant import (
    RestaurantQRAEngine,
    RestaurantQRAConfig,
    estimate_loglog_elasticity,
    estimate_exponential_churn,
)


def make_restaurant_data():
    rng = np.random.default_rng(0)
    orgs = ["loc_downtown", "loc_suburb"]

    price_rows = []
    for org in orgs:
        base_price = 28 if org == "loc_downtown" else 22
        base_qty = 4000 if org == "loc_downtown" else 2500
        for pct in [-0.05, 0.0, 0.05]:
            price = base_price * (1 + pct)
            qty = base_qty * (price / base_price) ** -0.8 * rng.normal(1.0, 0.02)
            price_rows.append({"org_id": org, "price": price, "quantity": max(qty, 10.0)})
    price_obs = pd.DataFrame(price_rows)

    months = pd.period_range("2024-01", periods=6, freq="M")
    funnel_rows = []
    for org in orgs:
        base = 4200 if org == "loc_downtown" else 2600
        for m in months:
            funnel_rows.append({"org_id": org, "month": m, "leads": int(base * rng.normal(1.0, 0.04))})
    funnel = pd.DataFrame(funnel_rows)

    retention_rows = []
    for org in orgs:
        base_customers = 2000 if org == "loc_downtown" else 1400
        hazard = 0.06 if org == "loc_downtown" else 0.08
        for months_since in [0, 3, 6]:
            active = int(base_customers * np.exp(-hazard * (months_since / 3)))
            retention_rows.append({
                "org_id": org,
                "cohort_month": "2024-01",
                "months_since_acquisition": months_since,
                "active_customers": active,
            })
    retention = pd.DataFrame(retention_rows)

    revenue_rows = []
    for org in orgs:
        ticket = 28 if org == "loc_downtown" else 22
        base_leads = 4200 if org == "loc_downtown" else 2600
        for m in months:
            rev = ticket * base_leads * rng.normal(1.0, 0.03)
            revenue_rows.append({"org_id": org, "month": m, "revenue": rev})
    revenue = pd.DataFrame(revenue_rows)

    return price_obs, funnel, retention, revenue


def test_restaurant_elasticity_sign():
    price_obs, _, _, _ = make_restaurant_data()
    eps = estimate_loglog_elasticity(price_obs)
    assert (eps < 0).all()


def test_restaurant_churn_positive_and_less_than_one():
    _, _, retention, _ = make_restaurant_data()
    churn = estimate_exponential_churn(retention)
    assert (churn > 0).all()
    assert (churn < 1).all()


def test_restaurant_qra_health_in_range():
    price_obs, funnel, retention, revenue = make_restaurant_data()
    engine = RestaurantQRAEngine(RestaurantQRAConfig())
    result = engine.build_state(price_obs, funnel, retention, revenue)
    df = result.state_df
    assert (df["qra_health_score"] >= 0.0).all()
    assert (df["qra_health_score"] <= 100.0).all()
