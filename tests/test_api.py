"""End-to-end: run the whole pipeline on fake data, then call the API."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_config):
    from src.api import main
    from src.controllers.orchestrator import OrchestratorController
    OrchestratorController.run_all()
    main._cache["forecast"] = None
    return TestClient(main.app)


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["cache_loaded"] is True and body["data_stale"] is False


def test_forecast_and_filters(client):
    body = client.get("/api/v1/forecast").json()
    assert body["metadata"]["total_count"] == len(body["data"]) > 0
    first = body["data"][0]
    one = client.get("/api/v1/forecast", params={"product_id": first["product_id"]}).json()
    assert len(one["data"]) == 1


def test_history_metrics_mba(client):
    pid = client.get("/api/v1/forecast").json()["data"][0]["product_id"]
    assert len(client.get(f"/api/v1/products/{pid}/history").json()["data"]) == 90
    assert client.get("/api/v1/products/NOPE/history").status_code == 404
    assert "metrics" in client.get("/api/v1/metrics").json()["data"]
    assert client.get("/api/v1/mba").json()["data"]["summary"]["total_transactions"] > 0


def test_chat_without_key_explains_setup(client, monkeypatch):
    from src.config.config import config
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    r = client.post("/api/v1/chat", json={"message": "halo"})
    assert r.status_code == 503 and "LLM_API_KEY" in r.json()["detail"]
    assert client.post("/api/v1/chat", json={"message": "  "}).status_code == 400
