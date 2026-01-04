from pathlib import Path

import pytest
from click.testing import CliRunner

from git_knit.cli import cli
from git_knit.commands.init import init
from git_knit.commands.add import add
from git_knit.commands.remove import remove, status
from git_knit.errors import BranchNotFoundError


class TestInitCommand:
    """Test git knit init command."""

    def test_init_basic(self, temp_git_repo_with_branches, runner):
        """Test initializing a new knit."""
        repo = temp_git_repo_with_branches["repo"]
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2"],
            cwd=repo,
        )
        assert result.exit_code == 0
        assert "Knit initialized" in result.output

    def test_init_branch_already_exists(self, temp_git_repo_with_branches, runner):
        """Test init when working branch already exists."""
        repo = temp_git_repo_with_branches["repo"]
        runner.invoke(
            cli,
            ["init", "work", "main", "b1"],
            cwd=repo,
            input="y\n",
        )
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1"],
            cwd=repo,
            input="y\n",
        )
        assert result.exit_code == 0


class TestAddCommand:
    """Test git knit add command."""

    def test_add_branch(self, temp_git_repo, runner):
        """Test adding a branch to knit."""
        result = runner.invoke(
            cli,
            ["init", "work", "main"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0

        result = runner.invoke(
            cli, ["add", "b1", "--working-branch", "work"], cwd=temp_git_repo
        )
        assert result.exit_code == 0
        assert "Added b1 to work" in result.output

    def test_add_branch_not_in_knit(self, temp_git_repo, runner):
        """Test adding branch when knit doesn't exist."""
        result = runner.invoke(cli, ["add", "b1"], cwd=temp_git_repo)
        assert result.exit_code == 1


class TestRemoveCommand:
    """Test git knit remove command."""

    def test_remove_branch(self, temp_git_repo, runner):
        """Test removing a branch from knit."""
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0

        result = runner.invoke(
            cli,
            ["remove", "b1", "--working-branch", "work"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0
        assert "Removed b1 from work" in result.output

    def test_remove_last_branch(self, temp_git_repo, runner):
        """Test removing the last branch."""
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0

        result = runner.invoke(
            cli,
            ["remove", "b1", "--working-branch", "work"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0


class TestStatusCommand:
    """Test git knit status command."""

    def test_status(self, temp_git_repo, runner):
        """Test displaying knit status."""
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2", "b3"],
            cwd=temp_git_repo,
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["status"], cwd=temp_git_repo)
        assert result.exit_code == 0
        assert "work" in result.output
        assert "main" in result.output
        assert "b1" in result.output
        assert "b2" in result.output
        assert "b3" in result.output

    def test_status_not_initialized(self, temp_git_repo, runner):
        """Test status when knit is not initialized."""
        result = runner.invoke(cli, ["status"], cwd=temp_git_repo)
        assert result.exit_code == 1
