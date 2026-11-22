from sqlmodel import Session, SQLModel, create_engine, select

from app.db import init_db
from app.models import AISettings, Chunk, Source, SourceType


def make_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False})


def test_tables_creees():
    engine = make_engine()
    init_db(engine)
    noms = set(SQLModel.metadata.tables)
    assert {"conversation", "message", "citation", "source", "chunk", "ai_settings", "knowledge_gap"} <= noms


def test_parametres_par_defaut_une_seule_ligne():
    engine = make_engine()
    init_db(engine)
    init_db(engine)  # idempotent
    with Session(engine) as session:
        lignes = session.exec(select(AISettings)).all()
        assert len(lignes) == 1
        assert lignes[0].top_k > 0
        assert "[1]" in lignes[0].system_prompt


def test_source_et_chunks():
    engine = make_engine()
    init_db(engine)
    with Session(engine) as session:
        source = Source(type=SourceType.faq, title="Congés", question="Combien ?", answer="25 jours")
        session.add(source)
        session.commit()
        session.add(Chunk(source_id=source.id, position=0, text="Q : Combien ? R : 25 jours"))
        session.commit()
        assert source.status == "pending"
        assert len(session.exec(select(Chunk)).all()) == 1
