"""CLI entry point for git-knit."""

import click
from pathlib import Path


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Git-knit: Merged branch workflow tool.

    Work on multiple feature branches simultaneously by merging them
    into a working branch, then route commits back to their sources.
    """
    ctx.ensure_object(dict)


if __name__ == "__main__":
    cli()
