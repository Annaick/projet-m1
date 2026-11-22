"""Qdrant en mode local (fichiers dans storage/qdrant, sans serveur ni Docker).

Le mode local n'est pas prévu pour des accès concurrents : un verrou sérialise
les appels (l'API traite les requêtes dans plusieurs threads).
"""
import functools
import threading
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from app.config import settings

COLLECTION = "chunks"
_client: QdrantClient | None = None
_lock = threading.RLock()


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)

    return wrapper


@dataclass
class Hit:
    chunk_id: int
    score: float
    payload: dict


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=str(settings.qdrant_path))
    return _client


def set_client(client: QdrantClient) -> None:
    global _client
    _client = client


def _exists() -> bool:
    return get_client().collection_exists(COLLECTION)


@_locked
def upsert(vectors: list[list[float]], payloads: list[dict]) -> list[str]:
    if not vectors:
        return []
    client = get_client()
    if not _exists():
        client.create_collection(
            COLLECTION, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE)
        )
    ids = [str(uuid.uuid4()) for _ in vectors]
    client.upsert(COLLECTION, points=[models.PointStruct(id=i, vector=v, payload=p) for i, v, p in zip(ids, vectors, payloads)])
    return ids


@_locked
def delete_source(source_id: int) -> None:
    if not _exists():
        return
    condition = models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id))
    get_client().delete(COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(must=[condition])))


@_locked
def search(vector: list[float], limit: int) -> list[Hit]:
    if not _exists():
        return []
    result = get_client().query_points(COLLECTION, query=vector, limit=limit, with_payload=True)
    return [Hit(chunk_id=p.payload["chunk_id"], score=p.score, payload=p.payload) for p in result.points]


@_locked
def count() -> int:
    return get_client().count(COLLECTION).count if _exists() else 0
