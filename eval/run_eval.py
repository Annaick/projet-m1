"""Banc d'évaluation : compare 3 configurations sur les 25 questions de référence.

  llm   : LLM seul, sans recherche documentaire (baseline exigée par l'énoncé)
  bm25  : recherche lexicale BM25 + LLM
  rag   : recherche sémantique (Qdrant) + seuil + LLM : la configuration de l'application

Il lit directement la base de l'application (storage/). Qdrant en mode local ne
supporte qu'un processus à la fois : **arrêtez l'API avant de lancer le banc.**

    python eval/run_eval.py                    # tout (recherche + génération), ~10-20 min
    python eval/run_eval.py --retrieval-only   # Recall@k et seuils seulement (rapide, sans LLM)
    python eval/run_eval.py --configs rag --limit 5
"""
import argparse
import csv
import json
import statistics
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlmodel import Session  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import AISettings  # noqa: E402
from app.rag import answer, ollama, vectorstore  # noqa: E402
from app.rag.bm25 import BM25Index  # noqa: E402

KS = [1, 3, 5, 10]
THRESHOLDS = [round(0.30 + 0.05 * i, 2) for i in range(9)]  # 0,30 → 0,70

LLM_ONLY_SYSTEM = (
    "Tu es l'assistant documentaire interne de l'entreprise Brumeval. Réponds à la question de l'utilisateur en français. "
    f"Si tu ne connais pas la réponse, réponds exactement : « {answer.REFUSAL} »"
)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace(" ", " ").replace(" ", " ")
    return " ".join(text.split())


def keywords_ok(text: str, keywords: list[str]) -> bool:
    return all(norm(k) in norm(text) for k in keywords)


def hit(extracts, expected: list[str], k: int) -> bool:
    return any(e.title in expected for e in extracts[:k])


# --- Recherche seule ---------------------------------------------------------------

def retrieval_metrics(session: Session, questions: list[dict], bm25: BM25Index) -> dict:
    in_corpus = [q for q in questions if q["dans_le_corpus"]]
    kmax = max(KS)
    semantic = {q["id"]: answer.retrieve(session, q["question"], kmax) for q in questions}
    lexical = {q["id"]: bm25.search(q["question"], kmax) for q in questions}

    recall = {
        name: {k: sum(hit(results[q["id"]], q["sources_attendues"], k) for q in in_corpus) / len(in_corpus) for k in KS}
        for name, results in (("bm25", lexical), ("semantique", semantic))
    }
    mrr = {}
    for name, results in (("bm25", lexical), ("semantique", semantic)):
        total = 0.0
        for q in in_corpus:
            rank = next((i + 1 for i, e in enumerate(results[q["id"]]) if e.title in q["sources_attendues"]), None)
            total += 1 / rank if rank else 0
        mrr[name] = total / len(in_corpus)

    # Meilleur score sémantique : séparation entre questions dans / hors corpus → choix du seuil
    best = {q["id"]: (semantic[q["id"]][0].score if semantic[q["id"]] else 0.0) for q in questions}
    sweep = []
    for t in THRESHOLDS:
        answered_in = sum(best[q["id"]] >= t for q in in_corpus) / len(in_corpus)
        out = [q for q in questions if not q["dans_le_corpus"]]
        refused_out = sum(best[q["id"]] < t for q in out) / len(out) if out else 0
        sweep.append({"seuil": t, "dans_corpus_au_dessus": answered_in, "hors_corpus_refusees": refused_out})
    return {
        "recall_at_k": recall,
        "mrr": mrr,
        "meilleur_score": best,
        "seuils": sweep,
        "top_semantique": {qid: [(e.title, e.score) for e in r[:5]] for qid, r in semantic.items()},
    }


# --- Génération ---------------------------------------------------------------------

def generate(messages: list[dict], ai: AISettings) -> str:
    return "".join(ollama.chat_stream(messages, ai.llm_model, ai.temperature))


def run_config(config: str, session: Session, ai: AISettings, q: dict, bm25: BM25Index) -> dict:
    started = time.perf_counter()
    extracts, cited = [], []
    if config == "llm":
        text = generate([{"role": "system", "content": LLM_ONLY_SYSTEM}, {"role": "user", "content": q["question"]}], ai)
        answered = not answer.is_refusal(text)
    elif config == "bm25":
        extracts = bm25.search(q["question"], ai.top_k)
        text = generate(answer.build_messages(ai, extracts, q["question"]), ai) if extracts else answer.NOT_IN_BASE
        answered = bool(extracts) and not answer.is_refusal(text)
        by_rank = {e.rank: e for e in extracts}
        cited = [by_rank[r].title for r in answer.cited_ranks(text, len(extracts))] if answered else []
    else:
        final = None
        for event in answer.answer_stream(session, ai, q["question"]):
            if event["type"] == "done":
                final = event
        text, answered = final["text"], final["answered"]
        cited = [c["title"] for c in final["citations"]]
    latency = int((time.perf_counter() - started) * 1000)

    expected = q["sources_attendues"]
    return {
        "id": q["id"],
        "config": config,
        "question": q["question"],
        "dans_le_corpus": q["dans_le_corpus"],
        "reponse": text.strip(),
        "repond": answered,
        "sources_citees": sorted(set(cited)),
        "bien_sourcee": answered and any(c in expected for c in cited),
        "mots_cles_ok": answered and keywords_ok(text, q["mots_cles"]) if q["dans_le_corpus"] else None,
        "latence_ms": latency,
    }


def summarize(rows: list[dict]) -> dict:
    inside = [r for r in rows if r["dans_le_corpus"]]
    outside = [r for r in rows if not r["dans_le_corpus"]]
    latencies = [r["latence_ms"] for r in rows]

    def rate(items, pred):
        return round(sum(1 for r in items if pred(r)) / len(items), 3) if items else None

    return {
        "questions": len(rows),
        "exactes_dans_corpus": rate(inside, lambda r: r["mots_cles_ok"]),
        "bien_sourcees_dans_corpus": rate(inside, lambda r: r["bien_sourcee"]),
        "refus_a_tort": rate(inside, lambda r: not r["repond"]),
        "bons_je_ne_sais_pas": rate(outside, lambda r: not r["repond"]),
        "hallucinations_hors_corpus": rate(outside, lambda r: r["repond"]),
        "reponses_inexactes_dans_corpus": rate(inside, lambda r: r["repond"] and not r["mots_cles_ok"]),
        "latence_moyenne_s": round(statistics.mean(latencies) / 1000, 2) if latencies else None,
        "latence_mediane_s": round(statistics.median(latencies) / 1000, 2) if latencies else None,
        "latence_max_s": round(max(latencies) / 1000, 2) if latencies else None,
    }


# --- Rapport ---------------------------------------------------------------------------

def pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f} %"


def markdown_report(meta: dict, retrieval: dict, summaries: dict) -> str:
    lines = [
        f"# Résultats de l'évaluation ({meta['date']})",
        "",
        f"Modèle : `{meta['llm']}` · embeddings : `{meta['embedding']}` · top-k : {meta['top_k']} · "
        f"seuil : {meta['seuil']} · température : {meta['temperature']} · {meta['questions']} questions",
        "",
        "## Recherche : Recall@k (questions dans le corpus)",
        "",
        "| Méthode | " + " | ".join(f"R@{k}" for k in KS) + " | MRR |",
        "|---|" + "---|" * (len(KS) + 1),
    ]
    for name, values in retrieval["recall_at_k"].items():
        lines.append(f"| {name} | " + " | ".join(pct(values[k]) for k in KS) + f" | {retrieval['mrr'][name]:.2f} |")
    lines += [
        "",
        "## Choix du seuil de pertinence (recherche sémantique)",
        "",
        "| Seuil | Questions du corpus au-dessus | Questions hors corpus refusées |",
        "|---|---|---|",
    ]
    for row in retrieval["seuils"]:
        lines.append(f"| {row['seuil']:.2f} | {pct(row['dans_corpus_au_dessus'])} | {pct(row['hors_corpus_refusees'])} |")
    if summaries:
        labels = {"llm": "LLM seul", "bm25": "BM25 + LLM", "rag": "RAG sémantique"}
        lines += [
            "",
            "## Réponses générées",
            "",
            "| Métrique | " + " | ".join(labels[c] for c in summaries) + " |",
            "|---|" + "---|" * len(summaries),
        ]
        metrics = [
            ("Réponses exactes (corpus, mots-clés)", "exactes_dans_corpus", pct),
            ("Réponses correctement sourcées (corpus)", "bien_sourcees_dans_corpus", pct),
            ("Refus à tort (corpus)", "refus_a_tort", pct),
            ("Bons « je ne sais pas » (hors corpus)", "bons_je_ne_sais_pas", pct),
            ("Hallucinations (hors corpus)", "hallucinations_hors_corpus", pct),
            ("Réponses inexactes (corpus)", "reponses_inexactes_dans_corpus", pct),
            ("Latence moyenne", "latence_moyenne_s", lambda x: f"{x:.1f} s".replace(".", ",")),
            ("Latence médiane", "latence_mediane_s", lambda x: f"{x:.1f} s".replace(".", ",")),
        ]
        for label, key, fmt in metrics:
            lines.append(f"| {label} | " + " | ".join(fmt(s[key]) for s in summaries.values()) + " |")
        lines += [
            "",
            "« Exactes » : les mots-clés de la réponse attendue figurent dans la réponse. Ce contrôle automatique est à "
            "confirmer à la main dans `reponses.csv` (colonne `verdict_manuel`).",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", default="llm,bm25,rag")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="nombre de questions (essais rapides)")
    parser.add_argument("--questions", default=str(ROOT / "eval" / "questions.json"))
    args = parser.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))[: args.limit]
    init_db()
    out_dir = ROOT / "eval" / "results" / datetime.now().strftime("%Y-%m-%d_%H%M")
    out_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        ai = session.get(AISettings, 1)
        from app.config import settings

        meta = {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "llm": ai.llm_model,
            "embedding": settings.embedding_model,
            "top_k": ai.top_k,
            "seuil": ai.score_threshold,
            "temperature": ai.temperature,
            "questions": len(questions),
        }
        bm25 = BM25Index(session)
        if not bm25.items:
            print("La base est vide : chargez le corpus (python data/load_corpus.py) avant d'évaluer.")
            return 1
        print("Recherche : Recall@k…")
        retrieval = retrieval_metrics(session, questions, bm25)

        rows, summaries = [], {}
        if not args.retrieval_only:
            for config in args.configs.split(","):
                config_rows = []
                for q in questions:
                    row = run_config(config, session, ai, q, bm25)
                    config_rows.append(row)
                    state = "répond" if row["repond"] else "refuse"
                    print(f"[{config:4}] {q['id']} {state:7} {row['latence_ms'] / 1000:5.1f} s  {row['reponse'][:70]!r}")
                summaries[config] = summarize(config_rows)
                rows += config_rows

    (out_dir / "resume.json").write_text(
        json.dumps({"meta": meta, "recherche": retrieval, "generation": summaries}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if rows:
        with open(out_dir / "reponses.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[*rows[0].keys(), "verdict_manuel"], delimiter=";")
            writer.writeheader()
            for row in rows:
                writer.writerow({**row, "sources_citees": ", ".join(row["sources_citees"]), "verdict_manuel": ""})
    report = markdown_report(meta, retrieval, summaries)
    (out_dir / "rapport.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Résultats : {out_dir}")
    vectorstore.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
