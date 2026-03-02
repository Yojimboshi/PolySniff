"""Time utilities and helpers."""

from datetime import datetime, timedelta
from typing import Tuple


def parse_iso_timestamp(timestamp: str) -> datetime:
    """Parse ISO 8601 timestamp string."""
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return datetime.utcnow()


def get_date_range(days: int) -> Tuple[datetime, datetime]:
    """Get date range for last N days."""
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end


def hourly_timestamp(offset_hours: int = 0) -> datetime:
    """Get timestamp rounded to hour boundary."""
    now = datetime.utcnow() - timedelta(hours=offset_hours)
    return now.replace(minute=0, second=0, microsecond=0)


def trading_hours_remain_today() -> float:
    """Estimate hours remaining in trading day."""
    now = datetime.utcnow()
    end_of_day = now.replace(hour=23, minute=59, second=59)
    return (end_of_day - now).total_seconds() / 3600
