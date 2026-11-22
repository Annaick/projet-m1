from pathlib import Path

import docx
import pymupdf
from sqlmodel import select

from app.models import Chunk, Source, SourceStatus, SourceType
from app.rag import embeddings, vectorstore
from app.rag.chunking import chunk_text
from app.rag.extraction import extract_file, html_to_text
from app.rag.ingestion import delete_source, index_source


# --- Extraction -------------------------------------------------------------

def test_extraction_pdf_garde_les_pages(tmp_path: Path):
    path = tmp_path / "guide.pdf"
    doc = pymupdf.open()
    for text in ("Page un : congés payés.", "Page deux : télétravail."):
        doc.new_page().insert_text((72, 72), text)
    doc.save(path)
    segments = extract_file(path)
    assert [s.page for s in segments] == [1, 2]
    assert "télétravail" in segments[1].text


def test_extraction_docx_et_txt(tmp_path: Path):
    d = docx.Document()
    d.add_paragraph("Note de frais : plafond de 25 € par repas.")
    d.save(tmp_path / "frais.docx")
    assert "plafond" in extract_file(tmp_path / "frais.docx")[0].text

    (tmp_path / "vpn.txt").write_text("Connexion VPN : utiliser le client fourni.", encoding="cp1252")
    assert "Connexion" in extract_file(tmp_path / "vpn.txt")[0].text


def test_html_vers_texte():
    text = html_to_text("<h2>Congés</h2><p>Poser ses congés &amp; RTT</p><ul><li>un</li><li>deux</li></ul>")
    assert "Congés\n\nPoser ses congés & RTT" in text
    assert "- un" in text


# --- Découpage --------------------------------------------------------------

def test_decoupage_taille_et_chevauchement():
    paragraphs = [" ".join(f"p{p}m{i}" for i in range(40)) for p in range(10)]  # 400 mots
    chunks = chunk_text("\n\n".join(paragraphs), size=100, overlap=20)
    assert len(chunks) > 3
    assert all(len(c.split()) <= 120 for c in chunks)
    # le début d'un fragment reprend la fin du précédent
    assert chunks[1].split()[:20] == chunks[0].split()[-20:]
    # aucun mot perdu
    assert set(" ".join(chunks).split()) == set(" ".join(paragraphs).split())


def test_decoupage_texte_court_un_seul_fragment():
    assert chunk_text("Un texte court.", size=100, overlap=20) == ["Un texte court."]
    assert chunk_text("   ", size=100, overlap=20) == []


def test_decoupage_paragraphe_trop_long():
    long = ". ".join(f"Phrase numéro {i} sur les congés" for i in range(100))
    chunks = chunk_text(long, size=50, overlap=10)
    assert all(len(c.split()) <= 60 for c in chunks)


# --- Indexation -------------------------------------------------------------

def test_indexation_faq_et_recherche(session):
    faq = Source(type=SourceType.faq, title="Congés", question="Combien de jours de congés ?", answer="25 jours ouvrés par an.")
    autre = Source(type=SourceType.richtext, title="VPN", content="<p>Le VPN se lance depuis le portail interne.</p>")
    session.add_all([faq, autre])
    session.commit()

    assert index_source(session, faq.id).status == SourceStatus.indexed
    assert index_source(session, autre.id).status == SourceStatus.indexed
    chunks = session.exec(select(Chunk)).all()
    assert len(chunks) == 2 and all(c.qdrant_id for c in chunks)
    assert vectorstore.count() == 2

    hits = vectorstore.search(embeddings.embed_query("jours de congés par an"), limit=2)
    assert hits[0].payload["title"] == "Congés"
    assert hits[0].score > hits[1].score


def test_reindexation_ne_duplique_pas(session):
    source = Source(type=SourceType.richtext, title="Note", content="Un contenu.")
    session.add(source)
    session.commit()
    index_source(session, source.id)
    index_source(session, source.id)
    assert len(session.exec(select(Chunk)).all()) == 1
    assert vectorstore.count() == 1


def test_echec_passe_en_erreur(session, tmp_path: Path):
    source = Source(type=SourceType.file, title="vide.pdf", file_path=str(tmp_path / "absent.pdf"))
    session.add(source)
    session.commit()
    result = index_source(session, source.id)
    assert result.status == SourceStatus.error and result.error
    assert vectorstore.count() == 0


def test_suppression_nettoie_partout(session, tmp_path: Path):
    path = tmp_path / "doc.txt"
    path.write_text("Procédure d'arrivée d'un nouveau salarié.", encoding="utf-8")
    source = Source(type=SourceType.file, title="doc.txt", file_path=str(path))
    session.add(source)
    session.commit()
    index_source(session, source.id)
    assert delete_source(session, source.id)
    assert session.exec(select(Chunk)).all() == []
    assert vectorstore.count() == 0
    assert not path.exists()
