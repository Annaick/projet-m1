# Évaluation

Compare trois configurations sur les mêmes 25 questions :

| Configuration | Recherche | Rôle |
|---|---|---|
| `llm` | aucune | baseline exigée par l'énoncé |
| `bm25` | mots-clés (BM25 sur les fragments) | point de comparaison classique |
| `rag` | sémantique (Qdrant) + seuil de pertinence | le système de l'application |

Les trois utilisent le même modèle, la même température et le même top-k (ceux des paramètres de l'IA).

## Lancer

L'API doit être **arrêtée** (Qdrant en mode local n'accepte qu'un processus), le corpus chargé et Ollama lancé.

```bash
python eval/run_eval.py --retrieval-only     # recherche seule : Recall@k, MRR, balayage des seuils
python eval/run_eval.py                      # tout
python eval/run_eval.py --configs rag --limit 5
```

Sortie dans `results/<date>/` :
- `rapport.md` : tableaux prêts pour le rapport ;
- `resume.json` : toutes les valeurs, plus les 5 meilleurs extraits sémantiques par question ;
- `reponses.csv` (séparateur `;`, s'ouvre dans Excel) : une ligne par question et configuration,
  avec une colonne `verdict_manuel` à remplir.

## `questions.json`

| Champ | Contenu |
|---|---|
| `id` | `Q01` à `Q25` |
| `question` | La question posée |
| `reponse_attendue` | La bonne réponse, rédigée à partir du corpus (`null` hors corpus) |
| `mots_cles` | Éléments qui doivent figurer dans une réponse juste (contrôle automatique) |
| `sources_attendues` | Titre(s) de la ou des sources qui contiennent la réponse : nom de fichier, titre du texte riche ou question de la FAQ |
| `dans_le_corpus` | `false` pour les 5 questions volontairement hors corpus (Q21 à Q25, dont une question piège) |

## Métriques

| Métrique | Définition |
|---|---|
| Recall@k | Part des questions du corpus dont au moins une source attendue figure dans les k premiers extraits |
| MRR | Moyenne de 1 / rang de la première source attendue |
| Réponses exactes | L'assistant répond et tous les mots-clés attendus sont présents (à confirmer à la main) |
| Réponses correctement sourcées | L'assistant répond et cite au moins une source attendue |
| Refus à tort | Question du corpus à laquelle l'assistant dit ne pas savoir |
| Bons « je ne sais pas » | Question hors corpus à laquelle l'assistant refuse de répondre |
| Hallucinations (hors corpus) | Question hors corpus à laquelle l'assistant répond quand même |
| Latence | Temps entre la question et la fin de la réponse |

Le balayage des seuils (0,30 à 0,70) montre, pour chaque seuil, la part des questions du corpus encore
traitées et la part des questions hors corpus refusées : il sert à justifier le seuil retenu.
