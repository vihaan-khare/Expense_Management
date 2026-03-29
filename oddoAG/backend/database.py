"""Database initialization and session management."""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase
from config import Config


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Resolve database path
db_url = Config.DATABASE_URL
if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    # Relative SQLite path — resolve from project root
    relative_path = db_url.replace("sqlite:///", "")
    abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), relative_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    db_url = f"sqlite:///{abs_path}"

engine = create_engine(
    db_url,
    echo=Config.DEBUG,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
)

# Enable WAL mode and foreign keys for SQLite (better concurrent performance)
if "sqlite" in db_url:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
db_session = scoped_session(SessionLocal)


def init_db():
    """Create all tables. Import models first so they are registered."""
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized")


def get_db():
    """Get a database session. Use in a with statement or call .close()."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
