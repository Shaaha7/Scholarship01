"""
Structured Logging Configuration
==================================
Production-ready structured logging with structlog.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add application context to log entries."""
    event_dict["app"] = settings.APP_NAME
    event_dict["version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Drop color message key for cleaner logs."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_structlog() -> None:
    """Configure structlog for the application."""
    
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_app_context,
    ]
    
    if settings.DEBUG:
        # Development: pretty console output
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.UnicodeDecoder(),
                drop_color_message_key,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.DEBUG,
        )
    else:
        # Production: JSON output for log aggregation
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Initialize logging on import
configure_structlog()
