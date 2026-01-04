import click

from ..operations import GitExecutor, KnitConfigManager
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
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    if not executor.branch_exists(branch):
        raise click.ClickException(f"Branch '{branch}' does not exist")

    config_manager.add_branch(working_branch, branch)

    executor.checkout(working_branch)
    click.echo(f"Merging {branch} into {working_branch}...")
    executor.merge_branch(branch)

    click.echo(f"Added {branch} to {working_branch}")
