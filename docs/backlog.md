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
- [ ] Ollama installé, `gemma3:4b` et `embeddinggemma` téléchargés, temps de réponse mesuré sur une machine de l'équipe
- [ ] Paramètres de config : seuil de score, top-k, taille et chevauchement des chunks
- [ ] 7 tables SQLModel (`conversation`, `message`, `citation`, `source`, `chunk`, `ai_settings`, `knowledge_gap`)
- [ ] Création de la base au démarrage + ligne `ai_settings` par défaut (prompt système, ton, directives)
- [ ] Tests : création des tables, valeurs par défaut

## Lot 2 — Moteur d'ingestion (`backend/app/rag/`)
- [ ] Extraction : PDF (PyMuPDF, numéro de page), TXT/MD, DOCX
- [ ] Découpage : ~500 tokens, chevauchement ~80, coupe sur les paragraphes/phrases
- [ ] Client Ollama : embeddings par lots, génération en streaming
- [ ] Qdrant en mode local (collection `chunks`, payload `chunk_id, source_id, source_type, title, page`)
- [ ] Pipeline `index_source(source_id)` : statut `pending → indexing → indexed | error`, chunks en SQLite + vecteurs en Qdrant
- [ ] Suppression d'une source : chunks SQLite + points Qdrant
- [ ] Tests (embeddings simulés) : extraction, découpage, indexation, suppression

## Lot 3 — API base de connaissances
- [ ] `POST /knowledge/sources` : envoi de fichier (multipart), texte riche, FAQ ; indexation en tâche de fond
- [ ] `GET /knowledge/sources?type=`, `GET/DELETE /knowledge/sources/{id}`
- [ ] `GET /knowledge/summary` (compteurs par type, chunks, état)
- [ ] `GET /chunks/{id}` (extrait d'une citation)
- [ ] Tests d'API

## Lot 4 — Moteur de réponse RAG
- [ ] Recherche : embedding de la question, top-k Qdrant, seuil de score
- [ ] Sous le seuil : réponse « pas dans la base » sans appel au LLM + `knowledge_gap`
- [ ] Prompt : prompt système + ton + directives + extraits numérotés [1]..[k] + historique court
- [ ] Génération streamée, analyse des citations `[n]` → table `citation`
- [ ] Le LLM peut aussi répondre « je ne trouve pas » malgré des extraits → aussi compté comme lacune
- [ ] Tests : seuil, prompt, analyse des citations

## Lot 5 — API conversations, paramètres, lacunes
- [ ] `GET/POST /conversations?q=`, `PATCH/DELETE /conversations/{id}` (titre auto depuis la 1re question)
- [ ] `GET /conversations/{id}/messages` (avec citations), `POST …/messages` (réponse streamée, métadonnées en fin de flux)
- [ ] `GET/PUT /settings`
- [ ] `GET /gaps?resolved=`, `PATCH /gaps/{id}`
- [ ] Tests d'API (LLM simulé)

## Lot 6 — Interface : socle (`frontend/`)
- [ ] Thème : `.streamlit/config.toml` + CSS injecté (couleurs, Inter, rayons) d'après `docs/design/`
- [ ] Barre latérale : nouvelle conversation, rechercher, base de connaissances, questions sans réponse (pastille), récentes (renommer/supprimer), paramètres, état Ollama
- [ ] Client API complet (`api_client.py`), streaming compris

## Lot 7 — Interface : accueil et conversation
- [ ] Accueil : phrase d'accueil, saisie centrée, sources récentes
- [ ] Conversation : bulles utilisateur, réponse streamée, bulles de citation (popover extrait + document), temps de réponse, copier
- [ ] Encadré « pas dans la base »
- [ ] Recherche dans les conversations

## Lot 8 — Interface : base de connaissances, paramètres, lacunes
- [ ] Base de connaissances : cartes Fichiers / Texte riche / FAQ avec compteur et « + », liste des sources, statut, suppression
- [ ] Paramètres de l'IA : ton, directives, prompt système, modèle, température, top-k, seuil
- [ ] Questions sans réponse : à traiter / traitées, « marquer comme traitée », « ajouter à la FAQ »

## Lot 9 — Corpus et questions de référence (`data/`, `eval/`)
- [ ] Choix de la société fictive et du domaine
- [ ] 15 à 30 documents (PDF/TXT/DOCX) rédigés, sans donnée réelle
- [ ] 25 questions avec réponse attendue et sources attendues, dont ~5 hors corpus
- [ ] Script de chargement du corpus dans l'application

## Lot 10 — Évaluation et finitions
- [ ] Banc `eval/` : 3 configurations (LLM seul, BM25 + LLM, RAG sémantique)
- [ ] Métriques : Recall@k, réponses correctement sourcées, hallucinations, bons « je ne sais pas », latence
- [ ] Résultats en CSV/JSON + tableau récapitulatif et graphiques pour le rapport
- [ ] Ajustement du seuil, du top-k et du chunking d'après les résultats
- [ ] Test de bout en bout, README final, scénario de démo
