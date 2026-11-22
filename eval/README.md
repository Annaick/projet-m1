# Évaluation

Compare trois configurations sur les mêmes 25 questions :

1. **LLM seul** (sans recherche) — baseline exigée par l'énoncé
2. **BM25 + LLM** (recherche par mots-clés)
3. **RAG sémantique** (Qdrant + LLM) — notre système

## `questions.json`

Une entrée par question :

| Champ | Contenu |
|---|---|
| `id` | `Q01` à `Q25` |
| `question` | La question posée |
| `reponse_attendue` | La bonne réponse, rédigée à partir du corpus |
| `sources_attendues` | Nom(s) du ou des fichiers de `data/corpus/` qui contiennent la réponse (vide si hors corpus) |
| `dans_le_corpus` | `false` pour les ~5 questions volontairement hors corpus |

## Mesures

Recall@k, taux de réponses correctement sourcées, hallucinations, bons « je ne sais pas », temps de réponse.

Le script `run_eval.py` est à écrire ; les résultats bruts vont dans `results/` (non versionnés,
sauf ceux qu'on retient pour le rapport).
