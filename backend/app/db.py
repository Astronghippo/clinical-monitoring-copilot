from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _normalize_url(url: str) -> str:
    """Railway/Heroku/etc. expose Postgres as `postgres://...` but SQLAlchemy
    with psycopg3 needs `postgresql+psycopg://...`. Translate on the fly."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_database_url = _normalize_url(settings.database_url)

# `check_same_thread=False` is needed only for SQLite; harmless for Postgres if not passed.
_engine_kwargs: dict = {"pool_pre_ping": True}
if _database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
