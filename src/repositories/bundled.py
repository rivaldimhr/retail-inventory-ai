"""Results bundled in the repository (public/demo/*.json, exported from the real dataset).

The API falls back to these when the pipeline has not been run on the server, so a deployed
backend (e.g. on Render) works without the dataset. Run the pipeline to replace them.
"""
import json
import os

from src.config.config import config

DEMO_DIR = os.path.join(config.ROOT_DIR, "public", "demo")


def _load(name):
    path = os.path.join(DEMO_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def forecast():
    data = _load("forecast.json")
    if not data:
        return None
    meta = data["metadata"]
    return {
        "generated_at": meta["generated_at"],
        "data_as_of": meta["data_as_of"],
        "currency": meta.get("currency", "GBP"),
        "horizon_days": meta.get("horizon_days", config.HORIZON_DAYS),
        "model": meta.get("model"),
        "predictions": data["data"],
        "source": "bundled",
    }


def metrics():
    data = _load("metrics.json")
    return data["data"] if data else None


def mba():
    data = _load("mba.json")
    return data["data"] if data else None


def history(product_id: str, days: int):
    data = _load("history.json")
    if not data:
        return None
    match = next((k for k in data["data"] if k.lower() == product_id.lower()), None)
    if match is None:
        return []
    rows = [dict(zip(data["columns"], r)) for r in data["data"][match][-days:]]
    name = next((p["product_name"] for p in (forecast() or {}).get("predictions", []) if p["product_id"] == match), match)
    return {"product_id": match, "product_name": name, "data": rows}
