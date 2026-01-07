"""Pure functions for managing knit configuration."""

from git_knit.errors import (
    BranchNotFoundError,
    BranchNotInKnitError,
    AlreadyInKnitError,
    WorkingBranchNotSetError,
)
from git_knit.operations.config import KnitConfig
from git_knit.operations.executor_functions import (
    get_current_branch,
    branch_exists,
    get_config_value,
    set_config_value,
    unset_config_value,
    list_config_keys,
)


def _get_section(working_branch: str) -> str:
    """Get the git config section name for a working branch."""
    return f"knit.{working_branch}"


def init_knit(
    working_branch: str,
    base_branch: str,
    feature_branches: list[str],
) -> None:
    """Initialize a new knit configuration."""
    section = _get_section(working_branch)
    set_config_value(section, "base_branch", base_branch)
    for branch in feature_branches:
        set_config_value(section, "feature_branches", branch)


def add_branch(working_branch: str, branch: str) -> None:
    """Add a feature branch to a knit configuration."""
    if not branch_exists(branch):
        raise BranchNotFoundError(f"Branch not found: {branch}")

    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    if branch in config.feature_branches:
        raise AlreadyInKnitError(f"Branch already in knit: {branch}")

    section = _get_section(working_branch)
    set_config_value(section, "feature_branches", branch)


def remove_branch(working_branch: str, branch: str) -> None:
    """Remove a feature branch from a knit configuration."""
    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    if branch not in config.feature_branches:
        raise BranchNotInKnitError(f"Branch not in knit: {branch}")

    # Reconstruct feature_branches without the removed one
    section = _get_section(working_branch)
    unset_config_value(section, "feature_branches")
    for fb in config.feature_branches:
        if fb != branch:
            set_config_value(section, "feature_branches", fb)


def get_config(working_branch: str) -> KnitConfig | None:
    """Retrieve the knit configuration for a working branch."""
    section = _get_section(working_branch)

    base_branch = get_config_value(section, "base_branch")
    if base_branch is None:
        return None

    # Get all feature branches for this working branch
    # Note: git config returns multiple values for the same key
    feature_branches_str = get_config_value(section, "feature_branches")
    if feature_branches_str is None:
        feature_branches_list = []
    else:
        # Parse comma-separated or newline-separated values
        feature_branches_list = [fb.strip() for fb in feature_branches_str.split("\n") if fb.strip()]

    return KnitConfig(
        working_branch=working_branch,
        base_branch=base_branch,
        feature_branches=tuple(feature_branches_list),
    )


def list_working_branches() -> list[str]:
    """List all configured working branches."""
    keys = list_config_keys("knit")
    working_branches = set()
    for key in keys:
        # Keys are like "main-working.base_branch"
        if ".base_branch" in key:
            working_branch = key.replace(".base_branch", "")
            working_branches.add(working_branch)
    return sorted(list(working_branches))


def resolve_working_branch(working_branch: str | None) -> str:
    """Resolve the working branch from explicit argument or current branch."""
    if working_branch:
        config = get_config(working_branch)
        if config is None:
            raise ValueError(f"Working branch not configured: {working_branch}")
        return working_branch

    # Try to infer from current branch
    current_branch = get_current_branch()
    config = get_config(current_branch)
    if config:
        return current_branch

    raise WorkingBranchNotSetError(
        f"Cannot determine working branch. Current branch '{current_branch}' is not a knit. "
        "Use --working-branch to specify."
    )


def delete_config(working_branch: str) -> None:
    """Delete a knit configuration."""
    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    section = _get_section(working_branch)
    unset_config_value(section, "base_branch")
    unset_config_value(section, "feature_branches")
