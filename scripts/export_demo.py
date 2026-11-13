"""Export pipeline results as static JSON for the demo build (no backend needed).

Run after the pipeline:
    python -m src.controllers.orchestrator
    python scripts/export_demo.py

Writes public/demo/{forecast,mba,metrics,history}.json. The demo build
(VITE_DEMO=true npm run build) reads these files instead of calling the API.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config import config  # noqa: E402
from src.repositories.data_repository import DataRepository, ModelRepository  # noqa: E402
from src.repositories.mba_repository import MBARepository  # noqa: E402

OUT = os.path.join(config.ROOT_DIR, "public", "demo")
HISTORY_DAYS = 90


def main():
    os.makedirs(OUT, exist_ok=True)
    forecast = ModelRepository.load_forecast()
    if not forecast:
        raise SystemExit("No forecast found. Run: python -m src.controllers.orchestrator")

    response = {
        "status": "success",
        "metadata": {
            "generated_at": forecast["generated_at"],
            "data_as_of": forecast["data_as_of"],
            "currency": forecast.get("currency", "GBP"),
            "horizon_days": forecast.get("horizon_days", config.HORIZON_DAYS),
            "model": forecast.get("model"),
            "stale": False,
            "total_count": len(forecast["predictions"]),
        },
        "data": forecast["predictions"],
    }
    _dump("forecast.json", response)
    _dump("mba.json", {"status": "success", "data": MBARepository.load()})
    _dump("metrics.json", {"status": "success", "data": ModelRepository.load_metrics()})

    daily = DataRepository.load_daily()
    history = {}
    for code, g in daily.sort_values("date").groupby("stock_code"):
        g = g.tail(HISTORY_DAYS)
        history[code] = [
            [str(r.date.date()), int(r.units_sold), int(r.stock_qty), int(r.lost_sales), int(r.received)]
            for r in g.itertuples()
        ]
    _dump("history.json", {"columns": ["date", "units_sold", "stock", "lost_sales", "received"], "data": history})


def _dump(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"{name}: {os.path.getsize(path) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
