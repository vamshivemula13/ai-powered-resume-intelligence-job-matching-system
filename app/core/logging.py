"""
Centralized Structured Logging Infrastructure.

Provides standardized logging formats across CLI, background services,
and API route handlers with contextual timestamps and log levels.
"""

import logging
import sys

from app.core.config import settings


def setup_logging(level: str | None = None) -> None:
    """
    Initialize application-wide logging configuration.

    Args:
        level: Optional log level override ('DEBUG', 'INFO', 'WARNING', etc.).
               If omitted, defaults to DEBUG if settings.debug is True, else INFO.
    """
    if level is None:
        log_level = logging.DEBUG if settings.debug else logging.INFO
    else:
        log_level = getattr(logging, level.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Obtain a named logger scoped to a module or service.

    Usage:
        logger = get_logger(__name__)
        logger.info("PDF extraction started for file: %s", filename)
    """
    return logging.getLogger(name)
