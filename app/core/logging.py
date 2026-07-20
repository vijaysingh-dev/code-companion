import logging
import logging.config
from pathlib import Path

from app.core.config import settings
from app.core.constants import BASE_DIR

_configured = False


class RelativePathFormatter(logging.Formatter):
    """Render `pathname` relative to BASE_DIR so log lines read `app/api/chat.py:42`.

    Records originating from installed packages (under `site-packages`) fall back
    to the dotted logger name instead of a noisy absolute path.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            rel = Path(record.pathname).relative_to(BASE_DIR)
            record.relative_path = record.name if "site-packages" in rel.parts else str(rel)
        except (ValueError, IndexError):
            record.relative_path = record.name
        return super().format(record)


def _build_config() -> dict:
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "()": "app.core.logging.RelativePathFormatter",
                "format": "{levelname} {asctime}.{msecs:03.0f} {relative_path}:{lineno} - {message}",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "verbose",
                "filename": str(logs_dir / "application.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
        },
        "root": {
            "level": settings.LOG_LEVEL.upper(),
            "handlers": ["console", "file"],
        },
    }


def setup_logging() -> None:
    """Configure logging once per process (console + rotating file at logs/app.log)."""
    global _configured
    if _configured:
        return
    _configured = True

    logging.config.dictConfig(_build_config())
