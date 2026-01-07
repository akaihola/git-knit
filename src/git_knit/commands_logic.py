"""Pure functions for command implementations."""

import click

from git_knit.operations.config_functions import (
    init_knit,
    add_branch,
    remove_branch,
    get_config,
    resolve_working_branch,
)
from git_knit.operations.executor_functions import (
    create_branch,
    checkout,
    merge_branch,
    find_commit,
)
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
)


def cmd_init(
    working_branch: str,
    base_branch: str,
    feature_branches: list[str],
) -> None:
    """Initialize a new knit configuration."""
    create_branch(working_branch, base_branch)
    checkout(working_branch)
    init_knit(working_branch, base_branch, feature_branches)

    for branch in feature_branches:
        merge_branch(branch)


def cmd_add(
    working_branch: str | None,
    branch: str,
) -> None:
    """Add a branch to a knit."""
    wb = resolve_working_branch(working_branch)

    add_branch(wb, branch)

    checkout(wb)
    merge_branch(branch)


def cmd_remove(
    working_branch: str | None,
    branch: str,
) -> None:
    """Remove a branch from a knit and rebuild."""
    wb = resolve_working_branch(working_branch)

    remove_branch(wb, branch)

    # Rebuild after removing - need to get fresh config after removal
    config = get_config(wb)
    assert config is not None, f"Working branch {wb} should be configured"
    rebuild_working_branch(wb, config.base_branch, config.feature_branches)


def cmd_status(
    working_branch: str | None,
) -> None:
    """Display knit configuration."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)
    assert config is not None, f"Working branch {wb} should be configured"

    click.echo(f"Working branch: {config.working_branch}")
    click.echo(f"Base branch: {config.base_branch}")
    click.echo("Feature branches:")
    for branch in config.feature_branches:
        click.echo(f"  - {branch}")


def cmd_move(
    target_branch: str,
    commit_ref: str,
) -> None:
    """Move a commit to a different branch."""
    commit = find_commit(commit_ref)
    assert commit is not None, f"Commit {commit_ref} not found"

    checkout(target_branch)
    merge_branch(commit)

    detect_and_restack()

    # If target is a knit, rebuild it
    config = get_config(target_branch)
    if config:
        rebuild_working_branch(target_branch, config.base_branch, config.feature_branches)


def cmd_rebuild(
    working_branch: str | None,
) -> None:
    """Force rebuild a knit from scratch."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)
    assert config is not None, f"Working branch {wb} should be configured"

    rebuild_working_branch(wb, config.base_branch, config.feature_branches)


def cmd_restack(
    working_branch: str | None,
) -> None:
    """Restack branches using git-spice."""
    resolve_working_branch(working_branch)
    detect_and_restack()
