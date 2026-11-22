"""Modèle de données SQLite (7 tables, cf. docs/architecture.md §3)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    file = "file"
    richtext = "richtext"
    faq = "faq"


class SourceStatus(str, Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    error = "error"


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = "Nouvelle conversation"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, index=True)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=now)
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    # False quand l'assistant a répondu « pas dans la base »
    answered: bool = True


class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: SourceType = Field(index=True)
    title: str
    status: SourceStatus = SourceStatus.pending
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=now)
    # Fichier
    file_path: Optional[str] = None
    mime: Optional[str] = None
    # Texte riche
    content: Optional[str] = None
    # FAQ
    question: Optional[str] = None
    answer: Optional[str] = None


class Chunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    position: int
    text: str
    page: Optional[int] = None
    qdrant_id: Optional[str] = None


class Citation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="message.id", index=True)
    # Pas de clé étrangère : la source peut être supprimée après coup
    chunk_id: int
    rank: int
    score: float


DEFAULT_SYSTEM_PROMPT = (
    "Tu es l'assistant documentaire interne de l'entreprise. "
    "Tu réponds uniquement à partir des extraits fournis. "
    "Chaque affirmation est suivie du numéro de l'extrait qui la justifie, entre crochets, par exemple [1] ou [2]. "
    "Si les extraits ne contiennent pas la réponse, dis-le clairement et n'invente rien."
)


class AISettings(SQLModel, table=True):
    __tablename__ = "ai_settings"

    id: int = Field(default=1, primary_key=True)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    tone: str = "professionnel"
    directives: str = "Réponds en français, de façon concise. Utilise des listes quand il y a des étapes."
    llm_model: str = "gemma3:4b"
    temperature: float = 0.2
    top_k: int = 4
    score_threshold: float = 0.40


class KnowledgeGap(SQLModel, table=True):
    __tablename__ = "knowledge_gap"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    message_id: Optional[int] = Field(default=None, foreign_key="message.id")
    best_score: Optional[float] = None
    created_at: datetime = Field(default_factory=now)
    resolved: bool = Field(default=False, index=True)
