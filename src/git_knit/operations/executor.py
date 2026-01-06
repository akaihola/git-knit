"""Core operations for git-knit."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from git_knit.errors import (
    AmbiguousCommitError,
    BranchNotFoundError,
    GitConflictError,
    KnitError,
    UncommittedChangesError,
)
from git_knit.operations.config import KnitConfig, KnitConfigManager


class GitExecutor:
    """Execute git commands with proper error handling."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd

    def run(
        self,
        args: list[str],
        check: bool = True,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command safely and always return a CompletedProcess."""
        cmd = ["git"] + args
        result = subprocess.run(
            cmd,
            cwd=self.cwd,
            check=check,
            capture_output=capture,
            text=True,
        )
        return result

    def get_current_branch(self) -> str:
        """Get current branch name."""
        result = self.run(["rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        return result.stdout.strip()

    def is_clean_working_tree(self) -> bool:
        """Check if working tree has uncommitted changes."""
        result = self.run(["status", "--porcelain"], capture=True, check=False)
        return result.returncode == 0 and not result.stdout.strip()

    def ensure_clean_working_tree(self) -> None:
        """Ensure working tree is clean."""
        if not self.is_clean_working_tree():
            raise UncommittedChangesError("Working tree has uncommitted changes")

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists."""
        result = self.run(
            ["rev-parse", "--verify", f"refs/heads/{branch}"],
            check=False,
            capture=True,
        )
        return result.returncode == 0

    def create_branch(self, branch: str, start_point: str) -> None:
        """Create a new branch."""
        self.run(["branch", branch, start_point])

    def checkout(self, branch: str) -> None:
        """Checkout a branch."""
        self.run(["checkout", branch])

    def merge_branch(self, branch: str) -> None:
        """Merge a branch into current HEAD."""
        result = self.run(
            ["merge", "--no-ff", "--no-edit", branch],
            check=False,
            capture=True,
        )

        if result.returncode != 0:
            self.run(["merge", "--abort"], check=False)
            err = (result.stderr or result.stdout or "").strip()
            raise GitConflictError(f"Merge conflict with branch '{branch}': {err}")

    def cherry_pick(self, commit: str) -> None:
        """Cherry-pick a commit, leaving conflict state on failure for manual resolution."""
        result = self.run(
            ["cherry-pick", commit],
            check=False,
            capture=True,
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise GitConflictError(f"Cherry-pick conflict for commit '{commit}': {err}")

    def find_commit(self, ref: str, message: bool = False) -> str:
        """Find commit hash by reference or message substring."""
        if not message:
            result = self.run(["rev-parse", ref], capture=True, check=False)
            if result.returncode != 0 or not result.stdout.strip():
                raise KnitError(f"Commit not found: {ref}")
            return result.stdout.strip()

        result = self.run(
            ["log", "--all", "--grep", ref, "--format=%H", "-n", "2"],
            capture=True,
        )
        commits = result.stdout.strip().split("\n")

        if not commits or not commits[0]:
            raise KnitError(f"Commit not found: {ref}")

        if len(commits) > 1 and commits[1]:
            raise AmbiguousCommitError(f"Multiple commits match message '{ref}'")

        return commits[0]

    def delete_branch(self, branch: str, force: bool = False) -> None:
        """Delete a branch."""
        args = ["branch", "-D" if force else "-d", branch]
        self.run(args)

    def get_config(self, key: str) -> str:
        """Get a git config value."""
        result = self.run(["config", "--get", key], capture=True, check=False)

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "unknown error"
            raise KnitError(f"Config not found: {key} - {error_msg}")

        return result.stdout.strip()

    def set_config(self, key: str, value: str) -> None:
        """Set a git config value."""
        self.run(["config", key, value])

    def unset_config(self, key: str) -> None:
        """Unset a git config value."""
        self.run(["config", "--unset", key], check=False)

    def list_config_keys(self, prefix: str) -> list[str]:
        """List all config keys with a given prefix."""
        result = self.run(
            ["config", "--get-regexp", f"^{re.escape(prefix)}"],
            capture=True,
            check=False,
        )

        if result.returncode != 0:
            return []

        keys = []
        for line in result.stdout.strip().split("\n"):
            if line:
                key = line.split()[0]
                keys.append(key)

        return keys

    def get_branch_parent(self, branch: str) -> str | None:
        """Get the parent branch of a merge commit.

        Returns the branch name if found via name-rev, or the full SHA if
        name-rev fails. Returns None if not a merge commit (no parents).
        """
        result = self.run(
            ["log", f"{branch}", "--format=%P", "-n", "1"],
            capture=True,
        )
        parents = result.stdout.strip().split()
        if len(parents) < 2:
            return None
        result = self.run(
            ["name-rev", "--name-only", "--exclude=tags/*", parents[1]],
            capture=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return parents[1]

    def stash_push(self, message: str | None = None) -> bool:
        """Stash both staged and unstaged changes. Returns True if stash created."""
        if self.is_clean_working_tree():
            return False
        args = ["stash", "push", "--include-untracked"]
        if message:
            args += ["-m", message]
        result = self.run(args, capture=True, check=False)
        if result is None:
            return False
        out = (result.stdout or "").lower()
        if "no local changes" in out:
            return False
        return True

    def stash_pop(self) -> None:
        """Pop the most recent stash, trying to restore index when possible."""
        result = self.run(["stash", "pop", "--index"], check=False, capture=True)
        if result and result.returncode == 0:
            return
        result2 = self.run(["stash", "pop"], check=False, capture=True)
        if result2 and result2.returncode != 0:
            raise KnitError("Failed to pop stash")

    def get_commits_between(self, base: str, tip: str) -> list[str]:
        """Get commits that are on tip but not on base, in chronological order."""
        result = self.run(
            ["log", f"{base}..{tip}", "--format=%H", "--reverse"], capture=True
        )
        if not result.stdout.strip():
            return []
        return result.stdout.strip().split("\n")

    def get_local_working_branch_commits(
        self,
        working_branch: str,
        base_branch: str,
        feature_branches: tuple[str, ...],
    ) -> list[str]:
        """Get commits on working branch that aren't from feature branches.

        Uses rev-list with --not to deterministically exclude feature branch commits.
        """
        args = [
            "rev-list",
            "--reverse",
            "--no-merges",
            f"{base_branch}..{working_branch}",
        ]
        if feature_branches:
            args += ["--not"] + list(feature_branches)
        result = self.run(args, capture=True, check=False)
        if not result or result.returncode != 0:
            return []
        return [c for c in (result.stdout or "").splitlines() if c]

    def get_merge_base(self, ref1: str, ref2: str) -> str | None:
        result = self.run(["merge-base", ref1, ref2], capture=True, check=False)
        if not result or result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = self.run(
            ["merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
            capture=True,
        )
        return result.returncode == 0 if result else False

    def is_merge_commit(self, commit: str) -> bool:
        """Check if a commit is a merge commit by counting parents."""
        result = self.run(
            ["rev-list", "--parents", "-n", "1", commit], capture=True, check=False
        )
        if not result or result.returncode != 0 or not result.stdout:
            return False
        parts = result.stdout.strip().split()
        return len(parts) > 2

