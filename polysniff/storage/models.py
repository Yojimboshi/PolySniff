"""Database models and ORM configuration."""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from enum import Enum as PyEnum

from polysniff.config import get_settings, get_logger

logger = get_logger()

Base = declarative_base()


class TradeStatus(PyEnum):
    """Trade execution status."""

    PENDING = "PENDING"
    OPENED = "OPENED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Trade(Base):
    """Represents a single trade in the database."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False)
    market_id = Column(String(100), nullable=False)
    side = Column(String(10), nullable=False)  # YES or NO
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    status = Column(Enum(TradeStatus), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, market_id={self.market_id}, "
            f"side={self.side}, status={self.status})>"
        )


class MarketSnapshot(Base):
    """Historical market price snapshots."""

    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True)
    market_id = Column(String(100), nullable=False)
    yes_price = Column(Float, nullable=False)
    no_price = Column(Float, nullable=False)
    volume_24h = Column(Float, nullable=False)
    liquidity = Column(Float, nullable=False)
    fair_probability = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<MarketSnapshot(market_id={self.market_id}, "
            f"yes={self.yes_price:.4f}, no={self.no_price:.4f}, "
            f"ts={self.timestamp})>"
        )


class Prediction(Base):
    """Model prediction history."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    market_id = Column(String(100), nullable=False)
    fair_probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    model_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Prediction(market_id={self.market_id}, "
            f"prob={self.fair_probability:.4f}, ts={self.timestamp})>"
        )


class DatabaseSession:
    """Database connection and session management."""

    def __init__(self):
        self.config = get_settings()
        self.engine = None
        self.SessionLocal = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                self.config.storage.db_url,
                echo=self.config.storage.echo_sql,
                pool_size=self.config.storage.pool_size,
                max_overflow=self.config.storage.max_overflow,
            )

            self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

            # Create tables
            Base.metadata.create_all(self.engine)
            logger.info(f"Database initialized: {self.config.storage.db_url}")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_session(self):
        """Get new database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()

    def save_trade(self, trade: Trade) -> None:
        """Save trade to database."""
        session = self.get_session()
        try:
            session.add(trade)
            session.commit()
            logger.debug(f"Trade saved: {trade.order_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save trade: {e}")
        finally:
            session.close()

    def save_snapshot(self, snapshot: MarketSnapshot) -> None:
        """Save market snapshot."""
        session = self.get_session()
        try:
            session.add(snapshot)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save snapshot: {e}")
        finally:
            session.close()

    def save_prediction(self, prediction: Prediction) -> None:
        """Save prediction record."""
        session = self.get_session()
        try:
            session.add(prediction)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save prediction: {e}")
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database closed")
