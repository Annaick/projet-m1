"""Point d'entrée de l'API : uvicorn app.main:app --reload --app-dir backend"""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from sqlmodel import Session, select

from app import db
from app.config import settings
from app.models import Source, SourceStatus
from app.rag import ollama, vectorstore
from app.routers import admin, conversations, knowledge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    # Une indexation interrompue (arrêt de l'API) repasse en erreur, réindexable depuis l'interface
    with Session(db.engine) as session:
        for source in session.exec(select(Source).where(Source.status.in_([SourceStatus.pending, SourceStatus.indexing]))):
            source.status, source.error = SourceStatus.error, "Indexation interrompue : relancez-la"
            session.add(source)
        session.commit()
    yield


app = FastAPI(
    title="Assistant documentaire RAG",
    description="API de l'assistant documentaire local (Ollama + Qdrant + SQLite).",
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(knowledge.router)
app.include_router(conversations.router)
app.include_router(admin.router)


@app.get("/health", tags=["système"])
def health() -> dict:
    try:
        models = ollama.list_models()
        status = {"ok": True, "models": models}
        missing = [m for m in (settings.llm_model, settings.embedding_model) if not any(x.split(":")[0] == m.split(":")[0] for x in models)]
        if missing:
            status["missing"] = missing
    except httpx.HTTPError as exc:
        status = {"ok": False, "error": str(exc)}
    try:
        vectors = vectorstore.count()
        qdrant = {"ok": True, "vectors": vectors}
    except Exception as exc:  # noqa: BLE001
        qdrant = {"ok": False, "error": str(exc)}
    return {"api": "ok", "ollama": status, "qdrant": qdrant, "embedding_model": settings.embedding_model}
