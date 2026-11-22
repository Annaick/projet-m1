# Corpus : Brumeval (société fictive)

Brumeval est une PME **fictive** de transport et de logistique (182 salariés, siège à Nantes). Le corpus est sa
documentation interne RH et informatique : congés, RTT, télétravail, notes de frais, mutuelle, sécurité,
VPN, support… Toute ressemblance avec une entreprise réelle serait fortuite ; les adresses mail sont en
`.example`, les numéros de téléphone sont fictifs.

- 20 documents dans ce dossier : 9 PDF, 4 DOCX, 3 TXT, 4 MD, pour tester l'extraction sur tous les formats.
- Plus, dans `data/knowledge.json` : 1 texte riche (« Mémo paie ») et 6 entrées de FAQ.

**Ne pas modifier les fichiers de ce dossier à la main** : ils sont générés depuis `data/sources/*.md`.

```bash
python data/build_corpus.py   # régénère data/corpus/
python data/load_corpus.py    # charge le tout dans l'application (API lancée)
```

Chaque réponse de `eval/questions.json` doit pouvoir se retrouver dans ces documents.
