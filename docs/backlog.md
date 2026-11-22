# Backlog du MVP

Découpé en 10 lots, dans l'ordre de dépendance. Une case cochée = fait **et** testé.
Référence : [`architecture.md`](architecture.md) (conception v1) et [`design/`](design/) (maquettes).

| Lot | Contenu | Dépend de |
|---|---|---|
| 1 | Environnement et modèle de données | — |
| 2 | Moteur d'ingestion | 1 |
| 3 | API base de connaissances | 2 |
| 4 | Moteur de réponse RAG | 2 |
| 5 | API conversations, paramètres, questions sans réponse | 4 |
| 6 | Interface : socle (thème, barre latérale, client API) | 1 |
| 7 | Interface : accueil et conversation | 5, 6 |
| 8 | Interface : base de connaissances, paramètres, questions sans réponse | 3, 5, 6 |
| 9 | Corpus fictif et 25 questions de référence | — |
| 10 | Banc d'évaluation, résultats, finitions | 4, 9 |

---

## Lot 1 — Environnement et modèle de données
- [x] Ollama installé, `gemma3:4b` et `embeddinggemma` téléchargés, temps de réponse mesuré sur une machine de l'équipe
- [x] Paramètres de config : seuil de score, top-k, taille et chevauchement des chunks
- [x] 7 tables SQLModel (`conversation`, `message`, `citation`, `source`, `chunk`, `ai_settings`, `knowledge_gap`)
- [x] Création de la base au démarrage + ligne `ai_settings` par défaut (prompt système, ton, directives)
- [x] Tests : création des tables, valeurs par défaut

## Lot 2 — Moteur d'ingestion (`backend/app/rag/`)
- [x] Extraction : PDF (PyMuPDF, numéro de page), TXT/MD, DOCX
- [x] Découpage : ~500 tokens, chevauchement ~80, coupe sur les paragraphes/phrases
- [x] Client Ollama : embeddings par lots, génération en streaming
- [x] Qdrant en mode local (collection `chunks`, payload `chunk_id, source_id, source_type, title, page`)
- [x] Pipeline `index_source(source_id)` : statut `pending → indexing → indexed | error`, chunks en SQLite + vecteurs en Qdrant
- [x] Suppression d'une source : chunks SQLite + points Qdrant
- [x] Tests (embeddings simulés) : extraction, découpage, indexation, suppression

## Lot 3 — API base de connaissances
- [x] `POST /knowledge/sources` : envoi de fichier (multipart), texte riche, FAQ ; indexation en tâche de fond
- [x] `GET /knowledge/sources?type=`, `GET/DELETE /knowledge/sources/{id}`
- [x] `GET /knowledge/summary` (compteurs par type, chunks, état)
- [x] `GET /chunks/{id}` (extrait d'une citation)
- [x] Tests d'API

## Lot 4 — Moteur de réponse RAG
- [x] Recherche : embedding de la question, top-k Qdrant, seuil de score
- [x] Sous le seuil : réponse « pas dans la base » sans appel au LLM + `knowledge_gap`
- [x] Prompt : prompt système + ton + directives + extraits numérotés [1]..[k] + historique court
- [x] Génération streamée, analyse des citations `[n]` → table `citation`
- [x] Le LLM peut aussi répondre « je ne trouve pas » malgré des extraits → aussi compté comme lacune
- [x] Tests : seuil, prompt, analyse des citations

## Lot 5 — API conversations, paramètres, lacunes
- [x] `GET/POST /conversations?q=`, `PATCH/DELETE /conversations/{id}` (titre auto depuis la 1re question)
- [x] `GET /conversations/{id}/messages` (avec citations), `POST …/messages` (réponse streamée, métadonnées en fin de flux)
- [x] `GET/PUT /settings`
- [x] `GET /gaps?resolved=`, `PATCH /gaps/{id}`
- [x] Tests d'API (LLM simulé)

## Lot 6 — Interface : socle (`frontend/`)
- [x] Thème : `.streamlit/config.toml` + CSS injecté (couleurs, Inter, rayons) d'après `docs/design/`
- [x] Barre latérale : nouvelle conversation, rechercher, base de connaissances, questions sans réponse (pastille), récentes (renommer/supprimer), paramètres, état Ollama
- [x] Client API complet (`api_client.py`), streaming compris

## Lot 7 — Interface : accueil et conversation
- [x] Accueil : phrase d'accueil, saisie centrée, sources récentes
- [x] Conversation : bulles utilisateur, réponse streamée, bulles de citation (popover extrait + document), temps de réponse, copier
- [x] Encadré « pas dans la base »
- [x] Recherche dans les conversations

## Lot 8 — Interface : base de connaissances, paramètres, lacunes
- [x] Base de connaissances : cartes Fichiers / Texte riche / FAQ avec compteur et « + », liste des sources, statut, suppression
- [x] Paramètres de l'IA : ton, directives, prompt système, modèle, température, top-k, seuil
- [x] Questions sans réponse : à traiter / traitées, « marquer comme traitée », « ajouter à la FAQ »

## Lot 9 — Corpus et questions de référence (`data/`, `eval/`)
- [x] Choix de la société fictive et du domaine (Brumeval, à confirmer par l'équipe : D-014)
- [x] 15 à 30 documents (PDF/TXT/DOCX) rédigés, sans donnée réelle
- [x] 25 questions avec réponse attendue et sources attendues, dont ~5 hors corpus
- [x] Script de chargement du corpus dans l'application

## Lot 10 — Évaluation et finitions
- [x] Banc `eval/` : 3 configurations (LLM seul, BM25 + LLM, RAG sémantique)
- [x] Métriques : Recall@k, réponses correctement sourcées, hallucinations, bons « je ne sais pas », latence
- [x] Résultats en CSV/JSON + tableau récapitulatif (`eval/results/2026-11-22_1623/`)
- [ ] Graphiques pour le rapport et vérification manuelle (`verdict_manuel`)
- [x] Ajustement du seuil, du top-k et du chunking d'après les résultats
- [x] Test de bout en bout, README final, scénario de démo

## Après le MVP (rapport, à faire par l'équipe)
- [ ] Valider le domaine du corpus et relire les 25 questions
- [ ] Remplir `verdict_manuel` dans `reponses.csv`, tracer les graphiques
- [ ] Mesurer la latence sur une machine avec une carte graphique récente
- [ ] Rapport (15 à 20 pages) et répétition de la démo (`docs/demo.md`)
