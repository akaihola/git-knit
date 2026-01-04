"""Shared utilities for commands."""

import click

from ..operations import GitExecutor, KnitConfigManager
from ..errors import KnitError


def resolve_working_branch_param(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> str:
    """Resolve working branch from flag or current branch."""
    executor = ctx.ensure_object(dict)
    if "executor" not in executor:
        executor["executor"] = GitExecutor()

    if "config_manager" not in executor:
        executor["config_manager"] = KnitConfigManager(executor["executor"])

    try:
        return executor["config_manager"].resolve_working_branch(value)
    except KnitError as e:
        raise click.ClickException(str(e))
