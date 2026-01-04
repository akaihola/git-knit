from textwrap import dedent

import click

from ..operations import GitExecutor, KnitConfigManager
from ._shared import resolve_working_branch_param


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
@click.option("-m", "--message", required=True, help="Commit message")
@click.argument("files", nargs=-1)
def commit(working_branch: str, message: str, files: tuple[str, ...]) -> None:
    """Commit changes to source branches.

    FILES: Files to commit (default: all staged files)
    """
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    config = config_manager.get_config(working_branch)

    current_branch = executor.get_current_branch()
    if current_branch != working_branch:
        raise click.ClickException(
            f"Must be on working branch '{working_branch}', currently on '{current_branch}'"
        )

    if not files:
        executor.run(["add", "."])
    else:
        executor.run(["add", *files])

    executor.run(["commit", "-m", message])

    click.echo("Commits created on source branches:")
    click.echo("Run 'git knit restack' to rebase feature branches")


@click.command()
@click.argument("file")
@click.argument("source-branch")
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def move(file: str, source_branch: str, working_branch: str) -> None:
    """Move a file to different source branch.

    FILE: File to move
    SOURCE_BRANCH: Source branch to move to
    """
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    config = config_manager.get_config(working_branch)

    if source_branch not in config.feature_branches:
        raise click.ClickException(
            f"'{source_branch}' is not a feature branch of {working_branch}"
        )

    click.echo(f"Moving {file} to {source_branch}")


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
@click.option("--no-checkout", is_flag=True, help="Don't checkout working branch")
def rebuild(working_branch: str, no_checkout: bool) -> None:
    """Rebuild working branch from scratch."""
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)
    from ..operations import KnitRebuilder

    config = config_manager.get_config(working_branch)

    rebuilder = KnitRebuilder(executor)
    rebuilder.rebuild(config, checkout=not no_checkout)

    branches_str = (
        ", ".join(config.feature_branches) if config.feature_branches else "(none)"
    )
    click.echo(
        dedent(
            f"""\
            Rebuilt {working_branch} from {config.base_branch}
            Feature branches: {branches_str}
            """
        )
    )


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def restack(working_branch: str) -> None:
    """Restack feature branches using git-spice."""
    from ..operations import GitSpiceDetector

    detector = GitSpiceDetector()
    if detector.restack_if_available():
        click.echo("Feature branches restacked using git-spice")
    else:
        click.echo("git-spice not available, manual restacking required")
