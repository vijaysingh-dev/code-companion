import logging

import typer

from app.cli.runtime import get_app, run_async
from app.services.user import UserService

logger = logging.getLogger(__name__)

cli = typer.Typer(help="Manage users.")


@cli.command("create")
def create_user(
    user_id: str = typer.Option(..., "--id", "-i", help="Unique handle, e.g. 'alice'."),
    name: str = typer.Option(..., "--name", "-n", help="Display name."),
    email: str | None = typer.Option(None, "--email", "-e", help="Optional, unique."),
) -> None:
    """Create a user with the given handle and print its id."""

    async def _run() -> None:
        async with get_app().sessionmaker() as session:
            user = await UserService(session).create(user_id=user_id, name=name, email=email)
        typer.echo(user.id)

    run_async(_run)


@cli.command("list")
def list_users() -> None:
    """List all users (id, name, email)."""

    async def _run() -> None:
        async with get_app().sessionmaker() as session:
            users = await UserService(session).list_all()
        for user in users:
            typer.echo(f"{user.id}\t{user.name}\t{user.email or '-'}")

    run_async(_run)
