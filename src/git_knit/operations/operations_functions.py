"""Pure functions for complex git workflows."""

import subprocess

from git_knit.errors import UncommittedChangesError, GitConflictError
from git_knit.operations.executor_functions import (
    is_clean_working_tree,
    stash_push,
    stash_pop,
    create_branch,
    delete_branch,
    checkout,
    merge_branch,
    cherry_pick,
    get_commits_between,
    is_merge_commit,
    is_ancestor,
    run_git_command,
)


def rebuild_working_branch(
    working_branch: str,
    base_branch: str,
    feature_branches: tuple[str, ...] | list[str],
) -> None:
    """
    Rebuild a working branch from scratch while preserving local commits.

    Process:
    1. Verify working tree is clean
    2. Stash uncommitted changes
    3. Create temporary branch from base
    4. Merge feature branches
    5. Cherry-pick local (non-merge, non-feature) commits
    6. Atomically update working branch
    7. Restore stashed changes

    Args:
        working_branch: Name of working branch to rebuild
        base_branch: Base branch to rebuild from
        feature_branches: Tuple or list of feature branches to merge

    Raises:
        UncommittedChangesError: If working tree has uncommitted changes
        GitConflictError: If merge/cherry-pick conflicts occur
    """
    # Step 1: Verify clean working tree
    if not is_clean_working_tree():
        raise UncommittedChangesError("Working tree has uncommitted changes")

    # Step 2: Stash changes (in case there are any despite the check)
    stash_push()

    tmp_branch = f"{working_branch}-tmp"
    try:
        # Step 3: Clean up any leftover tmp branch
        try:
            delete_branch(tmp_branch, force=True)
        except Exception:
            pass  # Doesn't exist

        # Step 3: Create temporary branch from base
        create_branch(tmp_branch, base_branch)
        checkout(tmp_branch)

        # Step 4: Merge feature branches
        for feature in feature_branches:
            try:
                merge_branch(feature)
            except Exception as e:
                # Clean up on conflict
                run_git_command(["merge", "--abort"], check=False)
                raise GitConflictError(f"Conflict merging {feature}: {e}")

        # Step 5: Cherry-pick local commits
        local_commits = get_local_commits(base_branch, feature_branches)
        for commit in local_commits:
            try:
                cherry_pick(commit)
            except Exception as e:
                run_git_command(["cherry-pick", "--abort"], check=False)
                raise GitConflictError(f"Conflict cherry-picking {commit}: {e}")

        # Step 6: Atomically update working branch
        run_git_command(["branch", "-f", working_branch, tmp_branch], check=True)
        checkout(working_branch)

    finally:
        # Cleanup: delete temporary branch
        try:
            delete_branch(tmp_branch, force=True)
        except Exception:
            pass

        # Restore stashed changes
        try:
            stash_pop()
        except Exception:
            pass


def get_local_commits(base_branch: str, feature_branches: tuple[str, ...] | list[str]) -> list[str]:
    """Get commits that are local to working branch (not from base or features)."""
    commits = get_commits_between(base_branch, "HEAD")
    local = []

    for commit in commits:
        # Skip merge commits
        if is_merge_commit(commit):
            continue

        # Skip commits that are in any feature branch
        is_from_feature = False
        for feature in feature_branches:
            if is_ancestor(commit, feature):
                is_from_feature = True
                break

        if not is_from_feature:
            local.append(commit)

    return local


def detect_and_restack() -> None:
    """
    Detect if git-spice is available and restack if it is.

    Silently succeeds if git-spice is not available.
    """
    # Check if 'gs' is available and is git-spice
    result = subprocess.run(
        ["which", "gs"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return  # Not available

    # Verify it's git-spice, not ghostscript
    result = subprocess.run(
        ["gs", "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or "git-spice" not in result.stdout:
        return  # Not git-spice

    # Restack
    run_git_command(["gs", "stack", "restack"], check=True)
