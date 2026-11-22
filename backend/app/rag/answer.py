"""Moteur de réponse : recherche → seuil → prompt → génération → citations.

`answer_stream` est un générateur d'événements, consommé par l'API (streaming
NDJSON) et par le banc d'évaluation. Événements :
  {"type": "sources", "sources": [...]}   extraits retenus (avant génération)
  {"type": "token", "text": "..."}         morceau de réponse
  {"type": "done", "answered": bool, "citations": [...], "best_score": float|None}
"""
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass

from sqlmodel import Session

from app.models import AISettings, Chunk, Source
from app.rag import embeddings, ollama, vectorstore

NOT_IN_BASE = (
    "Je n'ai trouvé aucune information sur ce sujet dans la base de connaissances. "
    "La question a été ajoutée aux questions sans réponse pour que la base soit complétée."
)
REFUSAL = "Je ne trouve pas cette information dans la base de connaissances."

_CITATION = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
_REFUSAL_HINTS = (
    "ne trouve pas cette information",
    "ne contiennent pas",
    "ne contient pas",
    "aucune information",
    "pas d'information",
    "ne precisent pas",
    "ne mentionnent pas",
)


@dataclass
class Extract:
    """Un fragment retenu, numéroté [rank] dans le prompt."""

    rank: int
    chunk_id: int
    score: float
    text: str
    title: str
    page: int | None
    source_id: int | None

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("rank", "chunk_id", "score", "title", "page", "source_id")}


# --- Recherche ---------------------------------------------------------------

def search_query(question: str, previous_question: str | None) -> str:
    """Une relance courte (« Et pour les RTT ? ») est enrichie de la question précédente."""
    if previous_question and len(question.split()) <= 8:
        return f"{previous_question} {question}"
    return question


def retrieve(session: Session, query: str, top_k: int) -> list[Extract]:
    hits = vectorstore.search(embeddings.embed_query(query), limit=top_k)
    extracts = []
    for hit in hits:
        chunk = session.get(Chunk, hit.chunk_id)
        if chunk is None:  # désynchronisation SQLite / Qdrant : on ignore
            continue
        source = session.get(Source, chunk.source_id)
        extracts.append(
            Extract(
                rank=len(extracts) + 1,
                chunk_id=chunk.id,
                score=round(hit.score, 4),
                text=chunk.text,
                title=source.title if source else hit.payload.get("title", "?"),
                page=chunk.page,
                source_id=chunk.source_id,
            )
        )
    return extracts


# --- Prompt ------------------------------------------------------------------

def system_message(ai: AISettings) -> str:
    parts = [ai.system_prompt.strip()]
    if ai.tone.strip():
        parts.append(f"Ton à adopter : {ai.tone.strip()}.")
    if ai.directives.strip():
        parts.append(f"Directives : {ai.directives.strip()}")
    return "\n\n".join(parts)


def format_extracts(extracts: list[Extract]) -> str:
    blocks = []
    for e in extracts:
        where = f"{e.title}, page {e.page}" if e.page else e.title
        blocks.append(f"[{e.rank}] ({where})\n{e.text}")
    return "\n\n".join(blocks)


def build_messages(ai: AISettings, extracts: list[Extract], question: str, history: list[dict] | None = None) -> list[dict]:
    user = (
        "Extraits de la base de connaissances :\n\n"
        f"{format_extracts(extracts)}\n\n"
        "---\n"
        f"Question : {question}\n\n"
        "Réponds uniquement à partir des extraits ci-dessus et cite-les avec leur numéro entre crochets, "
        "par exemple [1]. Si les extraits ne permettent pas de répondre, réponds exactement : "
        f"« {REFUSAL} »"
    )
    return [{"role": "system", "content": system_message(ai)}, *(history or []), {"role": "user", "content": user}]


# --- Analyse de la réponse -----------------------------------------------------

def cited_ranks(text: str, max_rank: int) -> list[int]:
    """Numéros [n] cités, dans l'ordre d'apparition, sans doublon ni numéro inventé."""
    ranks: list[int] = []
    for group in _CITATION.findall(text):
        for n in re.split(r"\s*[,;]\s*", group):
            rank = int(n)
            if 1 <= rank <= max_rank and rank not in ranks:
                ranks.append(rank)
    return ranks


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode().replace("’", "'")


def is_refusal(text: str) -> bool:
    """Le LLM dit ne pas trouver la réponse (et ne cite rien)."""
    normalized = _normalize(text)
    return not _CITATION.search(text) and any(hint in normalized for hint in _REFUSAL_HINTS)


# --- Orchestration -----------------------------------------------------------

def answer_stream(
    session: Session,
    ai: AISettings,
    question: str,
    history: list[dict] | None = None,
    previous_question: str | None = None,
) -> Iterator[dict]:
    extracts = retrieve(session, search_query(question, previous_question), ai.top_k)
    best = max((e.score for e in extracts), default=None)
    kept = [e for e in extracts if e.score >= ai.score_threshold]

    if not kept:
        yield {"type": "sources", "sources": []}
        yield {"type": "token", "text": NOT_IN_BASE}
        yield {"type": "done", "answered": False, "citations": [], "best_score": best, "text": NOT_IN_BASE}
        return

    yield {"type": "sources", "sources": [e.as_dict() for e in kept]}
    parts: list[str] = []
    for token in ollama.chat_stream(build_messages(ai, kept, question, history), ai.llm_model, ai.temperature):
        parts.append(token)
        yield {"type": "token", "text": token}
    text = "".join(parts)

    if is_refusal(text):
        yield {"type": "done", "answered": False, "citations": [], "best_score": best, "text": text}
        return
    by_rank = {e.rank: e for e in kept}
    ranks = cited_ranks(text, len(kept))
    citations = [by_rank[r].as_dict() for r in ranks]
    yield {"type": "done", "answered": True, "citations": citations, "best_score": best, "text": text}
