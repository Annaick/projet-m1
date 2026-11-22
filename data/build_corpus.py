"""Génère le corpus de démonstration (data/corpus/) à partir des sources Markdown (data/sources/).

Chaque source porte un en-tête `format: pdf | docx | txt | md` qui fixe le format du fichier produit,
pour tester l'extraction sur des formats variés.

    python data/build_corpus.py
"""
import re
import sys
from html import escape
from pathlib import Path

import docx
import pymupdf

DATA = Path(__file__).resolve().parent
SOURCES, CORPUS = DATA / "sources", DATA / "corpus"

CSS = """
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1A1D23; }
h1 { font-size: 18pt; color: #2B46B0; margin-bottom: 6pt; }
h2 { font-size: 13pt; color: #2B46B0; margin-top: 12pt; }
p, li { margin: 3pt 0; }
table { border-collapse: collapse; margin: 6pt 0; }
td, th { border: 1px solid #D5D9E1; padding: 3pt 6pt; font-size: 9.5pt; }
th { background-color: #EEF0F4; }
.footer { font-size: 8pt; color: #5A6170; margin-top: 14pt; }
"""


def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = dict(line.split(": ", 1) for line in match.group(1).splitlines())
    return meta, text[match.end():].strip()


def inline(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(text, quote=False))


def blocks(body: str):
    """Découpe le Markdown en blocs simples : (kind, data)."""
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            yield f"h{level}", line.lstrip("# ").strip()
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            yield "table", rows
        elif re.match(r"(- |\d+\. )", line):
            ordered = bool(re.match(r"\d+\. ", line))
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                i += 1
            yield ("ol" if ordered else "ul"), items
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(#|\||- |\d+\. )", lines[i]):
                para.append(lines[i].strip())
                i += 1
            yield "p", " ".join(para)


def to_html(body: str) -> str:
    out = []
    for kind, data in blocks(body):
        if kind.startswith("h"):
            out.append(f"<{kind}>{inline(data)}</{kind}>")
        elif kind == "p":
            out.append(f"<p>{inline(data)}</p>")
        elif kind in ("ul", "ol"):
            out.append(f"<{kind}>" + "".join(f"<li>{inline(x)}</li>" for x in data) + f"</{kind}>")
        elif kind == "table":
            head, *rows = data
            out.append(
                "<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                + "</table>"
            )
    out.append("<p class='footer'>Brumeval (société fictive) · document interne de démonstration</p>")
    return "\n".join(out)


def write_pdf(body: str, path: Path) -> None:
    story = pymupdf.Story(html=to_html(body), user_css=CSS)
    writer = pymupdf.DocumentWriter(str(path))
    rect = pymupdf.paper_rect("a4")
    where = rect + (56, 56, -56, -56)
    more = True
    while more:
        device = writer.begin_page(rect)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()


def write_docx(body: str, path: Path) -> None:
    document = docx.Document()
    for kind, data in blocks(body):
        if kind.startswith("h"):
            document.add_heading(data.replace("**", ""), level=int(kind[1]))
        elif kind == "p":
            _rich_paragraph(document.add_paragraph(), data)
        elif kind in ("ul", "ol"):
            for item in data:
                _rich_paragraph(document.add_paragraph(style="List Number" if kind == "ol" else "List Bullet"), item)
        elif kind == "table":
            table = document.add_table(rows=len(data), cols=len(data[0]))
            table.style = "Table Grid"
            for r, row in enumerate(data):
                for c, cell in enumerate(row):
                    table.cell(r, c).text = cell.replace("**", "")
    document.save(str(path))


def _rich_paragraph(paragraph, text: str) -> None:
    for k, part in enumerate(re.split(r"\*\*", text)):
        paragraph.add_run(part).bold = k % 2 == 1


def write_txt(body: str, path: Path) -> None:
    path.write_text(body.replace("**", "") + "\n", encoding="utf-8")


def main() -> None:
    CORPUS.mkdir(exist_ok=True)
    for old in CORPUS.glob("*.*"):
        if old.suffix in {".pdf", ".docx", ".txt", ".md"} and old.name != "README.md":
            old.unlink()
    writers = {"pdf": write_pdf, "docx": write_docx, "txt": write_txt, "md": write_txt}
    for source in sorted(SOURCES.glob("*.md")):
        meta, body = parse(source)
        fmt = meta["format"]
        target = CORPUS / f"{source.stem}.{fmt}"
        writers[fmt](body, target)
        print(f"{source.name:40} -> {target.name}")
    print(f"{len(list(SOURCES.glob('*.md')))} documents générés dans {CORPUS}")


if __name__ == "__main__":
    sys.exit(main())
