import json

import numpy as np
import pandas as pd
import pytest

from src.data_pipeline.loader import clean_transactions, normalize_columns
from src.data_pipeline.pipeline import build_daily_demand, categorize, select_top_products
from src.services import inventory_service, mba_service, ml_service
from src.services.chat_context import build_context
from src.services.feature_service import FEATURES, TARGET, add_features
from src.services.stock_simulation import lead_time_for, simulate_product
from src.llm_engine.prompts import build_chat_prompt


@pytest.fixture(scope="module")
def tx(raw_df):
    return clean_transactions(normalize_columns(raw_df))


@pytest.fixture(scope="module")
def daily(tx):
    from src.services.stock_simulation import simulate_stock
    return simulate_stock(build_daily_demand(tx, select_top_products(tx, 16)))


# ---------------------------------------------------------------- cleaning

def test_cleaning_removes_cancellations_fees_and_bad_prices(tx):
    assert not tx["invoice"].str.startswith("C").any()
    assert set(tx["stock_code"]) <= {"85123A", "22423", "85099B", "84879", "47566", "20725", "22720", "21212",
                                     "23084", "22086", "22197", "21034", "22382", "23203", "22457", "21931"}
    assert (tx["quantity"] > 0).all() and (tx["price"] > 0).all()


def test_old_column_names_are_accepted():
    df = pd.DataFrame({"InvoiceNo": ["1"], "StockCode": ["22423"], "Description": ["X"], "Quantity": [1],
                       "InvoiceDate": ["2011-01-01"], "UnitPrice": [1.0], "CustomerID": [1], "Country": ["UK"]})
    assert {"invoice", "price", "customer_id"} <= set(normalize_columns(df).columns)


@pytest.mark.parametrize("desc,expected", [
    ("SET OF 3 CAKE TINS PANTRY DESIGN", "Baking & party"),
    ("PAPER CHAIN KIT 50'S CHRISTMAS", "Christmas & seasonal"),
    ("JUMBO BAG RED RETROSPOT", "Bags & storage"),
    ("OIL PAINTING VINTAGE", "Other"),          # 'TIN' inside a word must not match
])
def test_categorize(desc, expected):
    assert categorize(desc) == expected


def test_daily_table_is_complete(daily):
    days = daily["date"].nunique()
    assert len(daily) == days * daily["stock_code"].nunique()
    assert daily["units_sold"].ge(0).all()


# ---------------------------------------------------------------- simulation

def test_simulation_never_goes_negative_and_logs_lost_sales():
    units = np.array([5] * 30 + [200] * 3 + [5] * 30, dtype=float)
    stock, on_order, lost, received, ordered = simulate_product(units, lead_time=5)
    assert (stock >= 0).all()
    assert lost.sum() > 0                       # the spike cannot be fully served
    assert ordered.sum() > 0 and received.sum() > 0
    # stock balance holds every day: today = yesterday + received - sold
    sold = units - lost
    assert np.allclose(stock[1:], stock[:-1] + received[1:] - sold[1:])


def test_lead_time_is_stable_and_valid():
    assert lead_time_for("22423") == lead_time_for("22423")
    assert lead_time_for("22423") in (3, 5, 7, 10)


# ---------------------------------------------------------------- features / model

def test_target_is_sum_of_next_7_days(daily):
    f = add_features(daily)
    one = f[f["stock_code"] == f["stock_code"].iloc[0]].reset_index(drop=True)
    i = 100
    assert one.loc[i, TARGET] == one.loc[i + 1:i + 7, "units_sold"].sum()
    assert one[TARGET].tail(7).isna().all()      # future not observed


def test_features_do_not_use_the_future(daily):
    f1 = add_features(daily)
    cut = daily["date"].max() - pd.Timedelta(days=30)
    f2 = add_features(daily[daily["date"] <= cut])
    a = f1[f1["date"] == cut].sort_values("stock_code")[FEATURES].reset_index(drop=True)
    b = f2[f2["date"] == cut].sort_values("stock_code")[FEATURES].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_evaluation_reports_model_and_baselines(daily):
    m = ml_service.evaluate(add_features(daily))
    assert {"model", "baseline_last_7_days", "baseline_avg_28_days"} <= set(m["metrics"])
    assert m["test_period"][0] > m["train_period"][1]
    assert m["metrics"]["model"]["mae"] >= 0


# ---------------------------------------------------------------- decisions

def _snapshot(daily, forecast_7d=None):
    f = add_features(daily)
    latest = f[f["date"] == f["date"].max()].copy()
    latest["forecast_7d"] = forecast_7d if forecast_7d is not None else latest["mean_28"] * 7
    return inventory_service.build_snapshot(daily, latest)


def test_snapshot_schema(daily):
    snap = _snapshot(daily)
    p = snap["predictions"][0]
    for key in ("product_id", "product_name", "category", "current_stock", "recommended_order_qty",
                "revenue_at_risk", "stock_coverage_days", "risk_flags", "demand_signal"):
        assert key in p
    json.dumps(snap)  # serialisable


def test_high_forecast_triggers_stockout_and_order(daily):
    snap = _snapshot(daily, forecast_7d=1e6)
    assert all(p["risk_flags"]["stockout_risk"] for p in snap["predictions"])
    assert all(p["recommended_order_qty"] > 0 for p in snap["predictions"])
    assert all(p["revenue_at_risk"] > 0 for p in snap["predictions"])


def test_zero_forecast_means_no_order(daily):
    snap = _snapshot(daily, forecast_7d=0.0)
    assert all(p["recommended_order_qty"] == 0 for p in snap["predictions"])
    assert not any(p["risk_flags"]["stockout_risk"] for p in snap["predictions"])


# ---------------------------------------------------------------- market basket

def test_mba_finds_planted_pairs(tx):
    res = mba_service.run(tx, min_support=0.01, min_confidence=0.2, min_lift=1.0, top_n=50)
    pairs = {(r["antecedent_codes"][0], r["consequent_codes"][0]) for r in res["rules"]}
    assert ("23203", "85099B") in pairs or ("85099B", "23203") in pairs
    for r in res["rules"]:
        assert 0 < r["support"] <= 1 and 0 < r["confidence"] <= 1 and r["lift"] >= 1


# ---------------------------------------------------------------- chat

def test_chat_context_includes_named_product(daily):
    snap = _snapshot(daily)
    name = snap["predictions"][3]["product_name"]
    ctx = build_context(f"Bagaimana stok {name.lower()}?", snap)
    assert ctx["mentioned_products"][0]["product_name"] == name
    prompt = build_chat_prompt("test", ctx)
    assert name in prompt and "User question: test" in prompt
