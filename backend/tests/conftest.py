import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def client_with_sqlite():
    # Use a temporary file-based SQLite database instead of in-memory
    # to ensure the connection persists across thread boundaries in TestClient
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(engine)

        def _override_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        # Patch SessionLocal in every route module that has a background task
        # using it (otherwise the background task writes to the prod SessionLocal).
        import app.routes.analyses as analyses_mod
        import app.routes.protocols as protocols_mod
        originals = {
            analyses_mod: analyses_mod.SessionLocal,
            protocols_mod: protocols_mod.SessionLocal,
        }
        for mod in originals:
            mod.SessionLocal = TestSession
        app.dependency_overrides[get_db] = _override_db

        client = TestClient(app)
        try:
            yield client
        finally:
            for mod, orig in originals.items():
                mod.SessionLocal = orig
            app.dependency_overrides.clear()
    finally:
        import os
        os.close(db_fd)
        Path(db_path).unlink(missing_ok=True)
