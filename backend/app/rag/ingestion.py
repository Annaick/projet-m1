"""Pipeline d'ingestion : source → texte → fragments → embeddings → Qdrant + SQLite."""
import logging
from pathlib import Path

from sqlmodel import Session, delete

from app.config import settings
from app.models import Chunk, Source, SourceStatus, SourceType
from app.rag import embeddings, vectorstore
from app.rag.chunking import chunk_segments
from app.rag.extraction import Segment, extract_file, html_to_text

log = logging.getLogger(__name__)


def source_segments(source: Source) -> list[Segment]:
    if source.type == SourceType.file:
        return extract_file(Path(source.file_path))
    if source.type == SourceType.richtext:
        return [Segment(html_to_text(source.content or ""))]
    if source.type == SourceType.faq:
        return [Segment(f"Question : {source.question}\nRéponse : {source.answer}")]
    raise ValueError(f"Type de source inconnu : {source.type}")


def index_source(session: Session, source_id: int) -> Source:
    """Indexe (ou réindexe) une source. En cas d'échec, la source passe en `error`."""
    source = session.get(Source, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} introuvable")
    source.status, source.error = SourceStatus.indexing, None
    session.add(source)
    session.commit()
    try:
        _clear_chunks(session, source_id)
        segments = source_segments(source)
        # Une FAQ = un seul fragment, jamais découpé
        pieces = segments if source.type == SourceType.faq else chunk_segments(segments, settings.chunk_size, settings.chunk_overlap)
        if not pieces:
            raise ValueError("Aucun texte exploitable dans cette source")

        chunks = [Chunk(source_id=source_id, position=i, text=p.text, page=p.page) for i, p in enumerate(pieces)]
        session.add_all(chunks)
        session.flush()  # attribue les id

        vectors = embeddings.embed_documents([c.text for c in chunks], [source.title] * len(chunks))
        payloads = [
            {"chunk_id": c.id, "source_id": source_id, "source_type": source.type.value, "title": source.title, "page": c.page}
            for c in chunks
        ]
        for chunk, qdrant_id in zip(chunks, vectorstore.upsert(vectors, payloads)):
            chunk.qdrant_id = qdrant_id
        source.status = SourceStatus.indexed
        session.add(source)
        session.commit()
    except Exception as exc:  # l'erreur est affichée dans l'interface
        log.exception("Indexation de la source %s en échec", source_id)
        session.rollback()
        vectorstore.delete_source(source_id)
        source = session.get(Source, source_id)
        source.status, source.error = SourceStatus.error, str(exc)
        session.add(source)
        session.commit()
    session.refresh(source)
    return source


def _clear_chunks(session: Session, source_id: int) -> None:
    vectorstore.delete_source(source_id)
    session.exec(delete(Chunk).where(Chunk.source_id == source_id))
    session.commit()


def delete_source(session: Session, source_id: int) -> bool:
    source = session.get(Source, source_id)
    if source is None:
        return False
    _clear_chunks(session, source_id)
    if source.file_path:
        Path(source.file_path).unlink(missing_ok=True)
    session.delete(source)
    session.commit()
    return True
