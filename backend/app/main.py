"""Point d'entrée de l'API FastAPI."""

import httpx
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Assistant documentaire RAG",
    description="API du moteur RAG local : conversations, base de connaissances, paramètres de l'IA.",
    version="0.1.0",
)


@app.get("/health", tags=["système"])
def health() -> dict:
    """État de l'API et des services dont elle dépend."""
    try:
        response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        ollama = {"ok": True, "models": models}
    except httpx.HTTPError as exc:
        ollama = {"ok": False, "error": str(exc)}

    return {"api": "ok", "ollama": ollama}
