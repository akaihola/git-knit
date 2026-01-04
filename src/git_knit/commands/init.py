from textwrap import dedent

import click

from ..operations import GitExecutor, KnitConfigManager


@click.command()
@click.argument("working-branch")
@click.argument("base-branch")
@click.argument("branches", nargs=-1)
def init(working_branch: str, base_branch: str, branches: tuple[str, ...]) -> None:
    """Initialize a new knit configuration.

    WORKING_BRANCH: Name for the merged working branch
    BASE_BRANCH: Base branch (e.g., main)
    BRANCHES: Feature branches to include
    """
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)

    if not executor.branch_exists(base_branch):
        raise click.ClickException(f"Base branch '{base_branch}' does not exist")

    current_branch = executor.get_current_branch()
    if current_branch == working_branch:
        raise click.ClickException(
            f"Cannot initialize knit on current branch '{working_branch}'"
        )

    if not executor.branch_exists(working_branch):
        executor.create_branch(working_branch, base_branch)
    else:
        click.confirm(
            f"Branch '{working_branch}' already exists. Use it as working branch?",
            abort=True,
        )

    config_manager.init_knit(working_branch, base_branch, list(branches))

    executor.checkout(working_branch)
    for branch in branches:
        if not executor.branch_exists(branch):
            raise click.ClickException(f"Feature branch '{branch}' does not exist")
        click.echo(f"Merging {branch} into {working_branch}...")
        executor.merge_branch(branch)

    branches_str = ", ".join(branches) if branches else "(no feature branches)"
    click.echo(
        dedent(
            f"""\
            Knit initialized: {working_branch} = {base_branch} + {branches_str}
            """
        )
    )


def resolve_working_branch_param(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> str:
    """Resolve working branch from flag or current branch."""
    from ..operations import GitExecutor, KnitConfigManager
    from ..errors import KnitError

    executor = ctx.ensure_object(dict)
    if "executor" not in executor:
        executor["executor"] = GitExecutor()

    if "config_manager" not in executor:
        executor["config_manager"] = KnitConfigManager(executor["executor"])

    try:
        return executor["config_manager"].resolve_working_branch(value)
    except KnitError as e:
        raise click.ClickException(str(e))
