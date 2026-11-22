# Assistant documentaire RAG local

Projet de fin d'année — Master 1 Informatique, École Nationale d'Informatique.
Équipe : Annaïck, José, Yaël, Michael.

Un assistant conversationnel qui répond aux questions sur une base documentaire **en local**, en citant
les documents utilisés, et qui sait dire quand l'information n'est pas dans la base.
Tout tourne sur la machine : aucun service payant, aucune API cloud.

- Plan complet du projet (cadrage, maquettes, architecture, planning) : [`docs/plan-projet.pdf`](docs/plan-projet.pdf)
- Architecture détaillée (modèle de données, API, flux) : [`docs/architecture.md`](docs/architecture.md)
- Maquettes de l'interface (HTML à ouvrir dans un navigateur) et charte : [`docs/design/`](docs/design/README.md)
- Backlog du MVP (10 lots) : [`docs/backlog.md`](docs/backlog.md)

## Fonctionnalités (MVP)

- **Chat** façon assistant IA : conversations dans la barre latérale, réponses affichées au fil de l'écriture,
  bulles de citation cliquables vers l'extrait source.
- **Base de connaissances** : fichiers (PDF, TXT, MD, DOCX), texte riche, FAQ. Indexation automatique.
- **Questions sans réponse** : les questions où rien de pertinent n'a été trouvé sont enregistrées.
- **Paramètres de l'IA** : prompt système, ton, directives, modèle, température, top-k, seuil de pertinence.
- **Évaluation** : comparaison LLM seul / mots-clés (BM25) / RAG sémantique sur 25 questions de référence.

## Stack

| Rôle | Outil |
|---|---|
| Interface | Streamlit |
| API | FastAPI |
| LLM et embeddings | Ollama (`gemma3:4b`, `embeddinggemma`) |
| Base vectorielle | Qdrant (mode local, sans Docker) |
| Base relationnelle | SQLite (SQLModel) |
| Extraction | PyMuPDF, python-docx |

## Structure

```
backend/      API FastAPI + moteur RAG
  app/
    main.py       application FastAPI
    config.py     réglages (lus depuis .env)
    models.py     tables SQLite (SQLModel)
    routers/      routes : knowledge, conversations, admin (paramètres, lacunes)
    rag/          extraction, découpage, embeddings, Qdrant, BM25, réponse
  tests/          tests (LLM et embeddings simulés : pas besoin d'Ollama)
frontend/     interface Streamlit
  app.py          point d'entrée et navigation
  ui.py           thème, barre latérale, composants communs
  views/          chat, recherche, base de connaissances, questions sans réponse, paramètres
  api_client.py   appels à l'API
eval/         25 questions de référence + banc d'évaluation (run_eval.py)
data/
  sources/        textes Markdown du corpus (à modifier ici)
  corpus/         documents générés (PDF, DOCX, TXT, MD) : build_corpus.py
  knowledge.json  texte riche et FAQ de démonstration
docs/         plan du projet, architecture, maquettes (design/), backlog
```

## Installation

Prérequis : **Python 3.11 ou plus récent**, **Git**, **[Ollama](https://ollama.com/download)**.

```bash
# 1. Modèles Ollama (une seule fois)
ollama pull gemma3:4b
ollama pull embeddinggemma

# 2. Environnement Python (à la racine du dépôt)
python -m venv .venv
# Windows (PowerShell) : .venv\Scripts\Activate.ps1
# Windows (Git Bash)   : source .venv/Scripts/activate
# Linux / macOS        : source .venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt

# 3. Configuration
cp .env.example .env      # puis ajuster si besoin
```

Sous Windows, gardez `127.0.0.1` dans les URL du `.env` : avec `localhost`, chaque appel perd environ 2 s
(tentative IPv6 avant IPv4).

## Lancement

Deux terminaux, venv activé, depuis la racine du dépôt :

```bash
# Terminal 1 : API  → http://localhost:8000/docs
uvicorn app.main:app --reload --app-dir backend

# Terminal 2 : interface → http://localhost:8501
streamlit run frontend/app.py
```

Ollama doit tourner en arrière-plan (il démarre tout seul après installation sur Windows).
`GET http://127.0.0.1:8000/health` indique si l'API voit bien Ollama et les deux modèles.

### Charger le corpus de démonstration

Avec l'API lancée :

```bash
python data/load_corpus.py           # 20 documents de la société fictive Brumeval + texte riche + FAQ
python data/load_corpus.py --reset   # repartir d'une base vide
```

Les documents se modifient dans `data/sources/*.md`, puis `python data/build_corpus.py` régénère `data/corpus/`.

## Évaluation

Qdrant en mode local n'accepte qu'un processus à la fois : **arrêtez l'API** avant de lancer le banc.

```bash
python eval/run_eval.py --retrieval-only   # Recall@k et choix du seuil, sans LLM (quelques secondes)
python eval/run_eval.py                    # + génération : LLM seul, BM25 + LLM, RAG (≈ 75 appels au LLM)
```

Les résultats (`rapport.md`, `resume.json`, `reponses.csv`) sont écrits dans `eval/results/<date>/`.
Détails des métriques : [`eval/README.md`](eval/README.md).

## Tests

```bash
pytest backend/tests
```

## Travailler à plusieurs

- `main` doit toujours démarrer. On travaille sur une branche par fonctionnalité
  (`feat/ingestion`, `feat/chat-ui`…) et on fusionne par pull request.
- Messages de commit en français, à l'impératif : « Ajoute l'extraction PDF ».
- Jamais de secret ni de fichier `.env` dans le dépôt. Les bases locales (`storage/`) ne sont pas versionnées.

## Répartition

| Rôle | Périmètre | Personne |
|---|---|---|
| A | Moteur RAG (`backend/app/rag/`) | à définir |
| B | API et base de données (`backend/app/`) | à définir |
| C | Interface (`frontend/`) | à définir |
| D | Corpus et évaluation (`data/`, `eval/`) | à définir |
