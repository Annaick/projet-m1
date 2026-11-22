"""Client Ollama minimal : embeddings et génération en streaming."""
import json
from collections.abc import Iterator

import httpx

from app.config import settings


class OllamaError(Exception):
    pass


def _post(path: str, payload: dict, timeout: float = 300) -> dict:
    try:
        response = httpx.post(f"{settings.ollama_url}{path}", json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama injoignable ou en erreur : {exc}") from exc
    return response.json()


def embed(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        data = _post("/api/embed", {"model": settings.embedding_model, "input": texts[i : i + batch_size]})
        vectors.extend(data["embeddings"])
    return vectors


def chat_stream(messages: list[dict], model: str, temperature: float) -> Iterator[str]:
    payload = {"model": model, "messages": messages, "stream": True, "options": {"temperature": temperature}}
    try:
        with httpx.stream("POST", f"{settings.ollama_url}/api/chat", json=payload, timeout=600) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise OllamaError(data["error"])
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama injoignable ou en erreur : {exc}") from exc


def list_models() -> list[str]:
    response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
    response.raise_for_status()
    return [m["name"] for m in response.json().get("models", [])]
