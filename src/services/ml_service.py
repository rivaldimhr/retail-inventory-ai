"""7-day demand forecast: training, time-based evaluation against baselines, prediction."""
from datetime import datetime

import numpy as np
import pandas as pd

from src.config.config import config
from src.services.feature_service import FEATURES, TARGET


def make_model():
    """Gradient boosting with a Poisson loss: demand is a count, and Poisson keeps the forecast
    unbiased on average (important for stock decisions; a log-target model under-forecasts).
    Set MODEL=xgboost in .env to use XGBoost with the same objective."""
    if config.MODEL == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            objective="count:poisson", n_estimators=600, learning_rate=0.03, max_depth=4,
            min_child_weight=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
            n_jobs=-1, random_state=42,
        )
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(
        loss="poisson", max_iter=600, learning_rate=0.03, max_leaf_nodes=15,
        min_samples_leaf=200, l2_regularization=1.0, random_state=42,
    )


def model_name(model) -> str:
    return f"{type(model).__name__} (Poisson)"


def fit(df: pd.DataFrame):
    model = make_model()
    model.fit(df[FEATURES], df[TARGET])
    return model


def predict(model, df: pd.DataFrame) -> np.ndarray:
    return np.clip(model.predict(df[FEATURES]), 0, None)


def _scores(y: np.ndarray, pred: np.ndarray) -> dict:
    err = np.abs(y - pred)
    total = y.sum()
    return {
        "mae": round(float(err.mean()), 3),
        "rmse": round(float(np.sqrt(((y - pred) ** 2).mean())), 3),
        "wape": round(float(err.sum() / total), 4) if total > 0 else None,
        "bias": round(float((pred.sum() - total) / total), 4) if total > 0 else None,
    }


def evaluate(features: pd.DataFrame) -> dict:
    """Hold out the last TEST_DAYS days. Training rows end HORIZON days before the test period,
    so no training target overlaps the test weeks. Compare with two simple baselines."""
    labeled = features.dropna(subset=[TARGET])
    last = labeled["date"].max()
    test_start = last - pd.Timedelta(days=config.TEST_DAYS - 1)
    train_end = test_start - pd.Timedelta(days=config.HORIZON_DAYS + 1)
    train = labeled[labeled["date"] <= train_end]
    test = labeled[labeled["date"] >= test_start]

    model = fit(train)
    y = test[TARGET].to_numpy()
    results = {
        "model": _scores(y, predict(model, test)),
        "baseline_last_7_days": _scores(y, test["mean_7"].to_numpy() * config.HORIZON_DAYS),
        "baseline_avg_28_days": _scores(y, test["mean_28"].to_numpy() * config.HORIZON_DAYS),
    }
    best_baseline = min(results["baseline_last_7_days"]["mae"], results["baseline_avg_28_days"]["mae"])
    improvement = (best_baseline - results["model"]["mae"]) / best_baseline if best_baseline else 0.0

    by_category = []
    test = test.assign(_pred=predict(model, test))
    for cat, part in test.groupby("category"):
        s = _scores(part[TARGET].to_numpy(), part["_pred"].to_numpy())
        by_category.append({"category": cat, "mae": s["mae"], "wape": s["wape"], "rows": int(len(part))})

    return {
        "generated_at": datetime.now().isoformat(),
        "algorithm": model_name(model),
        "target": f"units sold in the next {config.HORIZON_DAYS} days, per product",
        "train_period": [str(train["date"].min().date()), str(train_end.date())],
        "test_period": [str(test_start.date()), str(last.date())],
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "metrics": results,
        "mae_improvement_vs_best_baseline": round(float(improvement), 4),
        "by_category": sorted(by_category, key=lambda r: r["category"]),
    }


def train_final(features: pd.DataFrame):
    """Retrain on every labeled day before forecasting the real future."""
    return fit(features.dropna(subset=[TARGET]))


def forecast_latest(model, features: pd.DataFrame) -> pd.DataFrame:
    """Forecast the next 7 days from the last observed day of every product."""
    latest = features[features["date"] == features["date"].max()].copy()
    latest["forecast_7d"] = predict(model, latest)
    return latest
