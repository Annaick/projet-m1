# Architecture — v1 validée

Statut : **validée par l'équipe le 22/11/2026**. Toute évolution se discute avant d'être appliquée ici.

## 1. Vue d'ensemble

```
┌──────────────────────┐   HTTP/JSON (+ streaming)   ┌───────────────────────────────┐
│  Streamlit (front)   │ ──────────────────────────▶ │  FastAPI (back)               │
│  - Chat + sidebar    │                             │  - API REST                   │
│  - Base de connaiss. │ ◀────────────────────────── │  - Moteur RAG                 │
│  - Paramètres IA     │                             │                               │
└──────────────────────┘                             │   ┌─────────┐  ┌───────────┐  │
                                                     │   │ SQLite  │  │  Qdrant   │  │
                                                     │   │ (métier)│  │ (vecteurs,│  │
                                                     │   └─────────┘  │ mode local│  │
                                                     │                └───────────┘  │
                                                     │        ┌──────────────┐       │
                                                     │        │ Ollama       │       │
                                                     │        │ LLM + embed. │       │
                                                     └────────┴──────────────┴───────┘
```

- Le front ne parle **qu'à l'API**. Toute la logique (RAG, base, Ollama) est côté back.
- Qdrant en **mode local embarqué** (`QdrantClient(path=...)`) : pas de Docker, rien à installer en plus.
- Ollama tourne à part sur chaque machine (service local, port 11434).

## 2. Dépôt unique (monorepo)

```
<nom-du-repo>/
├── backend/
│   ├── app/
│   │   ├── main.py              # création de l'app FastAPI
│   │   ├── config.py            # réglages (.env) : chemins, modèles, URL Ollama
│   │   ├── db.py                # moteur SQLite, session
│   │   ├── models.py            # tables (SQLModel)
│   │   ├── schemas.py           # objets d'entrée/sortie de l'API
│   │   ├── routers/
│   │   │   ├── conversations.py # CRUD conversations + envoi de message
│   │   │   ├── knowledge.py     # sources : fichiers, texte riche, FAQ
│   │   │   ├── settings.py      # paramètres de l'IA
│   │   │   └── gaps.py          # questions sans réponse
│   │   └── rag/
│   │       ├── extraction.py    # PDF (PyMuPDF), TXT/MD, DOCX
│   │       ├── chunking.py      # découpage en fragments
│   │       ├── embeddings.py    # appel Ollama embeddings
│   │       ├── vectorstore.py   # Qdrant
│   │       ├── retriever.py     # recherche sémantique (+ BM25 pour la baseline)
│   │       ├── prompts.py       # construction du prompt
│   │       └── pipeline.py      # ingestion() et answer()
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app.py                   # point d'entrée Streamlit, navigation
│   ├── views/                   # chat, base de connaissances, paramètres
│   ├── api_client.py            # appels à l'API
│   └── requirements.txt
├── eval/
│   ├── questions.json           # 25 questions de référence + réponses + sources attendues
│   ├── run_eval.py              # lance les 3 configurations, écrit les résultats
│   └── results/
├── data/
│   └── corpus/                  # documents de la société fictive (livrable : données de test)
├── .env.example
└── README.md                    # installation + lancement
```

## 3. Modèle de données (SQLite)

| Table | Champs principaux | Rôle |
|---|---|---|
| `conversation` | id, title, created_at, updated_at | Une ligne par conversation de la sidebar |
| `message` | id, conversation_id, role (user/assistant), content, created_at, latency_ms, model, answered (bool) | Historique ; `answered=false` quand l'IA dit « pas dans le corpus » |
| `citation` | id, message_id, chunk_id, rank, score | Les bulles de source sous une réponse |
| `source` | id, type (file/richtext/faq), title, status (pending/indexing/indexed/error), error, created_at, + selon type : file_path, mime / content (texte riche) / question, answer (FAQ) | Une entrée de la base de connaissances |
| `chunk` | id, source_id, position, text, page (nullable), qdrant_id | Fragment indexé. Dupliqué en SQLite pour afficher l'extrait cité et pour la baseline BM25 |
| `ai_settings` | id=1, system_prompt, tone, directives, llm_model, temperature, top_k, score_threshold | Une seule ligne (pas de comptes) |
| `knowledge_gap` | id, question, message_id, created_at, resolved | Questions restées sans réponse |

Qdrant : une collection `chunks`, vecteur + payload `{chunk_id, source_id, source_type, title, page}`.

## 4. Flux principaux

**Ingestion** (ajout d'une source) : enregistrement `source` (pending) → extraction du texte → découpage
→ embeddings → upsert Qdrant + lignes `chunk` → `source.status = indexed`.
Une FAQ = un seul fragment « Q : … R : … ». Suppression d'une source = suppression de ses fragments partout.

**Question** : embedding de la question → top-k Qdrant → si aucun score ≥ seuil : réponse « pas dans la base »
+ ligne `knowledge_gap` → sinon prompt (paramètres IA + fragments numérotés [1]…[k] + historique court)
→ Ollama en streaming → extraction des [n] cités → lignes `citation` → le front affiche les bulles.

## 5. API (premier jet)

```
GET/POST        /conversations?q=          PATCH/DELETE /conversations/{id}   (q = recherche titre/contenu)
GET             /conversations/{id}/messages
POST            /conversations/{id}/messages        → réponse streamée + citations
GET             /knowledge/summary                  → compteurs par type (cartes façon GoHighLevel)
GET/POST        /knowledge/sources?type=            (POST fichier = multipart)
GET/DELETE      /knowledge/sources/{id}
GET             /chunks/{id}                        → extrait affiché au clic sur une bulle
GET/PUT         /settings
GET/PATCH       /gaps
GET             /health                             → état Ollama / Qdrant / SQLite
```

## 6. Évaluation (le livrable qui pèse le plus)

Trois configurations sur les 25 questions :
1. **LLM seul** (sans RAG) — baseline exigée par l'énoncé.
2. **BM25** (mots-clés) + LLM — baseline « recherche simple ».
3. **RAG sémantique** (Qdrant) + LLM — notre système.

Mesures : Recall@k (sources attendues retrouvées), taux de réponses correctement sourcées,
hallucinations (notées à la main ou par grille), taux de bons « je ne sais pas » sur des questions
**volontairement hors corpus** (en prévoir ~5 sur les 25), temps de réponse.

## 7. Choix techniques proposés

| Point | Proposition | Pourquoi |
|---|---|---|
| ORM | SQLModel | Écrit par l'auteur de FastAPI, peu de code |
| Extraction | PyMuPDF (+ python-docx) | Léger, donne le numéro de page pour les citations. Docling tire PyTorch : trop lourd pour vos PC. Tesseract inutile : corpus rédigé par nous, donc pas de scans |
| Chunking | ~500 tokens, chevauchement ~80, coupe sur titres/paragraphes | Valeurs classiques, à ajuster pendant l'éval |
| Embeddings | `embeddinggemma` (Ollama, ~300M, multilingue) ; repli `bge-m3` | Corpus en français → multilingue obligatoire |
| LLM | `gemma3:4b` ; repli `qwen2.5:3b` ou `llama3.2:3b` | À chronométrer sur la machine la plus faible |
| Streaming | FastAPI `StreamingResponse` → `st.write_stream` | Effet « ChatGPT » et meilleur ressenti sur PC lents |
