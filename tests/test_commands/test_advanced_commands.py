import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from git_knit.cli import cli
from git_knit.commands.commit import commit, move
from git_knit.errors import UncommittedChangesError
from git_knit.operations import GitExecutor, KnitConfigManager


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_knit_repo(temp_git_repo):
    """Create a temporary repo with a knit configured."""
    executor = GitExecutor(cwd=temp_git_repo)
    manager = KnitConfigManager(executor)
    manager.init_knit("work", "main", ["b1", "b2"])
    executor.create_branch("work", "main")
    executor.checkout("work")
    for branch in ["b1", "b2"]:
        executor.create_branch(branch, "main")
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        executor.checkout(branch)
        executor.run(["add", "."], check=False)
        executor.run(["commit", "-m", f"Add {branch}"], check=False)
    executor.checkout("main")
    executor.checkout("work")
    return temp_git_repo


class TestCommitCommand:
    """Test git knit commit command."""

    def test_commit_all(self, temp_knit_repo, runner):
        """Test committing all staged files."""
        (temp_knit_repo / "test.txt").write_text("test content")
        runner.invoke(cli, ["add", "."], cwd=temp_knit_repo, input="y\n")
        result = runner.invoke(
            cli,
            ["commit", "--all", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test commit\n",
        )
        assert result.exit_code == 0
        assert "Committed to b1" in result.output

    def test_commit_specific_file(self, temp_knit_repo, runner):
        """Test committing a specific file."""
        (temp_knit_repo / "b1.txt").write_text("b1 content")
        (temp_knit_repo / "b2.txt").write_text("b2 content")
        result = runner.invoke(
            cli,
            ["commit", "b1.txt", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test commit\n",
        )
        assert result.exit_code == 0

    def test_commit_uncommitted_changes_error(self, temp_knit_repo, runner):
        """Test commit with uncommitted changes."""
        (temp_knit_repo / "uncommitted.txt").write_text("content")
        runner.invoke(
            cli,
            ["commit", "b1.txt", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test\n",
        )
        result = runner.invoke(
            cli,
            ["commit", "b1.txt", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test\n",
        )
        assert result.exit_code == 2


class TestMoveCommand:
    """Test git knit move command."""

    def test_move_file(self, temp_knit_repo, runner):
        """Test moving a file between branches."""
        (temp_knit_repo / "b1.txt").write_text("original")
        runner.invoke(
            cli,
            ["commit", "b1.txt", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test\n",
        )
        result = runner.invoke(
            cli,
            ["move", "b1.txt", "--source", "b2"],
            cwd=temp_knit_repo,
        )
        assert result.exit_code == 0

    def test_move_file_not_tracked(self, temp_knit_repo, runner):
        """Test moving an untracked file."""
        (temp_knit_repo / "new.txt").write_text("content")
        result = runner.invoke(
            cli,
            ["move", "new.txt", "--source", "b1"],
            cwd=temp_knit_repo,
        )
        assert result.exit_code == 1


class TestRebuildCommand:
    """Test git knit rebuild command."""

    def test_rebuild(self, temp_knit_repo, runner):
        """Test rebuilding a working branch."""
        (temp_knit_repo / "test.txt").write_text("test")
        runner.invoke(
            cli,
            ["commit", "test.txt", "--all", "--source", "b1"],
            cwd=temp_knit_repo,
            input="test\n",
        )
        result = runner.invoke(cli, ["rebuild"], cwd=temp_knit_repo)
        assert result.exit_code == 0
        assert "Rebuilt work" in result.output


class TestRestackCommand:
    """Test git knit restack command."""

    def test_restack_with_git_spice(self, temp_knit_repo, runner, monkeypatch):
        """Test restack when git-spice is available."""
        monkeypatch.setenv("PATH", "/fake/bin:/fake/usr/bin")

        class FakeProcess:
            stdout = "git-spice"
            returncode = 0

        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return FakeProcess()
            if args[0] == ["gs", "stack", "restack"]:
                return FakeProcess()
            return original_run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        result = runner.invoke(cli, ["restack"], cwd=temp_knit_repo)
        assert result.exit_code == 0
        assert "Restacked" in result.output

    def test_restack_not_available(self, temp_knit_repo, runner, monkeypatch):
        """Test restack when git-spice is not available."""
        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return original_run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        result = runner.invoke(cli, ["restack"], cwd=temp_knit_repo)
        assert result.exit_code == 1
        assert "git-spice not available" in result.output
