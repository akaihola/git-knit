import click

from ..operations import GitExecutor, KnitConfigManager
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
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    config_manager.remove_branch(working_branch, branch)

    click.echo(f"Removed {branch} from {working_branch}")


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def status(working_branch: str) -> None:
    """Show knit configuration."""
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    config = config_manager.get_config(working_branch)

    branches_str = (
        ", ".join(config.feature_branches) if config.feature_branches else "(none)"
    )
    click.echo(
        f"Working branch: {working_branch}\n"
        f"Base branch: {config.base_branch}\n"
        f"Feature branches: {branches_str}"
    )
