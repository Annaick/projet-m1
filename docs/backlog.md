# Backlog

Lots 1 à 10 : le MVP, **terminés** (22/11/2026). Lots 11 à 15 : **ce qui reste** pour le rendu.
Une case cochée = fait **et** testé.
Référence : [`architecture.md`](architecture.md) (conception v1) et [`design/`](design/) (maquettes).

| Lot | Contenu | Dépend de | État |
|---|---|---|---|
| 1 | Environnement et modèle de données | — | fait |
| 2 | Moteur d'ingestion | 1 | fait |
| 3 | API base de connaissances | 2 | fait |
| 4 | Moteur de réponse RAG | 2 | fait |
| 5 | API conversations, paramètres, questions sans réponse | 4 | fait |
| 6 | Interface : socle (thème, barre latérale, client API) | 1 | fait |
| 7 | Interface : accueil et conversation | 5, 6 | fait |
| 8 | Interface : base de connaissances, paramètres, questions sans réponse | 3, 5, 6 | fait |
| 9 | Corpus fictif et 25 questions de référence | — | fait |
| 10 | Banc d'évaluation, résultats, scripts d'installation | 4, 9 | fait |
| **11** | **Validation par l'équipe (corpus, questions, installation sur chaque PC)** | — | **à faire** |
| **12** | **Analyse des résultats (vérification manuelle, graphiques, mesures complémentaires)** | 11 | **à faire** |
| **13** | **Améliorations facultatives de l'application** | — | facultatif |
| **14** | **Rapport (15 à 20 pages)** | 12 | **à faire** |
| **15** | **Soutenance et démo** | 12, 14 | **à faire** |

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

---

# Ce qui reste

Point de départ : résultats de référence dans [`eval/results/2026-11-22_1623/`](../eval/results/2026-11-22_1623/rapport.md)
(RAG sémantique : 95 % de réponses exactes et sourcées, 0 % d'hallucination hors corpus ;
LLM seul sans consigne : 100 % d'hallucinations hors corpus). Barème : 45 pts sur 100 portent sur
l'évaluation (15) et le rapport (30) : les lots 12 et 14 sont prioritaires.

## Lot 11 — Validation par l'équipe
- [ ] Chacun clone le dépôt, lance `.\install.cmd` puis `.\start.cmd`, et note dans le journal : OS, RAM,
  carte graphique, mode GPU ou processeur, temps d'une réponse
- [ ] Valider le domaine du corpus (Brumeval, PME fictive de logistique, D-014) ou en choisir un autre :
  il suffit alors de réécrire `data/sources/*.md`, `data/knowledge.json` et `eval/questions.json`
- [ ] Relire les 20 documents (cohérence, aucune donnée réelle) et les 25 questions (réponse attendue juste,
  mots-clés pertinents)
- [ ] Ajouter 5 questions **reformulées** sans les mots du document (ex. « Je me marie en juin, j'ai droit à
  combien de jours ? ») : c'est là que la recherche sémantique devrait se distinguer de BM25

## Lot 12 — Analyse des résultats
- [ ] Remplir la colonne `verdict_manuel` de `reponses.csv` (juste / partiel / faux / hallucination) :
  le contrôle par mots-clés est indicatif
- [ ] Graphiques : Recall@k (BM25 vs sémantique), balayage des seuils (dans / hors corpus), latence par
  configuration, taux d'hallucination par configuration
- [ ] Analyse d'erreurs : Q09 (le modèle inverse 60 % / 40 % malgré le bon extrait), Q23 et Q25 (hors corpus
  mais proches du corpus : seul le refus du LLM les écarte), Q13 (score faible malgré le bon document)
- [ ] Relancer l'évaluation sur un PC avec une carte graphique récente (latence) : `scripts\eval.ps1`
- [ ] Facultatif : comparer un 2e modèle (`qwen2.5:3b` ou `llama3.2:3b`) et une 2e taille de fragments
  (380 mots) pour discuter les choix

## Lot 13 — Améliorations facultatives (seulement si le temps le permet)
- [ ] Boutons « Copier » et « Régénérer » sous les réponses (présents dans les maquettes)
- [ ] Afficher les extraits consultés quand le modèle répond sans citer
- [ ] Ouvrir le document source depuis une bulle de citation
- [ ] Interface : supprimer l'avertissement d'une conversation et mettre à jour la pastille « Questions sans
  réponse » sans recharger

## Lot 14 — Rapport (15 à 20 pages)
- [ ] Plan calé sur le barème : problème et objectifs (10), architecture (10), MVP et intégration IA (25),
  protocole de test et performances (15), conclusion et limites
- [ ] Sources réutilisables : `docs/plan-projet.pdf`, `docs/architecture.md`, `docs/design/`,
  `eval/README.md` (définition des métriques), journal et décisions de l'équipe
- [ ] Captures d'écran de l'application et schéma d'architecture
- [ ] Limites et perspectives : modèle 4B sur processeur (latence ~20 s), pas d'OCR, mono-utilisateur,
  multi-entreprise écarté du MVP

## Lot 15 — Soutenance et démo
- [ ] Répéter le scénario de [`demo.md`](demo.md) sur la machine de la soutenance (préchauffer le modèle)
- [ ] Diapositives (10 min) : problème, architecture, démo, résultats chiffrés, limites
- [ ] Vidéo de secours de la démo, au cas où la machine serait trop lente le jour J
