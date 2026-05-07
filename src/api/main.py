from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.repositories.data_repository import ModelRepository
from src.controllers.orchestrator import OrchestratorController
from src.llm_engine.generator import generate_chat_response
from typing import Optional
import time
import logging

# =========================
# CONFIG LOGGING
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# INIT APP
# =========================
app = FastAPI(
    title="AIforBusiness Forecast API",
    version="2.0.0",
    description="Retail Inventory Optimization API with ML Forecasting"
)

# =========================
# CACHE CONFIG
# =========================
forecast_cache = {
    "data": None,
    "loaded_at": None
}

CACHE_TTL_SECONDS = 3600  # 1 jam

# =========================
# CORS (Dashboard Integration)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # bisa dibatasi di production
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# CACHE HANDLER
# =========================


def refresh_cache() -> bool:
    try:
        data = ModelRepository.load_forecast()

        if not data or "error" in data:
            logging.warning("Forecast data missing or outdated")
            return False

        forecast_cache["data"] = data
        forecast_cache["loaded_at"] = time.time()

        logging.info("Cache successfully refreshed")
        return True

    except Exception as e:
        logging.error(f"Failed to load forecast: {e}")
        return False


def is_cache_expired() -> bool:
    if not forecast_cache["loaded_at"]:
        return True

    return (time.time() - forecast_cache["loaded_at"]) > CACHE_TTL_SECONDS


# =========================
# STARTUP EVENT
# =========================
@app.on_event("startup")
async def startup_event():
    logging.info("Starting API & loading cache...")
    refresh_cache()


# =========================
# ROOT ENDPOINT
# =========================
@app.get("/")
async def root():
    return {
        "message": "AIforBusiness API is running",
        "status": "active",
        "workload": "D"
    }


# =========================
# GET FORECAST
# =========================
@app.get("/api/v1/forecast")
async def get_forecast(
    product_id: Optional[str] = None,
    category: Optional[str] = None
):
    # Refresh cache jika kosong / expired
    if not forecast_cache["data"] or is_cache_expired():
        if not refresh_cache():
            raise HTTPException(
                status_code=503,
                detail="Forecast data unavailable or outdated. Please refresh."
            )

    raw_data = forecast_cache["data"]
    predictions = raw_data.get("predictions", [])

    # =========================
    # FILTERING
    # =========================
    if product_id:
        predictions = [
            p for p in predictions
            if p.get("product_id", "").lower() == product_id.lower()
        ]

    if category:
        predictions = [
            p for p in predictions
            if p.get("category", "").lower() == category.lower()
        ]

    return {
        "status": "success",
        "metadata": {
            "generated_at": raw_data.get("generated_at"),
            "cached_at": time.strftime(
                '%Y-%m-%d %H:%M:%S',
                time.localtime(forecast_cache["loaded_at"])
            ),
            "total_count": len(predictions)
        },
        "data": predictions
    }


# =========================
# CHAT ENDPOINT
# =========================

class ChatRequest(BaseModel):
    message: str
    inventory_context: Optional[dict] = None


@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    context = req.inventory_context
    if context is None and forecast_cache.get("data"):
        raw = forecast_cache["data"]
        predictions = raw.get("predictions", [])
        stockout = [p for p in predictions if p.get("risk_flags", {}).get("stockout_risk")]
        overstock = [p for p in predictions if p.get("risk_flags", {}).get("overstock_risk")]
        deadstock = [p for p in predictions if p.get("risk_flags", {}).get("deadstock_risk")]
        lost_sales = [p for p in predictions if p.get("risk_flags", {}).get("missed_revenue_flag")]
        top_risks = sorted(
            [p for p in predictions if any(p.get("risk_flags", {}).values())],
            key=lambda p: p.get("stock_coverage_days", 999)
        )
        context = {
            "total_count": len(predictions),
            "stockout_count": len(stockout),
            "overstock_count": len(overstock),
            "deadstock_count": len(deadstock),
            "lost_sales_count": len(lost_sales),
            "generated_at": raw.get("generated_at", "unknown"),
            "top_risks": top_risks[:10],
        }

    try:
        response_text = generate_chat_response(req.message.strip(), context)
        return {"status": "success", "response": response_text}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


# =========================
# REFRESH PIPELINE (IMPORTANT)
# =========================
@app.post("/api/v1/forecast/refresh")
async def refresh_forecast():
    try:
        logging.info("Running full pipeline...")

        OrchestratorController.run_data_pipeline()
        forecast = OrchestratorController.run_ml_workflow()

        refresh_cache()

        return {
            "status": "success",
            "message": "Forecast successfully refreshed",
            "data_points": len(forecast.get("predictions", []))
        }

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh forecast: {str(e)}"
        )
