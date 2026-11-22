import json


def ask(client, conversation_id: int, question: str) -> list[dict]:
    response = client.post(f"/conversations/{conversation_id}/messages", json={"content": question})
    assert response.status_code == 200
    return [json.loads(line) for line in response.text.splitlines() if line]


def seed(client):
    client.post("/knowledge/sources/faq", json={"question": "Combien de jours de congés payés ?", "answer": "25 jours ouvrés par an."})
    client.post(
        "/knowledge/sources/richtext",
        json={"title": "VPN", "content": "<p>Le VPN se lance depuis le portail interne avec le compte Windows.</p>"},
    )
    client.post(
        "/knowledge/sources/files",
        files=[("files", ("frais.txt", "Notes de frais : plafond repas de 25 euros, justificatif obligatoire.".encode(), "text/plain"))],
    )


# --- Base de connaissances ------------------------------------------------------

def test_ajout_et_indexation_des_sources(client):
    seed(client)
    sources = client.get("/knowledge/sources").json()
    assert len(sources) == 3
    assert all(s["status"] == "indexed" and s["chunks"] == 1 for s in sources)

    summary = client.get("/knowledge/summary").json()
    assert summary["by_type"] == {"file": 1, "richtext": 1, "faq": 1}
    assert summary["chunks"] == 3 and len(summary["recent"]) == 3

    assert len(client.get("/knowledge/sources", params={"type": "faq"}).json()) == 1


def test_format_refuse(client):
    response = client.post("/knowledge/sources/files", files=[("files", ("image.png", b"x", "image/png"))])
    assert response.status_code == 415


def test_modification_et_suppression(client):
    seed(client)
    faq = client.get("/knowledge/sources", params={"type": "faq"}).json()[0]
    updated = client.put(f"/knowledge/sources/{faq['id']}", json={"question": "Congés ?", "answer": "27 jours."})
    assert updated.status_code == 200
    chunks = client.get(f"/knowledge/sources/{faq['id']}/chunks").json()
    assert "27 jours" in chunks[0]["text"]
    assert client.get(f"/chunks/{chunks[0]['id']}").json()["source"]["title"] == "Congés ?"

    assert client.delete(f"/knowledge/sources/{faq['id']}").status_code == 204
    assert client.get(f"/chunks/{chunks[0]['id']}").status_code == 404
    assert client.get("/knowledge/summary").json()["chunks"] == 2


# --- Conversations --------------------------------------------------------------

def test_question_avec_reponse_et_citation(client):
    seed(client)
    conversation = client.post("/conversations").json()
    events = ask(client, conversation["id"], "Combien de jours de congés payés par an ?")

    types = [e["type"] for e in events]
    assert types[0] == "user" and types[1] == "sources" and types[-1] == "done"
    assert "".join(e["text"] for e in events if e["type"] == "token") == client.replies["text"]
    done = events[-1]
    assert done["answered"] and done["citations"][0]["title"] == "Combien de jours de congés payés ?"
    assert done["title"].startswith("Combien de jours")

    history = client.get(f"/conversations/{conversation['id']}/messages").json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["citations"][0]["rank"] == 1
    assert client.get("/gaps").json() == []


def test_question_hors_base_sans_appel_llm(client):
    seed(client)
    client.replies["text"] = "NE DOIT PAS ÊTRE APPELÉ"
    conversation = client.post("/conversations").json()
    events = ask(client, conversation["id"], "Quelle est la capitale du Pérou ?")
    assert events[-1]["answered"] is False
    assert "aucune information" in "".join(e.get("text", "") for e in events if e["type"] == "token")

    gaps = client.get("/gaps", params={"resolved": False}).json()
    assert gaps[0]["question"] == "Quelle est la capitale du Pérou ?"
    assert gaps[0]["conversation_id"] == conversation["id"]
    client.patch(f"/gaps/{gaps[0]['id']}", json={"resolved": True})
    assert client.get("/gaps", params={"resolved": False}).json() == []


def test_refus_du_llm_compte_comme_lacune(client):
    seed(client)
    client.replies["text"] = "Je ne trouve pas cette information dans la base de connaissances."
    client.put("/settings", json={**client.get("/settings").json(), "score_threshold": 0.0})
    conversation = client.post("/conversations").json()
    events = ask(client, conversation["id"], "Combien de jours de congés pour un mariage ?")
    assert events[-1]["answered"] is False and events[-1]["citations"] == []
    assert len(client.get("/gaps").json()) == 1


def test_recherche_renommage_suppression(client):
    seed(client)
    first = client.post("/conversations").json()
    ask(client, first["id"], "Combien de jours de congés payés ?")
    second = client.post("/conversations").json()
    ask(client, second["id"], "Comment se connecter au VPN ?")

    assert [c["id"] for c in client.get("/conversations").json()] == [second["id"], first["id"]]
    assert [c["id"] for c in client.get("/conversations", params={"q": "VPN"}).json()] == [second["id"]]

    client.patch(f"/conversations/{first['id']}", json={"title": "Mes congés"})
    assert client.get(f"/conversations/{first['id']}/messages").json()["conversation"]["title"] == "Mes congés"

    assert client.delete(f"/conversations/{first['id']}").status_code == 204
    assert client.get(f"/conversations/{first['id']}/messages").status_code == 404


def test_parametres(client):
    current = client.get("/settings").json()
    response = client.put("/settings", json={**current, "tone": "décontracté", "top_k": 6})
    assert response.status_code == 200 and response.json()["top_k"] == 6
    assert client.put("/settings", json={**current, "top_k": 0}).status_code == 422


def test_vingt_envois_d_affilee_avec_la_file_reelle(client, monkeypatch):
    """Régression : avec les BackgroundTasks, ~15 envois saturaient le pool de connexions SQLite."""
    from app.rag import indexer

    monkeypatch.setattr(indexer, "SYNCHRONOUS", False)
    for i in range(20):
        assert client.post("/knowledge/sources/faq", json={"question": f"Question {i} ?", "answer": f"Réponse {i}."}).status_code == 201
    indexer.wait_idle()
    summary = client.get("/knowledge/summary").json()
    assert summary["by_status"]["indexed"] == 20 and summary["chunks"] == 20
