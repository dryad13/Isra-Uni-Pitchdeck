from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_config, reload_config
from app.db.base import Base
from app.paths import FROZEN, RESOURCE_DIR

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _sqlite_pragma(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def _sqlite_url() -> str:
    cfg = get_config()
    db_path = cfg.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _backend_dir() -> Path:
    # Dev: backend/app/db/session.py -> backend/
    # Frozen: migrations ship under sys._MEIPASS (see omr.spec).
    if FROZEN:
        return RESOURCE_DIR
    return Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    backend_dir = _backend_dir()
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _sqlite_url())
    return cfg


def _bind_engine() -> None:
    global engine, SessionLocal
    engine = create_engine(
        _sqlite_url(),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    event.listen(engine, "connect", _sqlite_pragma)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def reset_engine() -> None:
    """Dispose and recreate the DB engine (used by test harness)."""
    global engine, SessionLocal
    if engine is not None:
        engine.dispose()
    engine = None
    SessionLocal = None
    reload_config()
    _bind_engine()


_bind_engine()


def run_migrations() -> None:
    """Apply Alembic migrations to head."""
    command.upgrade(_alembic_config(), "head")


def init_db() -> None:
    from app.db import models  # noqa: F401

    assert engine is not None
    run_migrations()


def get_db():
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
