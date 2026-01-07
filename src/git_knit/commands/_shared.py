"""Shared utilities for commands."""

import click

from ..operations.config_functions import resolve_working_branch
from ..errors import KnitError


def resolve_working_branch_param(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> str:
    """Resolve working branch from flag or current branch."""
    try:
        return resolve_working_branch(value)
    except KnitError as e:
        raise click.ClickException(str(e))
