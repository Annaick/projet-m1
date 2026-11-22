from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_repond_meme_sans_ollama():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert "ok" in body["ollama"]
