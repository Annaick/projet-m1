"""Connexion SQLite et création des tables."""
from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (enregistre les tables)
from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def init_db(bind: Engine | None = None) -> None:
    """Crée les tables et la ligne de paramètres IA par défaut."""
    bind = bind or engine
    SQLModel.metadata.create_all(bind)
    with Session(bind) as session:
        if session.get(models.AISettings, 1) is None:
            session.add(
                models.AISettings(
                    llm_model=settings.llm_model,
                    temperature=settings.default_temperature,
                    top_k=settings.default_top_k,
                    score_threshold=settings.default_score_threshold,
                )
            )
            session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
