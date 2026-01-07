"""Knit configuration data structure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnitConfig:
    """Immutable configuration for a knit working branch."""

    working_branch: str
    base_branch: str
    feature_branches: list[str]
