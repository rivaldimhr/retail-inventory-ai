"""LLM client. Works with any OpenAI-compatible API (Groq, Gemini, OpenAI, OpenRouter, ...)
or with Ollama. Configure in .env:

    LLM_PROVIDER=openai                     # or: ollama
    LLM_BASE_URL=https://api.groq.com/openai/v1
    LLM_API_KEY=...
    LLM_MODEL=llama-3.1-8b-instant
"""
import logging

import requests

from src.config.config import config
from src.llm_engine.prompts import CHAT_SYSTEM_PROMPT, build_chat_prompt

log = logging.getLogger(__name__)


class LLMNotConfigured(RuntimeError):
    pass


def llm_status() -> dict:
    configured = bool(config.LLM_API_KEY) or config.LLM_PROVIDER == "ollama"
    return {"provider": config.LLM_PROVIDER, "model": config.LLM_MODEL, "configured": configured}


def _call_llm(system_prompt: str, user_content: str, timeout: int = 45) -> str:
    if not llm_status()["configured"]:
        raise LLMNotConfigured(
            "Chat AI belum dikonfigurasi. Isi LLM_API_KEY (dan LLM_BASE_URL / LLM_MODEL) di file .env, lalu restart backend."
        )
    base = config.LLM_BASE_URL.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]

    if config.LLM_PROVIDER == "ollama":
        url, body = f"{base}/api/chat", {"model": config.LLM_MODEL, "messages": messages, "stream": False}
    else:
        url, body = f"{base}/chat/completions", {"model": config.LLM_MODEL, "messages": messages, "temperature": 0.3}

    try:
        res = requests.post(url, headers=headers, json=body, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        if config.LLM_PROVIDER == "ollama":
            return data["message"]["content"].strip()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise RuntimeError("Layanan AI tidak merespons (timeout). Coba lagi.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Tidak bisa terhubung ke layanan AI. Periksa LLM_BASE_URL.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        detail = e.response.text[:200] if e.response is not None else ""
        raise RuntimeError(f"Layanan AI mengembalikan error {status}: {detail}")
    except (KeyError, IndexError, ValueError):
        raise RuntimeError("Format jawaban dari layanan AI tidak dikenali.")


def generate_chat_response(message: str, inventory_context: dict = None) -> str:
    return _call_llm(CHAT_SYSTEM_PROMPT, build_chat_prompt(message, inventory_context))
