"""Shared test fixtures — SQLite in-memory database for all tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy import event as sqla_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from program.db import db
from program.db.base_model import get_base_metadata


@pytest.fixture(scope="session", autouse=True)
def _sqlite_db():
    """
    Session-wide in-memory SQLite engine.

    Replaces the default Postgres engine so every db_session() call and
    SQLAlchemy session used by production code hits SQLite during tests.
    Tables are created directly from the ORM models (no Alembic migrations)
    so there is no dependency on Docker or a live Postgres instance.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqla_event.listens_for(engine, "connect")
    def _enable_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    get_base_metadata().create_all(engine)

    db.engine = engine
    db.Session.configure(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture(scope="function")
def db_engine(_sqlite_db):
    """Expose the session-wide SQLite engine (backward-compat alias)."""
    return _sqlite_db


@pytest.fixture(scope="function")
def test_scoped_db_session(db_engine):
    """
    Per-test SQLAlchemy session.  All rows are deleted after each test so
    tests remain isolated without needing to recreate the schema.
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        metadata = get_base_metadata()
        with db_engine.connect() as conn:
            for table in reversed(metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()
