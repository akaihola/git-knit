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

    def test_move_commit_by_message(self, temp_knit_repo, runner, monkeypatch):
        """Test moving a commit by message."""
        (temp_knit_repo / "shared.txt").write_text("original")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "checkout", "b1"], cwd=temp_knit_repo, check=True)
        subprocess.run(["git", "add", "shared.txt"], cwd=temp_knit_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test commit"], cwd=temp_knit_repo, check=True
        )
        subprocess.run(["git", "checkout", "work"], cwd=temp_knit_repo, check=True)
        subprocess.run(["git", "merge", "b1"], cwd=temp_knit_repo, check=True)
        result = runner.invoke(
            cli,
            ["move", "b2", "test commit", "--working-branch", "work"],
        )
        assert result.exit_code == 0
        assert "Successfully moved commit to b2" in result.output

    def test_move_commit_from_other_branch(self, temp_knit_repo, runner, monkeypatch):
        """Test moving when not on working branch."""
        (temp_knit_repo / "new.txt").write_text("content")
        monkeypatch.chdir(temp_knit_repo)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "checkout", "b1"], cwd=temp_knit_repo, check=True)
        subprocess.run(["git", "add", "new.txt"], cwd=temp_knit_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test commit"], cwd=temp_knit_repo, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=temp_knit_repo, check=True)
        result = runner.invoke(
            cli,
            ["move", "b2", "test commit", "--working-branch", "work"],
        )
        assert result.exit_code == 0
        assert "Successfully moved commit to b2" in result.output

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

    def test_move_commit_not_found_by_hash_or_message(
        self, temp_knit_repo, runner, monkeypatch
    ):
        """move reports an error when COMMIT_REF matches neither hash nor message.

        Covers commit.py lines 75-76 (the inner except block when both
        find_commit(message=False) and find_commit(message=True) raise).
        """
        monkeypatch.chdir(temp_knit_repo)
        # Use a ref that is definitely not a hash and not any commit message
        result = runner.invoke(
            cli,
            [
                "move",
                "b1",
                "this-commit-absolutely-does-not-exist-xyz-123",
                "--working-branch",
                "work",
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


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

        monkeypatch.setattr(subprocess, "run", fake_run)
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

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.chdir(temp_knit_repo)
        result = runner.invoke(cli, ["restack", "--working-branch", "work"])
        assert result.exit_code == 1
        assert "git-spice not available" in result.output

    def test_move_commit_lookup_falls_back_to_message(
        self, temp_knit_repo, runner, monkeypatch
    ):
        """move falls back to message-based lookup when hash lookup fails.

        Covers commit.py lines 75-76 (the except+inner try when find_commit by
        hash raises, and message=True lookup succeeds).
        """
        monkeypatch.chdir(temp_knit_repo)
        # Commit something on b1
        (temp_knit_repo / "msg_lookup.txt").write_text("content")
        import subprocess as sp

        sp.run(["git", "checkout", "b1"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "add", "msg_lookup.txt"], cwd=temp_knit_repo, check=True)
        sp.run(
            ["git", "commit", "-m", "unique-message-xyz"],
            cwd=temp_knit_repo,
            check=True,
        )
        sp.run(["git", "checkout", "work"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "merge", "b1"], cwd=temp_knit_repo, check=True)

        # Pass the commit *message* (not hash) as COMMIT_REF so hash lookup fails
        result = runner.invoke(
            cli,
            ["move", "b2", "unique-message-xyz", "--working-branch", "work"],
        )
        assert result.exit_code == 0

    def test_move_restack_when_git_spice_available(
        self, temp_knit_repo, runner, monkeypatch
    ):
        """move calls restack when git-spice is available, printing the echo line.

        Covers commit.py line 88 (the True branch of
        'if detector.restack_if_available():').
        """
        import subprocess as sp

        monkeypatch.chdir(temp_knit_repo)
        (temp_knit_repo / "spice.txt").write_text("content")
        sp.run(["git", "checkout", "b1"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "add", "spice.txt"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "commit", "-m", "spice commit"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "checkout", "work"], cwd=temp_knit_repo, check=True)
        sp.run(["git", "merge", "b1"], cwd=temp_knit_repo, check=True)

        commit_hash = sp.run(
            ["git", "rev-parse", "--short", "b1"],
            cwd=temp_knit_repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Patch GitSpiceDetector.restack_if_available to return True
        from unittest.mock import patch as mock_patch

        with mock_patch(
            "git_knit.operations.spice_detector.GitSpiceDetector.restack_if_available",
            return_value=True,
        ):
            result = runner.invoke(
                cli,
                ["move", "b2", commit_hash, "--working-branch", "work"],
            )

        assert result.exit_code == 0
        assert "restacked" in result.output.lower()
