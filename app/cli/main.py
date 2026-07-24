import typer

from app.cli.migrate import cli as migrate_cli
from app.cli.token import cli as token_cli
from app.cli.user import cli as user_cli
from app.core.constants import AppMode
from app.core.logging import setup_logging

cli = typer.Typer(help="Code Companion admin CLI.")

cli.add_typer(migrate_cli, name="migrate")
cli.add_typer(user_cli, name="user")
cli.add_typer(token_cli, name="token")


@cli.callback()
def _main() -> None:
    setup_logging(AppMode.CLI)


if __name__ == "__main__":
    cli()
