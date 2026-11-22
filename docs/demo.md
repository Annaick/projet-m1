# Scénario de démonstration (≈ 10 minutes)

## Avant la soutenance

1. Ollama lancé, modèles présents (`ollama list` : `gemma3:4b`, `embeddinggemma`).
2. Base remise à zéro et corpus chargé :
   ```bash
   uvicorn app.main:app --app-dir backend          # terminal 1
   python data/load_corpus.py --reset              # terminal 2, une fois l'API lancée
   streamlit run frontend/app.py                   # terminal 3
   ```
3. Poser une première question « de chauffe » : le premier appel charge le modèle en mémoire (10 à 30 s).
4. Supprimer cette conversation de chauffe (menu ⋯ dans la barre latérale).
5. Avoir sous la main les résultats d'évaluation (`eval/results/<date>/rapport.md`).

## Déroulé

| # | Action | Ce qu'on montre |
|---|---|---|
| 1 | Ouvrir **Base de connaissances** | 20 fichiers (PDF, DOCX, TXT, MD), 1 texte riche, 6 FAQ, tous « Indexée » ; nombre de fragments par source ; « Voir le contenu indexé » sur un PDF (pages conservées) |
| 2 | Accueil → « Combien de jours de congés par an ? » | Réponse streamée, bulles de citation ; clic sur une bulle : extrait, document, page, score |
| 3 | Relance : « Et combien de jours de RTT ? » | La relance courte fonctionne grâce au contexte de la question précédente |
| 4 | « Comment réserver une salle de réunion ? » | Encadré « pas dans la base », aucun appel au LLM, la question part dans **Questions sans réponse** |
| 5 | **Questions sans réponse** → « Ajouter à la FAQ » avec une réponse inventée pour la démo | La FAQ est indexée en quelques secondes |
| 6 | Reposer la question sur la salle de réunion | L'assistant répond maintenant, en citant la nouvelle FAQ |
| 7 | **Paramètres de l'IA** : passer le ton à « chaleureux », ajouter une directive (« Termine par une phrase d'encouragement ») | Le comportement change sans redémarrer |
| 8 | Ajouter un fichier en direct (glisser un PDF) | Statut « Indexation… » puis « Indexée » |
| 9 | **Rechercher** « VPN » | Recherche dans les titres et le contenu des conversations |
| 10 | Résultats d'évaluation | LLM seul vs BM25 vs RAG : Recall@k, réponses sourcées, hallucinations, latence |

## Questions à préparer

- *Pourquoi un seuil ?* Sans seuil, le LLM reçoit toujours des extraits, même hors sujet, et a tendance à
  répondre quand même. Le balayage des seuils de l'évaluation justifie la valeur retenue.
- *Pourquoi Qdrant en mode local ?* Pas de serveur ni de Docker à installer ; même API que Qdrant serveur.
- *Et si le LLM invente malgré tout ?* Le prompt impose les citations ; une réponse sans citation est visible
  (« aucune source citée ») et l'évaluation mesure le taux d'hallucination.
- *Limites* : modèle de 4B (raisonnement limité, latence sur CPU), pas d'OCR, un seul utilisateur.
