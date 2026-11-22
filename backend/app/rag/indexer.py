"""File d'indexation : un seul fil d'exécution indexe les sources, l'une après l'autre.

Les routes d'envoi répondent tout de suite et déposent l'id de la source dans la file.
(Avec les BackgroundTasks de FastAPI, chaque tâche en attente gardait une connexion SQLite
ouverte : au-delà de ~15 envois d'affilée, le pool de connexions saturait.)
"""
import logging
import queue
import threading

from sqlmodel import Session

from app import db
from app.rag import ingestion

log = logging.getLogger(__name__)

# Vrai dans les tests : indexation immédiate, dans le fil de la requête
SYNCHRONOUS = False

_queue: "queue.Queue[int]" = queue.Queue()
_worker: threading.Thread | None = None
_start_lock = threading.Lock()


def _index(source_id: int) -> None:
    with Session(db.engine) as session:
        ingestion.index_source(session, source_id)


def _run() -> None:
    while True:
        source_id = _queue.get()
        try:
            _index(source_id)
        except Exception:  # noqa: BLE001  (la source passe en erreur dans index_source)
            log.exception("Indexation de la source %s impossible", source_id)
        finally:
            _queue.task_done()


def enqueue(source_id: int) -> None:
    global _worker
    if SYNCHRONOUS:
        _index(source_id)
        return
    with _start_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="indexation", daemon=True)
            _worker.start()
    _queue.put(source_id)


def wait_idle() -> None:
    """Attend la fin des indexations en cours (utile aux scripts)."""
    _queue.join()
