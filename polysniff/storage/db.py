"""Database session and context management."""

from contextlib import contextmanager
from typing import Generator

from polysniff.config import get_logger
from .models import DatabaseSession

logger = get_logger()

# Global database instance
_db_instance: DatabaseSession = None


def get_db() -> DatabaseSession:
    """Get database instance (singleton)."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseSession()
    return _db_instance


@contextmanager
def db_session() -> Generator:
    """Context manager for database sessions."""
    db = get_db()
    session = db.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database."""
    db = get_db()
    logger.info("Database initialized")


def close_db() -> None:
    """Close database connection."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
