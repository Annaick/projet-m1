"""Recherche lexicale BM25 sur les fragments SQLite (configuration de comparaison du banc d'évaluation)."""
import re
import unicodedata

from rank_bm25 import BM25Okapi
from sqlmodel import Session, select

from app.models import Chunk, Source
from app.rag.answer import Extract

STOPWORDS = set(
    "a au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me meme mes moi mon ne nos notre "
    "nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c d j l m n s t y "
    "est sont ai as avons avez ont etre avoir faire fait faut peut quel quelle quels quelles comment combien quand "
    "est-ce si plus".split()
)


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [w for w in re.findall(r"[a-z0-9]+", text) if w not in STOPWORDS]


class BM25Index:
    def __init__(self, session: Session):
        rows = session.exec(select(Chunk, Source).join(Source, Chunk.source_id == Source.id)).all()
        self.items = [(chunk, source) for chunk, source in rows]
        self.bm25 = BM25Okapi([tokenize(f"{s.title} {c.text}") for c, s in self.items]) if self.items else None

    def search(self, query: str, top_k: int) -> list[Extract]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            Extract(rank=r + 1, chunk_id=self.items[i][0].id, score=round(float(scores[i]), 4), text=self.items[i][0].text,
                    title=self.items[i][1].title, page=self.items[i][0].page, source_id=self.items[i][1].id)
            for r, i in enumerate(best)
            if scores[i] > 0
        ]
