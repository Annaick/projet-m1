# Résultats de l'évaluation (22/11/2026 16:23)

Modèle : `gemma3:4b` · embeddings : `embeddinggemma` · top-k : 3 · seuil : 0.3 · température : 0.2 · 25 questions

## Recherche : Recall@k (questions dans le corpus)

| Méthode | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| bm25 | 95 % | 100 % | 100 % | 100 % | 0.97 |
| semantique | 100 % | 100 % | 100 % | 100 % | 1.00 |

## Choix du seuil de pertinence (recherche sémantique)

| Seuil | Questions du corpus au-dessus | Questions hors corpus refusées |
|---|---|---|
| 0.30 | 100 % | 20 % |
| 0.35 | 95 % | 40 % |
| 0.40 | 95 % | 60 % |
| 0.45 | 90 % | 60 % |
| 0.50 | 80 % | 60 % |
| 0.55 | 55 % | 60 % |
| 0.60 | 35 % | 80 % |
| 0.65 | 15 % | 100 % |
| 0.70 | 0 % | 100 % |

## Réponses générées

| Métrique | LLM seul, sans consigne | LLM seul | BM25 + LLM | RAG sémantique |
|---|---|---|---|---|
| Réponses exactes (corpus, mots-clés) | 35 % | 0 % | 95 % | 95 % |
| Réponses correctement sourcées (corpus) | 0 % | 0 % | 95 % | 95 % |
| Refus à tort (corpus) | 0 % | 100 % | 0 % | 0 % |
| Bons « je ne sais pas » (hors corpus) | 0 % | 100 % | 100 % | 100 % |
| Hallucinations (hors corpus) | 100 % | 0 % | 0 % | 0 % |
| Réponses inexactes (corpus) | 65 % | 0 % | 5 % | 5 % |
| Latence moyenne | 3,5 s | 3,2 s | 19,8 s | 20,9 s |
| Latence médiane | 3,4 s | 3,2 s | 20,4 s | 20,6 s |

« Exactes » : les mots-clés de la réponse attendue figurent dans la réponse. Ce contrôle automatique est à confirmer à la main dans `reponses.csv` (colonne `verdict_manuel`).
