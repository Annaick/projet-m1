"""Base de connaissances : sources (fichiers, texte riche, FAQ) et fragments."""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

from app import db
from app.config import settings
from app.models import Chunk, Source, SourceStatus, SourceType
from app.rag import indexer, ingestion
from app.rag.extraction import SUPPORTED_EXTENSIONS

router = APIRouter(tags=["base de connaissances"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class RichTextIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class FaqIn(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class SourceOut(BaseModel):
    id: int
    type: SourceType
    title: str
    status: SourceStatus
    error: str | None
    created_at: str
    chunks: int
    mime: str | None = None
    content: str | None = None
    question: str | None = None
    answer: str | None = None


def _chunk_counts(session: Session) -> dict[int, int]:
    rows = session.exec(select(Chunk.source_id, func.count(Chunk.id)).group_by(Chunk.source_id))
    return dict(rows.all())


def _out(source: Source, chunks: int, full: bool = False) -> SourceOut:
    data = dict(
        id=source.id,
        type=source.type,
        title=source.title,
        status=source.status,
        error=source.error,
        created_at=source.created_at.isoformat(),
        chunks=chunks,
        mime=source.mime,
    )
    if full or source.type == SourceType.faq:
        data.update(question=source.question, answer=source.answer)
    if full:
        data.update(content=source.content)
    return SourceOut(**data)


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", Path(name).name)[:120]
    return f"{uuid.uuid4().hex[:8]}_{stem}"


@router.get("/knowledge/summary")
def summary(session: Session = Depends(db.get_session)) -> dict:
    sources = session.exec(select(Source).order_by(Source.created_at.desc())).all()
    counts = _chunk_counts(session)
    by_type = {t.value: sum(1 for s in sources if s.type == t) for t in SourceType}
    by_status = {st.value: sum(1 for s in sources if s.status == st) for st in SourceStatus}
    return {
        "sources": len(sources),
        "by_type": by_type,
        "by_status": by_status,
        "chunks": sum(counts.values()),
        "recent": [_out(s, counts.get(s.id, 0)) for s in sources[:4]],
    }


@router.get("/knowledge/sources", response_model=list[SourceOut])
def list_sources(type: SourceType | None = None, q: str | None = None, session: Session = Depends(db.get_session)):
    query = select(Source).order_by(Source.created_at.desc())
    if type:
        query = query.where(Source.type == type)
    if q:
        query = query.where(Source.title.contains(q))
    counts = _chunk_counts(session)
    return [_out(s, counts.get(s.id, 0)) for s in session.exec(query)]


@router.get("/knowledge/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: int, session: Session = Depends(db.get_session)):
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source introuvable")
    return _out(source, _chunk_counts(session).get(source_id, 0), full=True)


@router.get("/knowledge/sources/{source_id}/chunks")
def source_chunks(source_id: int, session: Session = Depends(db.get_session)) -> list[dict]:
    chunks = session.exec(select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.position))
    return [{"id": c.id, "position": c.position, "page": c.page, "text": c.text} for c in chunks]


@router.post("/knowledge/sources/files", response_model=list[SourceOut], status_code=201)
async def upload_files(files: list[UploadFile], session: Session = Depends(db.get_session)):
    created = []
    for upload in files:
        name = upload.filename or "document"
        if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(415, f"{name} : formats acceptés {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"{name} : 20 Mo maximum")
        path = settings.uploads_path / _safe_name(name)
        path.write_bytes(data)
        source = Source(type=SourceType.file, title=name, file_path=str(path), mime=upload.content_type)
        session.add(source)
        session.commit()
        session.refresh(source)
        indexer.enqueue(source.id)
        created.append(_out(source, 0))
    return created


@router.post("/knowledge/sources/richtext", response_model=SourceOut, status_code=201)
def add_richtext(body: RichTextIn, session: Session = Depends(db.get_session)):
    source = Source(type=SourceType.richtext, title=body.title.strip(), content=body.content)
    session.add(source)
    session.commit()
    session.refresh(source)
    indexer.enqueue(source.id)
    return _out(source, 0)


@router.post("/knowledge/sources/faq", response_model=SourceOut, status_code=201)
def add_faq(body: FaqIn, session: Session = Depends(db.get_session)):
    question = body.question.strip()
    source = Source(type=SourceType.faq, title=question[:200], question=question, answer=body.answer.strip())
    session.add(source)
    session.commit()
    session.refresh(source)
    indexer.enqueue(source.id)
    return _out(source, 0)


@router.put("/knowledge/sources/{source_id}", response_model=SourceOut)
def update_source(source_id: int, body: dict, session: Session = Depends(db.get_session)):
    """Modifie un texte riche ou une FAQ, puis réindexe."""
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source introuvable")
    if source.type == SourceType.richtext:
        data = RichTextIn(**body)
        source.title, source.content = data.title.strip(), data.content
    elif source.type == SourceType.faq:
        data = FaqIn(**body)
        source.title, source.question, source.answer = data.question.strip()[:200], data.question.strip(), data.answer.strip()
    else:
        raise HTTPException(400, "Un fichier ne se modifie pas : supprimez-le et envoyez la nouvelle version")
    source.status = SourceStatus.pending
    session.add(source)
    session.commit()
    session.refresh(source)
    indexer.enqueue(source.id)
    return _out(source, 0, full=True)


@router.post("/knowledge/sources/{source_id}/reindex", response_model=SourceOut)
def reindex(source_id: int, session: Session = Depends(db.get_session)):
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source introuvable")
    source.status = SourceStatus.pending
    session.add(source)
    session.commit()
    session.refresh(source)
    indexer.enqueue(source.id)
    return _out(source, 0)


@router.delete("/knowledge/sources/{source_id}", status_code=204)
def delete_source(source_id: int, session: Session = Depends(db.get_session)) -> None:
    if not ingestion.delete_source(session, source_id):
        raise HTTPException(404, "Source introuvable")


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: int, session: Session = Depends(db.get_session)) -> dict:
    chunk = session.get(Chunk, chunk_id)
    if chunk is None:
        raise HTTPException(404, "Extrait introuvable (source supprimée ?)")
    source = session.get(Source, chunk.source_id)
    return {
        "id": chunk.id,
        "text": chunk.text,
        "page": chunk.page,
        "position": chunk.position,
        "source": {"id": source.id, "title": source.title, "type": source.type} if source else None,
    }
