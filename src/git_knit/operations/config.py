"""Configuration management for git-knit."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from git_knit.errors import BranchNotFoundError, KnitError

if TYPE_CHECKING:
    from git_knit.operations import GitExecutor


class GitExecutor:  # type: ignore[no-redef]
    """Stub for type checking - actual class in operations.py."""


@dataclass(frozen=True, slots=True)
class KnitConfig:
    """Immutable configuration for a working branch."""

    working_branch: str
    base_branch: str
    feature_branches: tuple[str, ...]


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
        feature_branches = tuple(p for p in parts[2:] if p) if len(parts) > 2 else ()

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
