import os

import requests
from dotenv import load_dotenv

from src.llm_engine.prompts import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
BASE_URL = os.getenv("OLLAMA_BASE_URL")
MODEL_NAME = "nemotron-3-super"


def generate_recommendation(prediction: dict) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
    }

    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(prediction)},
        ],
        "stream": False,
    }

    try:
        response = requests.post(
            url=f"{BASE_URL}/api/chat", headers=headers, json=body, timeout=60
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "[Error] Request timed out."
    except requests.exceptions.HTTPError as e:
        return f"[Error] HTTP error: {e.response.status_code}"
    except KeyError:
        return "[Error] Unexpected response format."


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
