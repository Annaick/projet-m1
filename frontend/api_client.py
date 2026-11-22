"""Appels à l'API FastAPI. L'interface ne parle qu'à l'API, jamais directement à Ollama ou aux bases."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_health() -> dict | None:
    """Renvoie l'état de l'API, ou None si elle ne répond pas."""
    try:
        response = httpx.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        return None
