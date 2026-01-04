import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from git_knit.cli import cli
from git_knit.commands.commit import commit, move
from git_knit.errors import UncommittedChangesError
from git_knit.operations import GitExecutor, KnitConfigManager


class TestCommitCommand:
    """Test git knit commit command."""

    def test_commit_all(self, temp_knit_repo, runner, monkeypatch):
        """Test committing all staged files."""
        (temp_knit_repo / "test.txt").write_text("test content")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        result = runner.invoke(
            cli,
            ["commit", "-m", "test commit", "--working-branch", "work"],
        )
        assert result.exit_code == 0
        assert "Commits created on source branches" in result.output

    def test_commit_specific_file(self, temp_knit_repo, runner, monkeypatch):
        """Test committing a specific file."""
        (temp_knit_repo / "b1.txt").write_text("b1 content")
        (temp_knit_repo / "b2.txt").write_text("b2 content")
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(
            cli,
            ["commit", "-m", "test commit", "b1.txt", "--working-branch", "work"],
        )
        assert result.exit_code == 0

    def test_commit_uncommitted_changes_error(
        self, temp_knit_repo, runner, monkeypatch
    ):
        """Test commit with uncommitted changes."""
        (temp_knit_repo / "uncommitted.txt").write_text("content")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "test"], check=True)
        result = runner.invoke(
            cli,
            ["commit", "-m", "test", "b1.txt", "--working-branch", "work"],
        )
        assert result.exit_code == 1

    def test_commit_wrong_branch(self, temp_knit_repo, runner, monkeypatch):
        """Test commit when not on working branch."""
        (temp_knit_repo / "b1.txt").write_text("content")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "checkout", "main"], check=True)
        result = runner.invoke(
            cli,
            ["commit", "-m", "test", "b1.txt", "--working-branch", "work"],
        )
        assert result.exit_code == 1


class TestMoveCommand:
    """Test git knit move command."""

    def test_move_file(self, temp_knit_repo, runner, monkeypatch):
        """Test moving a file between branches."""
        (temp_knit_repo / "b1.txt").write_text("original")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        runner.invoke(
            cli,
            ["commit", "-m", "test", "--working-branch", "work"],
        )
        result = runner.invoke(
            cli,
            ["move", "b1.txt", "b2", "--working-branch", "work"],
        )
        assert result.exit_code == 0

    def test_move_file_not_tracked(self, temp_knit_repo, runner, monkeypatch):
        """Test moving an untracked file."""
        (temp_knit_repo / "new.txt").write_text("content")
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(
            cli,
            ["move", "new.txt", "b1", "--working-branch", "work"],
        )
        assert result.exit_code == 0

    def test_move_file_not_found(self, temp_knit_repo, runner, monkeypatch):
        """Test moving a file that doesn't exist."""
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(
            cli,
            ["move", "nonexistent.txt", "b1", "--working-branch", "work"],
        )
        assert result.exit_code == 1

    def test_move_branch_not_found(self, temp_knit_repo, runner, monkeypatch):
        """Test moving a file to a branch that doesn't exist."""
        (temp_knit_repo / "file.txt").write_text("content")
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(
            cli,
            ["move", "file.txt", "nonexistent", "--working-branch", "work"],
        )
        assert result.exit_code == 1


class TestRebuildCommand:
    """Test git knit rebuild command."""

    def test_rebuild(self, temp_knit_repo, runner, monkeypatch):
        """Test rebuilding a working branch."""
        (temp_knit_repo / "test.txt").write_text("test")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        runner.invoke(
            cli,
            ["commit", "-m", "test", "--working-branch", "work"],
        )
        result = runner.invoke(cli, ["rebuild", "--working-branch", "work"])
        assert result.exit_code == 0
        assert "Rebuilt work" in result.output


class TestRestackCommand:
    """Test git knit restack command."""

    def test_restack_with_git_spice(self, temp_knit_repo, runner, monkeypatch):
        """Test restack when git-spice is available."""

        class FakeProcess:
            stdout = "git-spice"
            stderr = ""
            returncode = 0

        original_run = subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if cmd == ["gs", "--help"]:
                return FakeProcess()
            if cmd == ["gs", "stack", "restack"]:
                return FakeProcess()
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(cli, ["restack", "--working-branch", "work"])
        assert result.exit_code == 0
        assert "restacked" in result.output.lower()

    def test_restack_not_available(self, temp_knit_repo, runner, monkeypatch):
        """Test restack when git-spice is not available."""
        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return original_run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(cli, ["restack", "--working-branch", "work"])
        assert result.exit_code == 1
        assert "git-spice not available" in result.output
