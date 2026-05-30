"""
M0.4 -- Structured Logging

SPEC: docs/modules/M0_4_structured_logging_SPEC.md
"""
from .writer import AsyncLogWriter, LogWriter, get_logger

__all__ = ["AsyncLogWriter", "LogWriter", "get_logger"]
