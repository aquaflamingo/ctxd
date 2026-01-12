"""
Logging configuration for ctxd.

Provides centralized logging setup with support for console and file outputs,
rotating log files, and optional JSON formatting.
"""

import logging
import sys
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = False,
    max_log_size_mb: int = 10,
    log_backups: int = 5,
) -> None:
    """
    Configure application-wide logging for ctxd.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for file output
        json_format: Use JSON formatting for logs
        max_log_size_mb: Maximum log file size in MB before rotation
        log_backups: Number of backup log files to keep

    Example:
        setup_logging(level="DEBUG", log_file=Path(".ctxd/ctxd.log"))
    """
    # Create formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handlers = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    handlers.append(console_handler)

    # File handler (rotating, optional)
    if log_file:
        try:
            # Ensure log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            file_handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
                backupCount=log_backups,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level.upper()))
            handlers.append(file_handler)

            root_logger.info(f"Logging to file: {log_file}")

        except Exception as e:
            # Fallback to console-only logging if file handler fails
            root_logger.warning(f"Failed to set up file logging: {e}. Using console only.")

    # Add all handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)

    # Log initial setup message
    root_logger.info(
        f"Logging initialized: level={level}, "
        f"file={'enabled' if log_file else 'disabled'}, "
        f"format={'JSON' if json_format else 'text'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    Dynamically change the log level for all loggers.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    for handler in root_logger.handlers:
        handler.setLevel(getattr(logging, level.upper()))

    root_logger.info(f"Log level changed to: {level}")
