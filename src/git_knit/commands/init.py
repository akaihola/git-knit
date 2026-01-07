from textwrap import dedent

import click

from ..commands_logic import cmd_init
from ..operations.executor_functions import branch_exists, get_current_branch
from ..errors import KnitError


@click.command()
@click.argument("working-branch")
@click.argument("base-branch")
@click.argument("branches", nargs=-1, required=True)
def init(working_branch: str, base_branch: str, branches: tuple[str, ...]) -> None:
    """Initialize a new knit configuration.

    WORKING_BRANCH: Name for the merged working branch
    BASE_BRANCH: Base branch (e.g., main)
    BRANCHES: Feature branches to include
    """
    try:
        if not branch_exists(base_branch):
            raise click.ClickException(f"Base branch '{base_branch}' does not exist")

        current_branch = get_current_branch()
        if current_branch == working_branch:
            raise click.ClickException(
                f"Cannot initialize knit on current branch '{working_branch}'"
            )

        for branch in branches:
            if not branch_exists(branch):
                raise click.ClickException(f"Feature branch '{branch}' does not exist")

        cmd_init(working_branch, base_branch, list(branches))

        branches_str = ", ".join(branches) if branches else "(no feature branches)"
        click.echo(
            dedent(
                f"""\
                Knit initialized: {working_branch} = {base_branch} + {branches_str}
                """
            )
        )
    except KnitError as e:
        raise click.ClickException(str(e))
