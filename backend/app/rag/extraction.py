"""Extraction du texte des sources, page par page quand c'est possible."""
import re
import unicodedata
from dataclasses import dataclass
from html import unescape
from pathlib import Path


@dataclass
class Segment:
    text: str
    page: int | None = None


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


class ExtractionError(Exception):
    pass


def clean(text: str) -> str:
    """NFKC : ligatures (« ﬁ » → « fi »), espaces insécables, etc."""
    return unicodedata.normalize("NFKC", text).replace("­", "")


def extract_file(path: Path) -> list[Segment]:
    return [Segment(clean(s.text), s.page) for s in _extract(path)]


def _extract(path: Path) -> list[Segment]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext in {".txt", ".md"}:
        return [Segment(_read_text(path))]
    if ext == ".docx":
        return [Segment(_extract_docx(path))]
    raise ExtractionError(f"Format non pris en charge : {ext}")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _extract_pdf(path: Path) -> list[Segment]:
    import pymupdf

    segments = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                segments.append(Segment(text, number))
    if not segments:
        raise ExtractionError("Aucun texte dans le PDF (document scanné ?)")
    return segments


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n\n".join(line for line in lines if line.strip())


def html_to_text(html: str) -> str:
    """Texte riche (HTML ou Markdown léger) → texte brut, paragraphes conservés."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
