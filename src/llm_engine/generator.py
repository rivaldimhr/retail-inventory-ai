import os
import logging

import requests
from dotenv import load_dotenv

from src.llm_engine.prompts import (
    SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    build_user_prompt,
    build_chat_prompt,
)

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
BASE_URL = os.getenv("OLLAMA_BASE_URL")
MODEL_NAME = "nemotron-3-super"

logger = logging.getLogger(__name__)


def _call_llm(system_prompt: str, user_content: str, timeout: int = 60) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
    }
    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }
    try:
        response = requests.post(
            url=f"{BASE_URL}/api/chat", headers=headers, json=body, timeout=timeout
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise RuntimeError("LLM request timed out.")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Cannot connect to LLM service: {e}")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        raise RuntimeError(f"LLM HTTP error {status}: {e.response.text[:200] if e.response is not None else ''}")
    except KeyError:
        raise RuntimeError("Unexpected response format from LLM service.")


def generate_recommendation(prediction: dict) -> str:
    try:
        return _call_llm(SYSTEM_PROMPT, build_user_prompt(prediction))
    except RuntimeError as e:
        logger.error("generate_recommendation failed: %s", e)
        return f"[Error] {e}"


def generate_chat_response(message: str, inventory_context: dict | None = None, history: list | None = None) -> str:
    user_content = build_chat_prompt(message, inventory_context)
    try:
        return _call_llm(CHAT_SYSTEM_PROMPT, user_content, timeout=45)
    except RuntimeError as e:
        logger.error("generate_chat_response failed: %s", e)
        raise


def batch_generate(forecast: dict) -> list:
    results = []
    for prediction in forecast.get("predictions", []):
        recommendation = generate_recommendation(prediction)
        results.append(
            {
                "product_id": prediction["product_id"],
                "recommendation": recommendation,
            }
        )
    return results
