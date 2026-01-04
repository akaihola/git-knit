import subprocess
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

    def test_init_basic(self, temp_git_repo_with_branches, runner, monkeypatch):
        """Test initializing a new knit."""
        repo = temp_git_repo_with_branches["repo"]
        monkeypatch.chdir(repo)
        result = runner.invoke(
            cli,
            ["init", "work", "main", "b1", "b2"],
        )
        assert result.exit_code == 0
        assert "Knit initialized" in result.output

    def test_init_branch_already_exists(self, temp_git_repo, runner, monkeypatch):
        """Test init when working branch already exists."""
        monkeypatch.chdir(temp_git_repo)
        result = runner.invoke(
            cli,
            ["init", "work", "main"],
            input="y\n",
        )
        assert result.exit_code == 0

        # Checkout main branch before trying to init again
        subprocess.run(["git", "checkout", "main"], check=True)
        result = runner.invoke(
            cli,
            ["init", "work", "main"],
            input="y\n",
        )
        assert result.exit_code == 0


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
