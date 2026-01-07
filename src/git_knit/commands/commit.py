import subprocess
from pathlib import Path
from textwrap import dedent

import click

from ..commands_logic import cmd_move, cmd_rebuild, cmd_restack
from ..errors import KnitError
from ..operations.config_functions import get_config
from ..operations.executor_functions import get_current_branch
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
    try:
        current_branch = get_current_branch()
        if current_branch != working_branch:
            raise click.ClickException(
                f"Must be on working branch '{working_branch}', currently on '{current_branch}'"
            )

        if files:
            for f in files:
                if not Path(f).exists():
                    raise click.ClickException(f"File '{f}' not found")
            subprocess.run(["git", "add", *files], check=True)
        else:
            subprocess.run(["git", "add", "."], check=True)

        subprocess.run(["git", "commit", "-m", message], check=True)

        click.echo("Commits created on source branches:")
        click.echo("Run 'git knit restack' to rebase feature branches")
    except KnitError as e:
        raise click.ClickException(str(e))


@click.command()
@click.argument("target-branch")
@click.argument("commit-ref")
def move(target_branch: str, commit_ref: str) -> None:
    """Move a committed change to a different branch.

    TARGET_BRANCH: Branch to move the commit to
    COMMIT_REF: Commit hash prefix or message substring
    """
    try:
        cmd_move(target_branch, commit_ref)
        click.echo(f"Successfully moved commit to {target_branch}")
    except KnitError as e:
        raise click.ClickException(str(e))


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def rebuild(working_branch: str) -> None:
    """Rebuild working branch from scratch."""
    try:
        cmd_rebuild(working_branch)
        config = get_config(working_branch)

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
    except KnitError as e:
        raise click.ClickException(str(e))


@click.command()
@click.option(
    "-w", "--working-branch", callback=resolve_working_branch_param, is_eager=True
)
def restack(working_branch: str) -> None:
    """Restack feature branches using git-spice."""
    try:
        cmd_restack(working_branch)
        click.echo("Feature branches restacked using git-spice")
    except KnitError as e:
        raise click.ClickException(str(e))
