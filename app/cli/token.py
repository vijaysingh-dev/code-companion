import logging

import typer

from app.cli.runtime import get_app, run_async
from app.core.security import create_token
from app.services.user import UserService

logger = logging.getLogger(__name__)

cli = typer.Typer(help="Manage tokens.")


@cli.callback(invoke_without_command=True)
def issue_token(user_id: str = typer.Argument(..., help="User id to sign a token for.")) -> None:
    """Issue a signed access token, after confirming the user id exists."""

    async def _run() -> None:
        async with get_app().sessionmaker() as session:
            user = await UserService(session).get(user_id)
        typer.echo(create_token(user.id))

    run_async(_run)
