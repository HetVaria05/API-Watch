"""
database.py - Database connection and session management.

Uses SQLAlchemy to connect to a local SQLite database.
The database file is stored in the 'data/' directory.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

# Build the path to the SQLite database file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'apiwatch.db')}"

# Create the SQLAlchemy engine
# check_same_thread=False is needed for SQLite with FastAPI (multi-threaded)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """
    Dependency that provides a database session.
    Used with FastAPI's Depends() to inject a session into route handlers.
    The session is automatically closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
