"""Central configuration. Every value can be overridden with an environment variable (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return type(default)(value) if default is not None else value


class Config:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(ROOT_DIR, "data")

    # ---- Input --------------------------------------------------------------
    # Online Retail II (UCI). Accepts the original .xlsx (two sheets) or a .csv export.
    RAW_DATA_PATH = _env("RAW_DATA_PATH", os.path.join(DATA_DIR, "online_retail_II.xlsx"))
    # Optional country filter, e.g. "United Kingdom". Empty = all countries.
    COUNTRY = _env("COUNTRY", "")

    # ---- Generated files ----------------------------------------------------
    CLEAN_DATA_PATH = os.path.join(DATA_DIR, "transactions_clean.csv.gz")
    DAILY_DATA_PATH = os.path.join(DATA_DIR, "daily_demand.csv.gz")
    MODEL_PATH = os.path.join(DATA_DIR, "demand_model.pkl")
    FORECAST_PATH = os.path.join(DATA_DIR, "forecast_results.json")
    METRICS_PATH = os.path.join(DATA_DIR, "model_metrics.json")
    MBA_PATH = os.path.join(DATA_DIR, "mba_results.json")

    # ---- Scope --------------------------------------------------------------
    TOP_N_PRODUCTS = _env("TOP_N_PRODUCTS", 300)      # products modelled (by number of invoices)
    MBA_TOP_N_PRODUCTS = _env("MBA_TOP_N_PRODUCTS", 500)

    # ---- Forecast -----------------------------------------------------------
    MODEL = _env("MODEL", "sklearn")   # "sklearn" (default, HistGradientBoosting) or "xgboost"
    HORIZON_DAYS = 7          # forecast covers the next 7 days
    TEST_DAYS = 56            # last 8 weeks held out for evaluation

    # ---- Inventory policy (simulation + recommendations) ---------------------
    SERVICE_LEVEL_Z = 1.65    # ~95% service level
    REVIEW_DAYS = 14          # an order should cover lead time + 14 days
    LEAD_TIME_OPTIONS = (3, 5, 7, 10)   # supplier lead time, assigned per product
    OVERSTOCK_DAYS = 60
    DEADSTOCK_NO_SALE_DAYS = 60

    # ---- Market basket -------------------------------------------------------
    MBA_MIN_SUPPORT = 0.005
    MBA_MIN_CONFIDENCE = 0.2
    MBA_MIN_LIFT = 1.0
    MBA_MAX_RULES = 500

    # ---- API ------------------------------------------------------------------
    STALE_AFTER_HOURS = 24
    CACHE_TTL_SECONDS = 3600

    # ---- LLM ------------------------------------------------------------------
    # LLM_PROVIDER: "openai" (any OpenAI-compatible API: Groq, Gemini, OpenAI, ...) or "ollama".
    LLM_PROVIDER = _env("LLM_PROVIDER", "ollama" if os.getenv("OLLAMA_API_KEY") else "openai")
    LLM_API_KEY = _env("LLM_API_KEY", os.getenv("OLLAMA_API_KEY", ""))
    LLM_BASE_URL = _env("LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL", "https://api.groq.com/openai/v1"))
    LLM_MODEL = _env("LLM_MODEL", "llama-3.1-8b-instant")


config = Config()
