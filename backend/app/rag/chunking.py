"""Découpage en fragments.

On remplit un fragment jusqu'à `size` mots en coupant sur les paragraphes
(puis les phrases s'ils sont trop longs), avec un chevauchement de `overlap` mots.
"""
import re

from app.rag.extraction import Segment

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _units(text: str, size: int) -> list[list[str]]:
    """Paragraphes (listes de mots), coupés en phrases puis en mots s'ils dépassent `size`."""
    units = []
    for paragraph in re.split(r"\n\s*\n", text):
        words = paragraph.split()
        if not words:
            continue
        if len(words) <= size:
            units.append(words)
            continue
        for sentence in _SENTENCE_END.split(" ".join(words)):
            sentence_words = sentence.split()
            for i in range(0, len(sentence_words), size):
                units.append(sentence_words[i : i + size])
    return units


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    fresh = 0  # mots ajoutés depuis le dernier fragment émis
    for words in _units(text, size):
        if fresh and len(current) + len(words) > size:
            chunks.append(" ".join(current))
            current = current[-overlap:] if overlap else []
            fresh = 0
        current.extend(words)
        fresh += len(words)
    if fresh:
        chunks.append(" ".join(current))
    return chunks


def chunk_segments(segments: list[Segment], size: int, overlap: int) -> list[Segment]:
    """Découpe chaque segment (page) séparément pour garder le numéro de page."""
    return [Segment(c, s.page) for s in segments for c in chunk_text(s.text, size, overlap)]
