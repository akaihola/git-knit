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


# Import and register commands
from .commands.init import init
from .commands.add import add
from .commands.remove import remove, status
from .commands.commit import commit, move, rebuild, restack

cli.add_command(init)
cli.add_command(add)
cli.add_command(remove)
cli.add_command(status)
cli.add_command(commit)
cli.add_command(move)
cli.add_command(rebuild)
cli.add_command(restack)


if __name__ == "__main__":
    cli()
