"""Structured logging configuration.

Provides a single `get_logger` accessor so every module logs consistently.

SCAFFOLD: thin placeholder around the stdlib; swap to structlog when needed.
"""

from __future__ import annotations

import logging

from app.config.settings import get_settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    return logging.getLogger(name)
