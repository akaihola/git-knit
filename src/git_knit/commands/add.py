import click

from ..commands_logic import cmd_add
from ..operations.executor_functions import branch_exists
from ..errors import KnitError
from ._shared import resolve_working_branch_param


@click.command()
@click.argument("branch")
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def add(branch: str, working_branch: str) -> None:
    """Add a feature branch to knit.

    BRANCH: Feature branch to add
    """
    try:
        if not branch_exists(branch):
            raise click.ClickException(f"Branch '{branch}' does not exist")

        cmd_add(working_branch, branch)
        click.echo(f"Added {branch} to {working_branch}")
    except KnitError as e:
        raise click.ClickException(str(e))
