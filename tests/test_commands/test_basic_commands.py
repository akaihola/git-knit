import subprocess
from pathlib import Path
import tempfile

import click
from click.testing import CliRunner
import pytest

from git_knit.cli import cli
from git_knit.commands.init import init
from git_knit.commands.add import add
from git_knit.commands.remove import remove, status
from git_knit.errors import BranchNotFoundError
from git_knit.operations import GitExecutor, KnitConfigManager


class TestInitCommand:
    """Test git knit init command."""

    def test_init(self, temp_git_repo, runner, monkeypatch):
        """Test init command."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(cli, ["init", "work", "main"])
        assert result.exit_code == 0
        assert "Knit initialized" in result.output
        assert "work = main" in result.output

    def test_init_base_branch_not_found(self, temp_git_repo, runner, monkeypatch):
        """Test init when base branch doesn't exist."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(cli, ["init", "work", "nonexistent"])
        assert result.exit_code == 1
        assert "Base branch 'nonexistent' does not exist" in result.output

    def test_init_on_current_branch(self, temp_git_repo, runner, monkeypatch):
        """Test init when already on the working branch."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(cli, ["init", "main", "main"])
        assert result.exit_code == 1
        assert "Cannot initialize knit on current branch 'main'" in result.output

    def test_init_feature_branch_not_found(self, temp_git_repo, runner, monkeypatch):
        """Test init when feature branch doesn't exist."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(cli, ["init", "work", "main"])
        assert result.exit_code == 0

        subprocess.run(
            ["git", "checkout", "-b", "feature1"], cwd=temp_git_repo, check=True
        )
        (temp_git_repo / "feature1.txt").write_text("feature1 content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature1"], cwd=temp_git_repo, check=True
        )
        subprocess.run(["git", "checkout", "work"], cwd=temp_git_repo, check=True)

        result = runner.invoke(cli, ["add", "feature1", "--working-branch", "work"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["add", "nonexistent", "--working-branch", "work"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_init_resolve_working_branch_param(self, temp_git_repo, monkeypatch):
        """Test init's resolve_working_branch_param function."""
        from git_knit.commands.init import resolve_working_branch_param
        import click

        monkeypatch.chdir(temp_git_repo)

        runner = CliRunner()

        result = runner.invoke(cli, ["init", "work", "main"])
        assert result.exit_code == 0

        ctx = click.Context(click.Command("test"))
        param = click.Option(["--working-branch"])

        with monkeypatch.context() as m:
            m.chdir(temp_git_repo)
            subprocess.run(["git", "checkout", "work"], cwd=temp_git_repo, check=True)

            resolved = resolve_working_branch_param(ctx, param, "work")
            assert resolved == "work"

            resolved = resolve_working_branch_param(ctx, param, None)
            assert resolved == "work"

            subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)
            with pytest.raises(click.ClickException):
                resolve_working_branch_param(ctx, param, "nonexistent")


class TestAddCommand:
    """Test git knit add command."""

    def test_add_branch(self, temp_git_repo, runner, monkeypatch):
        """Test adding a branch to knit."""
        monkeypatch.chdir(temp_git_repo)

        # Create b1 branch first
        subprocess.run(["git", "checkout", "-b", "b1"], check=True)
        (temp_git_repo / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add b1"], check=True)
        subprocess.run(["git", "checkout", "main"], check=True)

        result = runner.invoke(
            cli,
            ["init", "work", "main"],
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["add", "b1", "--working-branch", "work"])
        assert result.exit_code == 0
        assert "Added b1 to work" in result.output

    def test_add_branch_not_in_knit(self, temp_git_repo, runner, monkeypatch):
        """Test adding branch when knit doesn't exist."""
        monkeypatch.chdir(temp_git_repo)
        result = runner.invoke(cli, ["add", "b1"])
        assert result.exit_code == 1

    def test_add_branch_not_exists(self, temp_git_repo, runner, monkeypatch):
        """Test adding a branch that doesn't exist."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(
            cli,
            ["init", "work", "main"],
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["add", "nonexistent", "--working-branch", "work"])
        assert result.exit_code == 1

    def test_init_branch_already_exists(self, temp_git_repo, runner, monkeypatch):
        """Test init when working branch already exists."""
        monkeypatch.chdir(temp_git_repo)

        subprocess.run(
            ["git", "checkout", "-b", "existing"], cwd=temp_git_repo, check=True
        )
        (temp_git_repo / "existing.txt").write_text("existing content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add existing"], cwd=temp_git_repo, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

        result = runner.invoke(cli, ["init", "existing", "main"], input="y\n")
        assert result.exit_code == 0
        assert "existing = main" in result.output

    def test_init_feature_branch_not_exists(self, temp_git_repo, runner, monkeypatch):
        """Test init with non-existent feature branch."""
        monkeypatch.chdir(temp_git_repo)

        result = runner.invoke(
            cli,
            ["init", "work", "main", "nonexistent_feature"],
        )
        assert result.exit_code == 1
        assert "Feature branch 'nonexistent_feature' does not exist" in result.output


class TestRemoveCommand:
    """Test git knit remove command."""

    def test_remove_branch(self, temp_git_repo, runner, monkeypatch):
        """Test removing a branch from knit."""
        monkeypatch.chdir(temp_git_repo)

        # Create b1 and b2 branches
        for branch in ["b1", "b2"]:
            subprocess.run(["git", "checkout", "-b", branch], check=True)
            (temp_git_repo / f"{branch}.txt").write_text("content")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Add {branch}"], check=True)
            subprocess.run(["git", "checkout", "main"], check=True)

        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2"],
        )
        assert result.exit_code == 0

        result = runner.invoke(
            cli,
            ["remove", "b1", "--working-branch", "work"],
        )
        assert result.exit_code == 0
        assert "Removed b1 from work" in result.output

    def test_remove_last_branch(self, temp_git_repo, runner, monkeypatch):
        """Test removing the last branch."""
        monkeypatch.chdir(temp_git_repo)

        # Create b1 branch
        subprocess.run(["git", "checkout", "-b", "b1"], check=True)
        (temp_git_repo / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add b1"], check=True)
        subprocess.run(["git", "checkout", "main"], check=True)

        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1"],
        )
        assert result.exit_code == 0

        result = runner.invoke(
            cli,
            ["remove", "b1", "--working-branch", "work"],
        )
        assert result.exit_code == 0


class TestStatusCommand:
    """Test git knit status command."""

    def test_status(self, temp_git_repo, runner, monkeypatch):
        """Test displaying knit status."""
        monkeypatch.chdir(temp_git_repo)

        # Create b1, b2, b3 branches
        for branch in ["b1", "b2", "b3"]:
            subprocess.run(["git", "checkout", "-b", branch], check=True)
            (temp_git_repo / f"{branch}.txt").write_text("content")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Add {branch}"], check=True)
            subprocess.run(["git", "checkout", "main"], check=True)

        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2", "b3"],
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "work" in result.output
        assert "main" in result.output
        assert "b1" in result.output
        assert "b2" in result.output
        assert "b3" in result.output

    def test_status_not_initialized(self, temp_git_repo, runner, monkeypatch):
        """Test status when knit is not initialized."""
        monkeypatch.chdir(temp_git_repo)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1


class TestSharedFunctions:
    """Test shared utility functions."""

    def test_resolve_working_branch_param_with_value(self, temp_git_repo, monkeypatch):
        """Test resolve_working_branch_param with explicit value."""
        from git_knit.commands._shared import resolve_working_branch_param
        from git_knit.operations import KnitConfigManager

        monkeypatch.chdir(temp_git_repo)
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")

        ctx = click.Context(cli)
        ctx.obj = {"executor": executor, "config_manager": manager}
        param = click.Option(["-w"])

        result = resolve_working_branch_param(ctx, param, "work")
        assert result == "work"

    def test_resolve_working_branch_param_without_value(
        self, temp_git_repo, monkeypatch
    ):
        """Test resolve_working_branch_param without explicit value."""
        from git_knit.commands._shared import resolve_working_branch_param
        from git_knit.operations import KnitConfigManager

        monkeypatch.chdir(temp_git_repo)
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")

        ctx = click.Context(cli)
        ctx.obj = {"executor": executor, "config_manager": manager}
        param = click.Option(["-w"])

        result = resolve_working_branch_param(ctx, param, None)
        assert result == "work"

    def test_resolve_working_branch_param_creates_executor(
        self, temp_git_repo, monkeypatch
    ):
        """Test resolve_working_branch_param creates executor if missing."""
        from git_knit.commands._shared import resolve_working_branch_param

        monkeypatch.chdir(temp_git_repo)
        ctx = click.Context(cli)
        ctx.obj = {}
        param = click.Option(["-w"])

        manager = KnitConfigManager(GitExecutor(cwd=temp_git_repo))
        manager.init_knit("work", "main", ["b1"])

        result = resolve_working_branch_param(ctx, param, "work")
        assert result == "work"
        assert "executor" in ctx.obj
        assert "config_manager" in ctx.obj

    def test_resolve_working_branch_param_creates_config_manager(
        self, temp_git_repo, monkeypatch
    ):
        """Test resolve_working_branch_param creates config_manager if missing."""
        from git_knit.commands._shared import resolve_working_branch_param

        monkeypatch.chdir(temp_git_repo)
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])

        ctx = click.Context(cli)
        ctx.obj = {"executor": executor}
        param = click.Option(["-w"])

        result = resolve_working_branch_param(ctx, param, "work")
        assert result == "work"
        assert "config_manager" in ctx.obj

    def test_resolve_working_branch_param_error(self, temp_git_repo, monkeypatch):
        """Test resolve_working_branch_param raises error on invalid branch."""
        from git_knit.commands._shared import resolve_working_branch_param

        monkeypatch.chdir(temp_git_repo)
        executor = GitExecutor(cwd=temp_git_repo)
        ctx = click.Context(cli)
        ctx.obj = {"executor": executor, "config_manager": KnitConfigManager(executor)}
        param = click.Option(["-w"])

        with pytest.raises(click.ClickException, match="not configured"):
            resolve_working_branch_param(ctx, param, "nonexistent")
