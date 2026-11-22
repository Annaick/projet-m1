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


def table_to_lines(rows: list[list[str]]) -> list[str]:
    """Tableau → une ligne par rangée, chaque valeur associée à son en-tête de colonne.

    « Repas | 20,50 € | 25 € » devient « Repas — Province : 20,50 € ; Paris : 25 € » : sans cela,
    le lien entre une valeur et sa colonne se perd et le modèle confond les montants."""
    rows = [[" ".join((c or "").split()) for c in row] for row in rows if any((c or "").strip() for c in row)]
    if len(rows) < 2:
        return [" | ".join(r) for r in rows]
    header, *body = rows
    lines = []
    for row in body:
        pairs = [f"{h} : {v}" if h else v for h, v in zip(header[1:], row[1:]) if v]
        lines.append(f"{row[0]} — {' ; '.join(pairs)}" if pairs else row[0])
    return lines


def _extract_pdf(path: Path) -> list[Segment]:
    import pymupdf

    segments = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            pieces = []  # (ordonnée, texte), pour garder les tableaux à leur place
            tables = page.find_tables().tables
            for table in tables:
                rows = [
                    [page.get_textbox(pymupdf.Rect(cell)) if cell else "" for cell in row.cells]
                    for row in table.rows
                ]
                pieces.append((table.bbox[1], "\n".join(table_to_lines(rows))))
            boxes = [pymupdf.Rect(t.bbox) for t in tables]
            for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
                block = pymupdf.Rect(x0, y0, x1, y1)
                if text.strip() and not any(block.intersects(b) for b in boxes):
                    pieces.append((y0, text.strip()))
            text = "\n\n".join(t for _, t in sorted(pieces, key=lambda p: p[0])).strip()
            if text:
                segments.append(Segment(text, number))
    if not segments:
        raise ExtractionError("Aucun texte dans le PDF (document scanné ?)")
    return segments


def _extract_docx(path: Path) -> str:
    """Paragraphes et tableaux dans l'ordre du document."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    parts = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, document).text
            if text.strip():
                parts.append(text)
        elif tag == "tbl":
            rows = [[cell.text for cell in row.cells] for row in Table(child, document).rows]
            parts.append("\n".join(table_to_lines(rows)))
    return "\n\n".join(parts)


def html_to_text(html: str) -> str:
    """Texte riche (HTML ou Markdown léger) → texte brut, paragraphes conservés."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
