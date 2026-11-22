from app.models import AISettings
from app.rag.answer import Extract, build_messages, cited_ranks, is_refusal, search_query


def test_citations_ordre_sans_doublon_ni_numero_invente():
    text = "Oui [2]. Et aussi [1, 3]. Encore [2] et [9]."
    assert cited_ranks(text, max_rank=3) == [2, 1, 3]


def test_refus_detecte_sans_citation():
    assert is_refusal("Je ne trouve pas cette information dans la base de connaissances.")
    assert is_refusal("Les extraits ne contiennent pas d’indication sur ce point.")
    assert not is_refusal("Les extraits ne contiennent pas tout, mais le plafond est de 25 € [1].")
    assert not is_refusal("Le plafond est de 25 € par repas [1].")


def test_relance_courte_enrichie():
    assert search_query("Et pour les RTT ?", "Combien de jours de congés ?") == "Combien de jours de congés ? Et pour les RTT ?"
    assert search_query("Quelle est la procédure complète pour commander un nouvel ordinateur portable ?", "x") .startswith("Quelle")
    assert search_query("Et les RTT ?", None) == "Et les RTT ?"


def test_prompt_contient_parametres_et_extraits():
    ai = AISettings(tone="chaleureux", directives="Tutoie l'utilisateur.")
    extracts = [Extract(1, 10, 0.8, "25 jours de congés.", "Règlement", 3, 1)]
    history = [{"role": "user", "content": "Bonjour"}, {"role": "assistant", "content": "Bonjour !"}]
    messages = build_messages(ai, extracts, "Combien de congés ?", history)
    assert messages[0]["role"] == "system" and "chaleureux" in messages[0]["content"] and "Tutoie" in messages[0]["content"]
    assert messages[1:3] == history
    assert "[1] (Règlement, page 3)\n25 jours de congés." in messages[-1]["content"]
    assert messages[-1]["content"].count("Combien de congés ?") == 1


def test_bm25_trouve_le_bon_fragment(session):
    from app.models import Source, SourceType
    from app.rag.bm25 import BM25Index, tokenize
    from app.rag.ingestion import index_source

    assert tokenize("Combien de jours de Congés ?") == ["jours", "conges"]
    docs = [
        ("Congés", "Vingt-cinq jours de congés payés par an."),
        ("VPN", "Le VPN se lance depuis le portail."),
        ("Frais", "Les notes de frais se déclarent dans Spendo."),
        ("Badge", "Le badge est remis le premier jour."),
    ]
    for title, text in docs:
        source = Source(type=SourceType.richtext, title=title, content=text)
        session.add(source)
        session.commit()
        index_source(session, source.id)
    results = BM25Index(session).search("combien de jours de congés ?", top_k=2)
    assert results[0].title == "Congés" and len(results) == 1
