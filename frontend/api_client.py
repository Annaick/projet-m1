"""Appels à l'API FastAPI. L'interface ne parle qu'à l'API, jamais directement à Ollama ou aux bases."""
import json
import os
from collections.abc import Iterator
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
_client = httpx.Client(base_url=API_URL, timeout=30)


class ApiError(Exception):
    pass


def _call(method: str, path: str, **kwargs):
    try:
        response = _client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise ApiError(f"L'API ne répond pas ({API_URL}). Est-elle lancée ?") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False))
    return response.json() if response.content else None


# --- Système -----------------------------------------------------------------

def get_health() -> dict | None:
    try:
        return _call("GET", "/health")
    except ApiError:
        return None


# --- Conversations -------------------------------------------------------------

def list_conversations(q: str | None = None, limit: int = 30) -> list[dict]:
    return _call("GET", "/conversations", params={"q": q, "limit": limit} if q else {"limit": limit})


def create_conversation() -> dict:
    return _call("POST", "/conversations")


def rename_conversation(conversation_id: int, title: str) -> dict:
    return _call("PATCH", f"/conversations/{conversation_id}", json={"title": title})


def delete_conversation(conversation_id: int) -> None:
    _call("DELETE", f"/conversations/{conversation_id}")


def get_messages(conversation_id: int) -> dict:
    return _call("GET", f"/conversations/{conversation_id}/messages")


def ask(conversation_id: int, question: str) -> Iterator[dict]:
    """Événements NDJSON de la réponse (user, sources, token…, done | error)."""
    try:
        with httpx.stream(
            "POST", f"{API_URL}/conversations/{conversation_id}/messages", json={"content": question}, timeout=600
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise ApiError(response.text)
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)
    except httpx.HTTPError as exc:
        yield {"type": "error", "message": f"Connexion à l'API perdue : {exc}"}


# --- Base de connaissances -------------------------------------------------------

def knowledge_summary() -> dict:
    return _call("GET", "/knowledge/summary")


def list_sources(type_: str | None = None, q: str | None = None) -> list[dict]:
    params = {k: v for k, v in {"type": type_, "q": q}.items() if v}
    return _call("GET", "/knowledge/sources", params=params)


def get_source(source_id: int) -> dict:
    return _call("GET", f"/knowledge/sources/{source_id}")


def upload_files(files: list[tuple[str, bytes, str]]) -> list[dict]:
    return _call("POST", "/knowledge/sources/files", files=[("files", f) for f in files], timeout=120)


def add_richtext(title: str, content: str) -> dict:
    return _call("POST", "/knowledge/sources/richtext", json={"title": title, "content": content})


def add_faq(question: str, answer: str) -> dict:
    return _call("POST", "/knowledge/sources/faq", json={"question": question, "answer": answer})


def update_source(source_id: int, body: dict) -> dict:
    return _call("PUT", f"/knowledge/sources/{source_id}", json=body)


def reindex_source(source_id: int) -> dict:
    return _call("POST", f"/knowledge/sources/{source_id}/reindex")


def delete_source(source_id: int) -> None:
    _call("DELETE", f"/knowledge/sources/{source_id}")


def get_chunk(chunk_id: int) -> dict | None:
    try:
        return _call("GET", f"/chunks/{chunk_id}")
    except ApiError:
        return None


# --- Paramètres et lacunes ---------------------------------------------------------

def get_settings() -> dict:
    return _call("GET", "/settings")


def put_settings(body: dict) -> dict:
    return _call("PUT", "/settings", json=body)


def default_prompt() -> str:
    return _call("GET", "/settings/default-prompt")["system_prompt"]


def list_gaps(resolved: bool | None = None) -> list[dict]:
    return _call("GET", "/gaps", params={} if resolved is None else {"resolved": str(resolved).lower()})


def set_gap_resolved(gap_id: int, resolved: bool = True) -> dict:
    return _call("PATCH", f"/gaps/{gap_id}", json={"resolved": resolved})


def source_chunks(source_id: int) -> list[dict]:
    return _call("GET", f"/knowledge/sources/{source_id}/chunks")
