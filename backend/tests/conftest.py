"""Isole les tests : stockage temporaire, Qdrant en mémoire, embeddings simulés.

Aucun test n'a besoin d'Ollama.
"""
import hashlib
import os
import re
import tempfile
import unicodedata

os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="rag-tests-")

import pytest  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, create_engine  # noqa: E402

from app.db import init_db  # noqa: E402
from app.rag import embeddings, vectorstore  # noqa: E402

DIM = 256
_PREFIX = re.compile(r"^(title: .*? \| text: |task: search result \| query: )")


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Sac de mots haché : deux textes qui partagent des mots sont proches."""
    vectors = []
    for text in texts:
        text = _PREFIX.sub("", text)
        text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
        vector = [0.0] * DIM
        for word in re.findall(r"[a-z0-9]{3,}", text):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
        if not any(vector):
            vector[0] = 1.0
        vectors.append(vector)
    return vectors


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def fake_rag_backends():
    embeddings.set_backend(fake_embed)
    vectorstore.set_client(QdrantClient(":memory:"))
    yield


@pytest.fixture
def client(engine, monkeypatch):
    """Client HTTP sur une base en mémoire ; le LLM est simulé par `llm_reply`."""
    from fastapi.testclient import TestClient

    from app import db
    from app.main import app
    from app.rag import answer

    from app.rag import indexer

    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(indexer, "SYNCHRONOUS", True)
    replies = {"text": "Selon le règlement, vous avez 25 jours de congés [1]."}

    def fake_chat(messages, model, temperature):
        yield from replies["text"].split(" ")[:1]
        for word in replies["text"].split(" ")[1:]:
            yield " " + word

    monkeypatch.setattr(answer.ollama, "chat_stream", fake_chat)
    with TestClient(app) as c:
        c.replies = replies
        yield c
