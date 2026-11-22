"""Charge le corpus de démonstration dans l'application, via l'API (qui doit être lancée).

    python data/load_corpus.py            # ajoute les fichiers, le texte riche et la FAQ
    python data/load_corpus.py --reset    # supprime d'abord toutes les sources existantes
"""
import argparse
import json
import mimetypes
import sys
import time
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--reset", action="store_true", help="supprime toutes les sources avant le chargement")
    args = parser.parse_args()
    api = httpx.Client(base_url=args.api, timeout=600)

    if args.reset:
        for source in api.get("/knowledge/sources").json():
            api.delete(f"/knowledge/sources/{source['id']}").raise_for_status()
        print("Base vidée.")

    files = sorted(p for p in (DATA / "corpus").iterdir() if p.suffix in {".pdf", ".docx", ".txt", ".md"} and p.name != "README.md")
    if not files:
        print("Aucun document dans data/corpus : lancez d'abord python data/build_corpus.py")
        return 1
    started = time.perf_counter()
    for path in files:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        api.post("/knowledge/sources/files", files=[("files", (path.name, path.read_bytes(), mime))]).raise_for_status()
        print(f"fichier    {path.name}")

    extra = json.loads((DATA / "knowledge.json").read_text(encoding="utf-8"))
    for item in extra["richtext"]:
        api.post("/knowledge/sources/richtext", json=item).raise_for_status()
        print(f"texte      {item['title']}")
    for item in extra["faq"]:
        api.post("/knowledge/sources/faq", json=item).raise_for_status()
        print(f"faq        {item['question']}")

    print("Indexation en cours…")
    while True:
        summary = api.get("/knowledge/summary").json()
        busy = summary["by_status"]["pending"] + summary["by_status"]["indexing"]
        if not busy:
            break
        time.sleep(2)
    errors = [s for s in api.get("/knowledge/sources").json() if s["status"] == "error"]
    for s in errors:
        print(f"ERREUR     {s['title']} : {s['error']}")
    print(
        f"{summary['sources']} sources, {summary['chunks']} fragments indexés "
        f"en {time.perf_counter() - started:.0f} s ({len(errors)} erreur(s))."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
