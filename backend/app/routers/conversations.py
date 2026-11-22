"""Conversations et messages. La réponse de l'assistant est streamée en NDJSON."""
import json
import time
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, col, delete, or_, select

from app import db
from app.models import AISettings, Chunk, Citation, Conversation, KnowledgeGap, Message, Source, now
from app.rag import answer
from app.rag.ollama import OllamaError

router = APIRouter(tags=["conversations"])

HISTORY_MESSAGES = 4  # 2 derniers échanges envoyés au LLM


class ConversationIn(BaseModel):
    title: str | None = None


class ConversationPatch(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class QuestionIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def _get_conversation(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation introuvable")
    return conversation


def _title_from(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= 60 else title[:57].rstrip() + "…"


@router.get("/conversations")
def list_conversations(q: str | None = None, limit: int = 50, session: Session = Depends(db.get_session)) -> list[Conversation]:
    query = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
    if q:
        matching = select(Message.conversation_id).where(col(Message.content).contains(q))
        query = query.where(or_(col(Conversation.title).contains(q), col(Conversation.id).in_(matching)))
    return list(session.exec(query))


@router.post("/conversations", status_code=201)
def create_conversation(body: ConversationIn | None = None, session: Session = Depends(db.get_session)) -> Conversation:
    conversation = Conversation(title=(body.title if body and body.title else "Nouvelle conversation"))
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@router.patch("/conversations/{conversation_id}")
def rename_conversation(conversation_id: int, body: ConversationPatch, session: Session = Depends(db.get_session)) -> Conversation:
    conversation = _get_conversation(session, conversation_id)
    conversation.title = body.title.strip()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, session: Session = Depends(db.get_session)) -> None:
    conversation = _get_conversation(session, conversation_id)
    message_ids = select(Message.id).where(Message.conversation_id == conversation_id)
    session.exec(delete(Citation).where(col(Citation.message_id).in_(message_ids)))
    for gap in session.exec(select(KnowledgeGap).where(col(KnowledgeGap.message_id).in_(message_ids))):
        gap.message_id = None  # la question reste dans « Questions sans réponse »
        session.add(gap)
    session.exec(delete(Message).where(Message.conversation_id == conversation_id))
    session.delete(conversation)
    session.commit()


def _citations_of(session: Session, message_id: int) -> list[dict]:
    rows = session.exec(select(Citation).where(Citation.message_id == message_id).order_by(Citation.rank))
    result = []
    for c in rows:
        chunk = session.get(Chunk, c.chunk_id)
        source = session.get(Source, chunk.source_id) if chunk else None
        result.append(
            {
                "rank": c.rank,
                "chunk_id": c.chunk_id,
                "score": c.score,
                "title": source.title if source else "Source supprimée",
                "page": chunk.page if chunk else None,
                "source_id": source.id if source else None,
            }
        )
    return result


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, session: Session = Depends(db.get_session)) -> dict:
    conversation = _get_conversation(session, conversation_id)
    messages = session.exec(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id))
    return {
        "conversation": conversation,
        "messages": [{**m.model_dump(mode="json"), "citations": _citations_of(session, m.id)} for m in messages],
    }


@router.post("/conversations/{conversation_id}/messages")
def ask(conversation_id: int, body: QuestionIn, session: Session = Depends(db.get_session)) -> StreamingResponse:
    """Pose une question. Réponse en NDJSON : une ligne JSON par événement
    (`user`, `sources`, `token`…, puis `done` avec l'id du message et les citations, ou `error`)."""
    _get_conversation(session, conversation_id)
    return StreamingResponse(_answer_events(conversation_id, body.content.strip()), media_type="application/x-ndjson")


def _answer_events(conversation_id: int, question: str) -> Iterator[str]:
    started = time.perf_counter()
    with Session(db.engine) as session:
        ai = session.get(AISettings, 1)
        conversation = session.get(Conversation, conversation_id)
        previous = list(
            session.exec(
                select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.desc()).limit(HISTORY_MESSAGES)
            )
        )[::-1]
        history = [{"role": m.role, "content": m.content} for m in previous if m.answered]
        previous_question = next((m.content for m in reversed(previous) if m.role == "user"), None)

        user_message = Message(conversation_id=conversation_id, role="user", content=question)
        session.add(user_message)
        if not previous:
            conversation.title = _title_from(question)
        conversation.updated_at = now()
        session.add(conversation)
        session.commit()
        session.refresh(user_message)
        yield _line({"type": "user", "message_id": user_message.id, "conversation_id": conversation_id})

        try:
            final = None
            for event in answer.answer_stream(session, ai, question, history, previous_question):
                if event["type"] == "done":
                    final = event
                else:
                    yield _line(event)
        except OllamaError as exc:
            yield _line({"type": "error", "message": f"Le modèle ne répond pas. Ollama est-il lancé ? ({exc})"})
            return

        latency_ms = int((time.perf_counter() - started) * 1000)
        message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=final["text"],
            latency_ms=latency_ms,
            model=ai.llm_model if final["answered"] or final["citations"] else None,
            answered=final["answered"],
        )
        session.add(message)
        session.flush()
        for c in final["citations"]:
            session.add(Citation(message_id=message.id, chunk_id=c["chunk_id"], rank=c["rank"], score=c["score"]))
        if not final["answered"]:
            session.add(KnowledgeGap(question=question, message_id=message.id, best_score=final["best_score"]))
        session.commit()
        yield _line(
            {
                "type": "done",
                "message_id": message.id,
                "answered": final["answered"],
                "citations": final["citations"],
                "latency_ms": latency_ms,
                "title": conversation.title,
            }
        )


def _line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"
