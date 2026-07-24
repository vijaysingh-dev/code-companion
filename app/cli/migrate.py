import logging

import typer
from alembic import command
from alembic.config import Config

from app.core.constants import BASE_DIR

logger = logging.getLogger(__name__)

cli = typer.Typer(invoke_without_command=True)


def alembic_config() -> Config:
    """Alembic config rooted at the repo's alembic.ini (url comes from settings in env.py)."""
    return Config(str(BASE_DIR / "alembic.ini"))


@cli.callback()
def migrate() -> None:
    """Apply all pending database migrations (alembic upgrade head)."""
    logger.info("Applying migrations")
    command.upgrade(alembic_config(), "head")
    typer.echo("Migrations applied.")
