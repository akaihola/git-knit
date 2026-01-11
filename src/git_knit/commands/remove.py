import click

from ..commands_logic import cmd_remove, cmd_status
from ..errors import KnitError
from ._shared import resolve_working_branch_param


@click.command()
@click.argument("branch")
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def remove(branch: str, working_branch: str) -> None:
    """Remove a feature branch from knit.

    BRANCH: Feature branch to remove
    """
    try:
        cmd_remove(working_branch, branch)
        click.echo(f"Removed {branch} from {working_branch}")
    except KnitError as e:
        raise click.ClickException(str(e))


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def status(working_branch: str) -> None:
    """Show knit configuration."""
    try:
        cmd_status(working_branch)
    except KnitError as e:
        raise click.ClickException(str(e))
