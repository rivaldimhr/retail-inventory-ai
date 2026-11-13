import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config import config  # noqa: E402
from tests.fake_data import make_raw  # noqa: E402


@pytest.fixture(scope="session")
def raw_df():
    return make_raw()


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch, raw_df):
    """Point every data path at a temporary folder holding a fake Online Retail II CSV."""
    raw_path = tmp_path / "online_retail_II.csv"
    raw_df.to_csv(raw_path, index=False)
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "RAW_DATA_PATH", str(raw_path))
    for attr, name in [
        ("CLEAN_DATA_PATH", "transactions_clean.csv.gz"), ("DAILY_DATA_PATH", "daily_demand.csv.gz"),
        ("MODEL_PATH", "demand_model.pkl"), ("FORECAST_PATH", "forecast_results.json"),
        ("METRICS_PATH", "model_metrics.json"), ("MBA_PATH", "mba_results.json"),
    ]:
        monkeypatch.setattr(config, attr, str(tmp_path / name))
    monkeypatch.setattr(config, "TOP_N_PRODUCTS", 16)
    return config
