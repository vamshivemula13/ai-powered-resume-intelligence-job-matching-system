"""
Unit Tests for Logging Infrastructure (app/core/logging.py).
"""

import logging

from app.core.logging import get_logger, setup_logging


def test_setup_logging_configures_root_logger() -> None:
    """Verify that setup_logging configures root logger handlers and levels."""
    setup_logging(level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) > 0


def test_get_logger_returns_named_logger() -> None:
    """Verify get_logger returns a Logger with the specified module name."""
    logger = get_logger("app.test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.test_module"
