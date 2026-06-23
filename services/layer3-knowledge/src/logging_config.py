"""Structured logging configuration for Value Fabric Layer 3."""

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime

from value_fabric.shared.security.redaction import install_redaction_filter

try:
    from .config import Settings, get_settings
except ImportError as _import_exc:  # pragma: no cover - fallback for top-level module imports
    if "attempted relative import with no known parent package" in str(_import_exc):
        from src.config import Settings, get_settings
    else:
        raise


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production logging."""

    def __init__(
        self,
        timestamp_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
        include_module: bool = True,
        include_function: bool = True,
        include_line_number: bool = True,
    ):
        """Initialize JSON formatter.

        Args:
            timestamp_format: Format for timestamp strings
            include_module: Whether to include module name in logs
            include_function: Whether to include function name in logs
            include_line_number: Whether to include line number in logs
        """
        super().__init__()
        self.timestamp_format = timestamp_format
        self.include_module = include_module
        self.include_function = include_function
        self.include_line_number = include_line_number

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().strftime(self.timestamp_format),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add optional fields based on configuration
        if self.include_module and hasattr(record, "module"):
            log_entry["module"] = record.module
        elif self.include_module:
            log_entry["module"] = record.name.split(".")[-1]

        if self.include_function and hasattr(record, "funcName"):
            log_entry["function"] = record.funcName

        if self.include_line_number and hasattr(record, "lineno"):
            log_entry["line_number"] = record.lineno

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add request ID if present (from middleware)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Add any extra fields
        extra_fields = set(record.__dict__.keys()) - {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
            "request_id",
            "message",
        }

        for key in extra_fields:
            log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """Configured structured logger with JSON formatting."""

    def __init__(self, settings: Settings | None = None):
        """Initialize structured logger.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or get_settings()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure root logger with structured formatting."""
        # Get the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.log_level.upper()))
        redaction_filter = install_redaction_filter(root_logger)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create formatter based on configuration
        if self.settings.log_format.lower() == "json":
            formatter = JSONFormatter(
                timestamp_format=self.settings.log_timestamp_format,
                include_module=self.settings.log_include_module,
                include_function=self.settings.log_include_function,
                include_line_number=self.settings.log_include_line_number,
            )
        else:
            # Text formatter for development
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt=self.settings.log_timestamp_format,
            )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, self.settings.log_level.upper()))
        console_handler.addFilter(redaction_filter)
        root_logger.addHandler(console_handler)

        # File handler for ERROR level and above (if needed)
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(redaction_filter)
        root_logger.addHandler(error_handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance with the given name.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)


def setup_logging(settings: Settings | None = None) -> None:
    """Setup structured logging for the application.

    Args:
        settings: Application settings. If None, loads from environment.
    """
    StructuredLogger(settings)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return StructuredLogger.get_logger(name)
