"""Pure functions for executing git commands."""

import subprocess
from typing import Optional

from git_knit.errors import (
    GitConflictError,
    BranchNotFoundError,
    CommitNotFoundError,
    AmbiguousCommitError,
)


def run_git_command(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Execute a git command and return the result.

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout/stderr

    Returns:
        CompletedProcess with returncode, stdout, stderr

    Raises:
        GitConflictError: If merge/cherry-pick conflict detected
        RuntimeError: If git command fails and check=True
    """
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
    )

    if check and result.returncode != 0:
        if "CONFLICT" in result.stderr or "conflict" in result.stdout:
            raise GitConflictError(
                f"Conflict during git operation: {' '.join(args)}"
            )
        raise RuntimeError(
            f"Git command failed: {' '.join(args)}\n{result.stderr}"
        )

    return result


def get_current_branch() -> str:
    """Get the name of the currently checked out branch."""
    result = run_git_command(
        ["rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
    )
    return result.stdout.strip()


def branch_exists(branch: str) -> bool:
    """Check if a branch exists."""
    result = run_git_command(
        ["rev-parse", "--verify", branch],
        check=False,
    )
    return result.returncode == 0


def create_branch(branch: str, start_point: Optional[str] = None) -> None:
    """Create a new branch."""
    args = ["branch", branch]
    if start_point:
        args.append(start_point)
    run_git_command(args, check=True)


def checkout(branch: str) -> None:
    """Check out a branch."""
    run_git_command(["checkout", branch], check=True)


def delete_branch(branch: str, force: bool = False) -> None:
    """Delete a branch."""
    flag = "-D" if force else "-d"
    run_git_command(["branch", flag, branch], check=True)


def merge_branch(branch: str) -> subprocess.CompletedProcess:
    """Merge a branch into the current branch."""
    return run_git_command(["merge", "--no-ff", branch], check=True)


def cherry_pick(commit: str) -> subprocess.CompletedProcess:
    """Cherry-pick a commit into the current branch."""
    return run_git_command(["cherry-pick", commit], check=True)


def stash_push() -> None:
    """Stash uncommitted changes."""
    run_git_command(["stash", "push", "-u"], check=True)


def stash_pop() -> None:
    """Pop stashed changes."""
    run_git_command(["stash", "pop"], check=True)


def get_commits_between(base: str, target: str) -> list[str]:
    """Get commits between two refs (base..target)."""
    result = run_git_command(
        ["rev-list", f"{base}..{target}"],
        check=True,
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def get_merge_base(branch1: str, branch2: str) -> str:
    """Get the merge base of two branches."""
    result = run_git_command(
        ["merge-base", branch1, branch2],
        check=True,
    )
    return result.stdout.strip()


def is_ancestor(commit: str, branch: str) -> bool:
    """Check if commit is an ancestor of branch."""
    result = run_git_command(
        ["merge-base", "--is-ancestor", commit, branch],
        check=False,
    )
    return result.returncode == 0


def is_merge_commit(commit: str) -> bool:
    """Check if a commit is a merge commit."""
    result = run_git_command(
        ["cat-file", "-p", commit],
        check=True,
    )
    # Merge commits have 2 parent lines
    parent_count = result.stdout.count("\nparent ")
    return parent_count >= 2


def find_commit(ref: str) -> Optional[str]:
    """Find a commit by hash or message pattern."""
    # First try as a commit hash
    result = run_git_command(
        ["rev-parse", "--verify", f"{ref}^{{commit}}"],
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    # Try as a message pattern
    result = run_git_command(
        ["log", "--all", f"--grep={ref}", "--format=%H"],
        check=True,
    )
    commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    if not commits:
        raise CommitNotFoundError(f"Commit not found: {ref}")
    if len(commits) > 1:
        raise AmbiguousCommitError(f"Multiple commits match: {ref}")

    return commits[0]


def get_local_working_branch_commits(
    base_branch: str,
    feature_branches: list[str],
) -> list[str]:
    """
    Get commits in working branch that are not merge commits or from base/feature branches.
    """
    # Get all commits in working branch that aren't in base
    all_commits = get_commits_between(base_branch, "HEAD")

    # Filter out merge commits and commits from feature branches
    local_commits = []
    for commit in all_commits:
        if is_merge_commit(commit):
            continue

        # Check if commit is in any feature branch
        is_from_feature = False
        for feature in feature_branches:
            if is_ancestor(commit, feature):
                is_from_feature = True
                break

        if not is_from_feature:
            local_commits.append(commit)

    return local_commits


def is_clean_working_tree() -> bool:
    """Check if working tree is clean (no uncommitted changes)."""
    result = run_git_command(
        ["status", "--porcelain"],
        check=True,
    )
    return result.stdout.strip() == ""


def get_config_value(section: str, key: str) -> Optional[str]:
    """Get a git config value."""
    result = run_git_command(
        ["config", "--get", f"{section}.{key}"],
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def set_config_value(section: str, key: str, value: str) -> None:
    """Set a git config value."""
    run_git_command(
        ["config", f"{section}.{key}", value],
        check=True,
    )


def unset_config_value(section: str, key: str) -> None:
    """Unset a git config value."""
    run_git_command(
        ["config", "--unset", f"{section}.{key}"],
        check=True,
    )


def list_config_keys(section: str) -> list[str]:
    """List all keys in a git config section."""
    result = run_git_command(
        ["config", "--get-regexp", f"^{section}\\."],
        check=False,
    )
    if result.returncode != 0:
        return []

    keys = []
    for line in result.stdout.strip().split("\n"):
        if line:
            key = line.split(" ")[0].replace(f"{section}.", "")
            keys.append(key)
    return keys
