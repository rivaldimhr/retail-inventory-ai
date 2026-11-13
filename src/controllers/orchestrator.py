"""Runs the full workflow: raw data -> daily demand + stock -> forecast + decisions -> market basket.

Usage (from the project root):
    python -m src.controllers.orchestrator
"""
import logging
import time

from src.config.config import config
from src.data_pipeline.loader import clean_transactions, read_raw
from src.data_pipeline.pipeline import build_daily_demand, select_top_products
from src.repositories.data_repository import DataRepository, ModelRepository
from src.repositories.mba_repository import MBARepository
from src.services import inventory_service, mba_service, ml_service
from src.services.feature_service import add_features
from src.services.stock_simulation import simulate_stock

log = logging.getLogger("orchestrator")


class OrchestratorController:
    @staticmethod
    def run_data_pipeline():
        t0 = time.time()
        log.info("Reading %s", config.RAW_DATA_PATH)
        tx = clean_transactions(read_raw(config.RAW_DATA_PATH), country=config.COUNTRY)
        DataRepository.save_clean(tx)
        log.info("Clean transactions: %d lines, %d invoices, %d products",
                 len(tx), tx["invoice"].nunique(), tx["stock_code"].nunique())

        products = select_top_products(tx, config.TOP_N_PRODUCTS)
        daily = simulate_stock(build_daily_demand(tx, products))
        DataRepository.save_daily(daily)
        log.info("Daily demand + stock simulation for %d products (%.0fs)", len(products), time.time() - t0)
        return daily

    @staticmethod
    def run_ml_workflow():
        t0 = time.time()
        daily = DataRepository.load_daily()
        features = add_features(daily)

        metrics = ml_service.evaluate(features)
        ModelRepository.save_metrics(metrics)
        log.info("Evaluation: model MAE %.2f vs best baseline (improvement %.1f%%)",
                 metrics["metrics"]["model"]["mae"], metrics["mae_improvement_vs_best_baseline"] * 100)

        model = ml_service.train_final(features)
        ModelRepository.save_model(model)
        latest = ml_service.forecast_latest(model, features)
        snapshot = inventory_service.build_snapshot(daily, latest)
        snapshot["model"] = {
            "algorithm": metrics["algorithm"],
            "mae_7d": metrics["metrics"]["model"]["mae"],
            "wape_7d": metrics["metrics"]["model"]["wape"],
            "mae_improvement_vs_best_baseline": metrics["mae_improvement_vs_best_baseline"],
        }
        ModelRepository.save_forecast(snapshot)
        log.info("Forecast for %d products saved (%.0fs)", len(snapshot["predictions"]), time.time() - t0)
        return snapshot

    @staticmethod
    def run_mba_workflow(**params):
        result = mba_service.run(DataRepository.load_clean(), **params)
        MBARepository.save(result)
        log.info("Market basket: %d rules from %d invoices",
                 result["summary"]["total_rules"], result["summary"]["total_transactions"])
        return result

    @classmethod
    def run_all(cls):
        cls.run_data_pipeline()
        cls.run_ml_workflow()
        cls.run_mba_workflow()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    OrchestratorController.run_all()
