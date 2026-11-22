"""Paramètres de l'IA et questions sans réponse."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app import db
from app.models import DEFAULT_SYSTEM_PROMPT, AISettings, KnowledgeGap, Message

router = APIRouter()


class SettingsIn(BaseModel):
    system_prompt: str = Field(min_length=1)
    tone: str = ""
    directives: str = ""
    llm_model: str = Field(min_length=1)
    temperature: float = Field(ge=0, le=2)
    top_k: int = Field(ge=1, le=20)
    score_threshold: float = Field(ge=0, le=1)


class GapPatch(BaseModel):
    resolved: bool


@router.get("/settings", tags=["paramètres"])
def get_settings(session: Session = Depends(db.get_session)) -> AISettings:
    return session.get(AISettings, 1)


@router.put("/settings", tags=["paramètres"])
def put_settings(body: SettingsIn, session: Session = Depends(db.get_session)) -> AISettings:
    ai = session.get(AISettings, 1)
    for key, value in body.model_dump().items():
        setattr(ai, key, value)
    session.add(ai)
    session.commit()
    session.refresh(ai)
    return ai


@router.get("/settings/default-prompt", tags=["paramètres"])
def default_prompt() -> dict:
    return {"system_prompt": DEFAULT_SYSTEM_PROMPT}


@router.get("/gaps", tags=["questions sans réponse"])
def list_gaps(resolved: bool | None = None, session: Session = Depends(db.get_session)) -> list[dict]:
    query = select(KnowledgeGap).order_by(KnowledgeGap.created_at.desc())
    if resolved is not None:
        query = query.where(KnowledgeGap.resolved == resolved)
    result = []
    for gap in session.exec(query):
        message = session.get(Message, gap.message_id) if gap.message_id else None
        result.append({**gap.model_dump(mode="json"), "conversation_id": message.conversation_id if message else None})
    return result


@router.patch("/gaps/{gap_id}", tags=["questions sans réponse"])
def patch_gap(gap_id: int, body: GapPatch, session: Session = Depends(db.get_session)) -> KnowledgeGap:
    gap = session.get(KnowledgeGap, gap_id)
    if gap is None:
        raise HTTPException(404, "Question introuvable")
    gap.resolved = body.resolved
    session.add(gap)
    session.commit()
    session.refresh(gap)
    return gap
