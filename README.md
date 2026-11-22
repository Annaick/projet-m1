# Assistant documentaire RAG local

Projet de fin d'année — Master 1 Informatique, École Nationale d'Informatique.
Équipe : Annaïck, José, Yaël, Michael.

Un assistant conversationnel qui répond aux questions sur une base documentaire **en local**, en citant
les documents utilisés, et qui sait dire quand l'information n'est pas dans la base.
Tout tourne sur la machine : aucun service payant, aucune API cloud.

- Plan complet du projet (cadrage, maquettes, architecture, planning) : [`docs/plan-projet.pdf`](docs/plan-projet.pdf)
- Architecture détaillée (modèle de données, API, flux) : [`docs/architecture.md`](docs/architecture.md)

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
    routers/      routes : conversations, knowledge, settings, gaps
    rag/          extraction, découpage, embeddings, Qdrant, recherche, génération
  tests/
frontend/     interface Streamlit
  app.py          point d'entrée et navigation
  views/          accueil/chat, base de connaissances, paramètres
  api_client.py   appels à l'API
eval/         25 questions de référence + script d'évaluation
data/corpus/  documents de la société fictive (jeu de test)
docs/         plan du projet, architecture
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

## Lancement

Deux terminaux, venv activé, depuis la racine du dépôt :

```bash
# Terminal 1 : API  → http://localhost:8000/docs
uvicorn app.main:app --reload --app-dir backend

# Terminal 2 : interface → http://localhost:8501
streamlit run frontend/app.py
```

Ollama doit tourner en arrière-plan (il démarre tout seul après installation sur Windows).
`GET http://localhost:8000/health` indique si l'API voit bien Ollama.

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
