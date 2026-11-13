"""Retail Inventory AI - REST API.

Run from the project root:
    uvicorn src.api.main:app --reload
"""
import logging
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config.config import config
from src.controllers.orchestrator import OrchestratorController
from src.llm_engine.generator import LLMNotConfigured, generate_chat_response, llm_status
from src.repositories.data_repository import DataRepository, ModelRepository, file_age_hours
from src.repositories.mba_repository import MBARepository
from src.services.chat_context import build_context

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

app = FastAPI(
    title="Retail Inventory AI API",
    version="3.0.0",
    description="7-day demand forecast, stock recommendations, market basket analysis and an AI assistant "
                "for retail inventory, built on the Online Retail II dataset.",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_cache = {"forecast": None, "loaded_at": 0.0}


def _forecast() -> Optional[dict]:
    """Forecast from memory, reloaded from disk at most once per CACHE_TTL_SECONDS."""
    if _cache["forecast"] is None or time.time() - _cache["loaded_at"] > config.CACHE_TTL_SECONDS:
        _cache["forecast"] = ModelRepository.load_forecast()
        _cache["loaded_at"] = time.time()
    return _cache["forecast"]


def _require_forecast() -> dict:
    data = _forecast()
    if not data:
        raise HTTPException(503, "Belum ada hasil forecast. Jalankan pipeline: python -m src.controllers.orchestrator "
                                 "atau POST /api/v1/forecast/refresh.")
    return data


def _is_stale() -> bool:
    age = file_age_hours(config.FORECAST_PATH)
    return age is None or age > config.STALE_AFTER_HOURS


@app.get("/")
def root():
    return {"message": "Retail Inventory AI API is running", "docs": "/docs"}


@app.get("/api/v1/health")
def health():
    data = _forecast()
    return {
        "status": "ok",
        "cache_loaded": data is not None,
        "data_stale": _is_stale(),
        "forecast_age_hours": file_age_hours(config.FORECAST_PATH),
        "data_as_of": data.get("data_as_of") if data else None,
        "llm": llm_status(),
    }


@app.get("/api/v1/forecast")
def get_forecast(product_id: Optional[str] = None, category: Optional[str] = None):
    raw = _require_forecast()
    predictions = raw.get("predictions", [])
    if product_id:
        predictions = [p for p in predictions if p["product_id"].lower() == product_id.lower()]
    if category:
        predictions = [p for p in predictions if p["category"].lower() == category.lower()]
    return {
        "status": "success",
        "metadata": {
            "generated_at": raw.get("generated_at"),
            "data_as_of": raw.get("data_as_of"),
            "currency": raw.get("currency", "GBP"),
            "horizon_days": raw.get("horizon_days", config.HORIZON_DAYS),
            "model": raw.get("model"),
            "stale": _is_stale(),
            "total_count": len(predictions),
        },
        "data": predictions,
    }


@app.get("/api/v1/products/{product_id}/history")
def product_history(product_id: str, days: int = 90):
    """Daily sales, stock and lost sales of one product, for charts."""
    try:
        daily = DataRepository.load_daily()
    except FileNotFoundError:
        raise HTTPException(503, "Data harian belum ada. Jalankan pipeline terlebih dahulu.")
    rows = daily[daily["stock_code"].str.lower() == product_id.lower()].sort_values("date").tail(max(7, min(days, 400)))
    if rows.empty:
        raise HTTPException(404, f"Produk {product_id} tidak ditemukan.")
    return {
        "status": "success",
        "product_id": rows["stock_code"].iloc[0],
        "product_name": str(rows["description"].iloc[0]).title(),
        "data": [
            {"date": str(r.date.date()), "units_sold": int(r.units_sold), "stock": int(r.stock_qty),
             "lost_sales": int(r.lost_sales), "received": int(r.received)}
            for r in rows.itertuples()
        ],
    }


@app.get("/api/v1/metrics")
def get_metrics():
    data = ModelRepository.load_metrics()
    if not data:
        raise HTTPException(503, "Belum ada hasil evaluasi model. Jalankan pipeline terlebih dahulu.")
    return {"status": "success", "data": data}


@app.post("/api/v1/forecast/refresh")
def refresh_forecast(rebuild_data: bool = False):
    """Retrain and re-forecast. rebuild_data=true also re-reads the raw dataset (slower)."""
    try:
        if rebuild_data:
            OrchestratorController.run_data_pipeline()
        snapshot = OrchestratorController.run_ml_workflow()
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception("Pipeline failed")
        raise HTTPException(500, f"Gagal memperbarui forecast: {e}")
    _cache["forecast"], _cache["loaded_at"] = snapshot, time.time()
    return {"status": "success", "data_points": len(snapshot["predictions"]), "data_as_of": snapshot["data_as_of"]}


@app.get("/api/v1/mba")
def get_mba():
    data = MBARepository.load()
    if not data:
        raise HTTPException(503, "Data market basket belum ada. Jalankan POST /api/v1/mba/refresh terlebih dahulu.")
    return {"status": "success", "data": data}


@app.post("/api/v1/mba/refresh")
def refresh_mba(min_support: float = config.MBA_MIN_SUPPORT, min_confidence: float = config.MBA_MIN_CONFIDENCE,
                min_lift: float = config.MBA_MIN_LIFT):
    try:
        result = OrchestratorController.run_mba_workflow(
            min_support=min_support, min_confidence=min_confidence, min_lift=min_lift)
    except FileNotFoundError:
        raise HTTPException(400, "Transaksi bersih belum ada. Jalankan pipeline data terlebih dahulu.")
    return {"status": "success", "total_rules": result["summary"]["total_rules"],
            "total_transactions": result["summary"]["total_transactions"]}


# ---------------------------------------------------------------- chat

class ChatRequest(BaseModel):
    message: str
    inventory_context: Optional[dict] = None


@app.post("/api/v1/chat")
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(400, "Pesan tidak boleh kosong.")
    forecast = _forecast()
    context = build_context(message, forecast) if forecast else (req.inventory_context or None)
    try:
        return {"status": "success", "response": generate_chat_response(message, context)}
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
