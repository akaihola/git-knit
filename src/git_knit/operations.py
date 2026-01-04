"""Core operations for git-knit."""

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


@dataclass(frozen=True, slots=True)
class KnitConfig:
    """Immutable configuration for a working branch."""

    working_branch: str
    base_branch: str
    feature_branches: tuple[str, ...]


class GitExecutor:
    """Execute git commands with proper error handling."""

    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd

    def run(
        self,
        args: list[str],
        check: bool = True,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        """Run a git command safely."""
        cmd = ["git"] + args

        if capture:
            result = subprocess.run(
                cmd,
                cwd=self.cwd,
                check=check,
                capture_output=True,
                text=True,
            )
            return result
        else:
            subprocess.run(cmd, cwd=self.cwd, check=check)
            return None

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
            raise GitConflictError(f"Merge conflict with branch '{branch}'")

    def cherry_pick(self, commit: str) -> None:
        """Cherry-pick a commit."""
        result = self.run(
            ["cherry-pick", commit],
            check=False,
            capture=True,
        )

        if result.returncode != 0:
            self.run(["cherry-pick", "--abort"], check=False)
            raise GitConflictError(f"Cherry-pick conflict for commit '{commit}'")

    def find_commit(self, ref: str, message: bool = False) -> str:
        """Find commit hash by reference or message substring."""
        if not message:
            result = self.run(["rev-parse", ref], capture=True)
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
            raise KnitError(f"Config not found: {key}")

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
            ["config", "--get-regexp", prefix],
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
        """Get the parent branch of a merge commit."""
        result = self.run(
            ["log", f"{branch}", "--format=%P", "-n", "1"],
            capture=True,
        )
        parents = result.stdout.strip().split()
        return parents[1] if len(parents) > 1 else None


class GitSpiceDetector:
    """Detect if git-spice is available (not GhostScript)."""

    def detect(self) -> Literal["git-spice", "ghostscript", "not-found", "unknown"]:
        """Detect gs binary type."""
        result = subprocess.run(
            ["gs", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return "not-found"

        output = result.stdout
        error = result.stderr

        full_output = output + error

        if "git-spice" in full_output.lower():
            return "git-spice"
        elif "ghostscript" in full_output.lower():
            return "ghostscript"
        else:
            return "unknown"

    def restack_if_available(self) -> bool:
        """Run gs stack restack if git-spice is available."""
        spice_type = self.detect()

        if spice_type != "git-spice":
            return False

        subprocess.run(["gs", "stack", "restack"], check=True)
        return True


class KnitConfigManager:
    """Manage knit metadata in git config."""

    CONFIG_PREFIX = "knit."

    def __init__(self, executor: GitExecutor):
        self.executor = executor

    def _get_config_key(self, working_branch: str) -> str:
        """Get the config key for a working branch."""
        return f"{self.CONFIG_PREFIX}{working_branch}"

    def _parse_config(self, value: str) -> KnitConfig:
        """Parse config value into KnitConfig."""
        parts = value.split(":")

        if len(parts) < 2:
            raise KnitError(f"Invalid config format: {value}")

        working_branch = parts[0]
        base_branch = parts[1]
        feature_branches = tuple(parts[2:]) if len(parts) > 2 else ()

        return KnitConfig(
            working_branch=working_branch,
            base_branch=base_branch,
            feature_branches=feature_branches,
        )

    def _serialize_config(self, config: KnitConfig) -> str:
        """Serialize KnitConfig to string."""
        parts = [config.working_branch, config.base_branch]
        parts.extend(config.feature_branches)
        return ":".join(parts)

    def init_knit(
        self,
        working_branch: str,
        base_branch: str,
        feature_branches: list[str],
    ) -> None:
        """Initialize a new knit configuration."""
        config = KnitConfig(
            working_branch=working_branch,
            base_branch=base_branch,
            feature_branches=tuple(feature_branches),
        )

        key = self._get_config_key(working_branch)
        value = self._serialize_config(config)

        self.executor.set_config(key, value)

    def add_branch(self, working_branch: str, branch: str) -> None:
        """Add a feature branch to knit."""
        config = self.get_config(working_branch)

        if branch in config.feature_branches:
            raise KnitError(f"Branch '{branch}' is already in the knit")

        new_config = KnitConfig(
            working_branch=config.working_branch,
            base_branch=config.base_branch,
            feature_branches=config.feature_branches + (branch,),
        )

        key = self._get_config_key(working_branch)
        value = self._serialize_config(new_config)

        self.executor.set_config(key, value)

    def remove_branch(self, working_branch: str, branch: str) -> None:
        """Remove a feature branch from knit."""
        config = self.get_config(working_branch)

        if branch not in config.feature_branches:
            raise BranchNotFoundError(f"Branch '{branch}' is not in the knit")

        new_config = KnitConfig(
            working_branch=config.working_branch,
            base_branch=config.base_branch,
            feature_branches=tuple(b for b in config.feature_branches if b != branch),
        )

        key = self._get_config_key(working_branch)
        value = self._serialize_config(new_config)

        self.executor.set_config(key, value)

    def get_config(self, working_branch: str) -> KnitConfig:
        """Get configuration for a working branch."""
        key = self._get_config_key(working_branch)

        try:
            value = self.executor.get_config(key)
        except KnitError:
            raise KnitError(f"No knit configured for '{working_branch}'")

        return self._parse_config(value)

    def list_working_branches(self) -> list[str]:
        """List all configured working branches."""
        keys = self.executor.list_config_keys(self.CONFIG_PREFIX)
        branches = []

        for key in keys:
            branch = key[len(self.CONFIG_PREFIX) :]
            branches.append(branch)

        return branches

    def is_initialized(self) -> bool:
        """Check if any knit is configured."""
        branches = self.list_working_branches()
        return len(branches) > 0

    def resolve_working_branch(self, explicit: str | None = None) -> str:
        """Resolve working branch from context or explicit flag."""
        if explicit:
            if explicit not in self.list_working_branches():
                raise KnitError(f"Working branch '{explicit}' is not configured")
            return explicit

        current = self.executor.get_current_branch()

        if current in self.list_working_branches():
            return current

        branches = self.list_working_branches()

        if len(branches) == 1:
            return branches[0]

        raise KnitError(
            "Cannot determine working branch. "
            "Use --working-branch flag or checkout a working branch."
        )

    def delete_config(self, working_branch: str) -> None:
        """Delete knit configuration for a working branch."""
        key = self._get_config_key(working_branch)
        self.executor.unset_config(key)


class KnitRebuilder:
    """Rebuild working branches from scratch."""

    def __init__(self, executor: GitExecutor):
        self.executor = executor

    def rebuild(self, config: KnitConfig, checkout: bool = True) -> None:
        """Rebuild working branch by deleting and recreating it."""
        current = self.executor.get_current_branch()
        was_on_working = current == config.working_branch

        self.executor.ensure_clean_working_tree()

        if self.executor.branch_exists(config.working_branch):
            self.executor.delete_branch(config.working_branch, force=True)

        self.executor.create_branch(
            config.working_branch,
            config.base_branch,
        )

        if checkout or was_on_working:
            self.executor.checkout(config.working_branch)

        for branch in config.feature_branches:
            if not self.executor.branch_exists(branch):
                raise BranchNotFoundError(f"Feature branch '{branch}' does not exist")

            self.executor.merge_branch(branch)
