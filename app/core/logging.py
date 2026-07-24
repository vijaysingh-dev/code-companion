import logging
import logging.config
from pathlib import Path

from app.core.config import settings
from app.core.constants import BASE_DIR, AppMode

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


def _build_cli_config() -> dict:
    """CLI logging: plain stderr, no rotating file (a CLI shouldn't write app logs)."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"plain": {"format": "{levelname} {message}", "style": "{"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "plain",
            },
        },
        "root": {"level": settings.LOG_LEVEL.upper(), "handlers": ["console"]},
    }


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


def setup_logging(mode: AppMode = AppMode.APP) -> None:
    """Configure logging once per process. APP: console + rotating file; CLI: plain stderr."""
    global _configured
    if _configured:
        return
    _configured = True

    config = _build_cli_config() if mode is AppMode.CLI else _build_config()
    logging.config.dictConfig(config)
