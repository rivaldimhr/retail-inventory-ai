import json
import os
import pickle
import time

import pandas as pd

from src.config.config import config


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _read_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def file_age_hours(path):
    if not os.path.exists(path):
        return None
    return round((time.time() - os.path.getmtime(path)) / 3600, 1)


class DataRepository:
    @staticmethod
    def save_clean(df: pd.DataFrame):
        df.to_csv(config.CLEAN_DATA_PATH, index=False)

    @staticmethod
    def load_clean() -> pd.DataFrame:
        return pd.read_csv(config.CLEAN_DATA_PATH, parse_dates=["invoice_date", "date"],
                           dtype={"invoice": str, "stock_code": str})

    @staticmethod
    def save_daily(df: pd.DataFrame):
        df.to_csv(config.DAILY_DATA_PATH, index=False)

    @staticmethod
    def load_daily() -> pd.DataFrame:
        return pd.read_csv(config.DAILY_DATA_PATH, parse_dates=["date"], dtype={"stock_code": str})


class ModelRepository:
    @staticmethod
    def save_model(model):
        with open(config.MODEL_PATH, "wb") as f:
            pickle.dump(model, f)

    @staticmethod
    def save_forecast(data: dict):
        _write_json(config.FORECAST_PATH, data)

    @staticmethod
    def load_forecast():
        """Returns the forecast even when it is old; callers decide what 'stale' means."""
        return _read_json(config.FORECAST_PATH)

    @staticmethod
    def save_metrics(data: dict):
        _write_json(config.METRICS_PATH, data)

    @staticmethod
    def load_metrics():
        return _read_json(config.METRICS_PATH)
