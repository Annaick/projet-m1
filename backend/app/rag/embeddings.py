"""Embeddings des documents et des questions.

embeddinggemma attend des préfixes de tâche différents pour les documents et
pour les requêtes : on les applique ici. Le backend est remplaçable (tests).
"""
from collections.abc import Callable

from app.rag import ollama

Backend = Callable[[list[str]], list[list[float]]]
_backend: Backend = ollama.embed


def set_backend(fn: Backend) -> None:
    global _backend
    _backend = fn


def embed_documents(texts: list[str], titles: list[str]) -> list[list[float]]:
    return _backend([f"title: {t or 'none'} | text: {x}" for x, t in zip(texts, titles)])


def embed_query(question: str) -> list[float]:
    return _backend([f"task: search result | query: {question}"])[0]
