"""Logging configuration and setup."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .settings import LoggingConfig


class LoggerSetup:
    """Configure loguru for consistent logging across the application."""

    _initialized = False

    @classmethod
    def setup(cls, config: LoggingConfig, rotation_time: str = "00:00") -> None:
        """
        Initialize logging with the provided configuration.

        Args:
            config: LoggingConfig instance with logging parameters
            rotation_time: Time for daily log rotation in HH:MM format
        """
        if cls._initialized:
            return

        # Remove default handler
        logger.remove()

        # Ensure log directory exists
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Console output
        logger.add(
            sys.stdout,
            level=config.level,
            format=config.format,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        # File output with rotation
        logger.add(
            config.file_path,
            level=config.level,
            format=config.format,
            rotation=config.max_file_size,
            retention=config.backup_count,
            colorize=False,
            backtrace=True,
            diagnose=False,
        )

        cls._initialized = True
        logger.info(f"Logging initialized at level {config.level}")

    @classmethod
    def get_logger(cls):
        """Get logger instance."""
        return logger


def get_logger():
    """Convenience function to get logger."""
    return LoggerSetup.get_logger()
