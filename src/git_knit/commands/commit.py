from textwrap import dedent
from pathlib import Path

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

    if files:
        for f in files:
            if not Path(f).exists():
                raise click.ClickException(f"File '{f}' not found")
        executor.run(["add", *files])
    else:
        executor.run(["add", "."])

    executor.run(["commit", "-m", message])

    click.echo("Commits created on source branches:")
    click.echo("Run 'git knit restack' to rebase feature branches")


@click.command()
@click.argument("target-branch")
@click.argument("commit-ref")
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def move(target_branch: str, commit_ref: str, working_branch: str) -> None:
    """Move a committed change to a different branch.

    TARGET_BRANCH: Branch to move the commit to
    COMMIT_REF: Commit hash prefix or message substring
    """
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    config = config_manager.get_config(working_branch)

    if target_branch not in config.feature_branches:
        raise click.ClickException(
            f"'{target_branch}' is not a feature branch of {working_branch}"
        )

    executor.ensure_clean_working_tree()

    try:
        commit_hash = executor.find_commit(commit_ref, message=False)
    except Exception:
        try:
            commit_hash = executor.find_commit(commit_ref, message=True)
        except Exception:
            raise click.ClickException(f"Commit not found: {commit_ref}")

    current_branch = executor.get_current_branch()

    click.echo(f"Moving commit {commit_hash[:7]} to {target_branch}...")
    executor.checkout(target_branch)
    executor.cherry_pick(commit_hash)

    from ..operations import GitSpiceDetector

    detector = GitSpiceDetector()
    if detector.restack_if_available():
        click.echo("Feature branches restacked using git-spice")

    from ..operations import KnitRebuilder

    rebuilder = KnitRebuilder(executor)
    rebuilder.rebuild(config)

    if executor.branch_exists(current_branch):
        executor.checkout(current_branch)

    click.echo(f"Successfully moved commit to {target_branch}")


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
            f"""            Rebuilt {working_branch} from {config.base_branch}
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
        raise click.ClickException(
            "git-spice not available, manual restacking required"
        )
