"""Tests for remaining coverage gaps."""

from pytest_check import check
from click.testing import CliRunner
from shlex import split

from git_knit.cli import cli
from git_knit.commands_logic import cmd_move, cmd_rebuild, cmd_restack


class TestMoveCommand:
    """Test move command logic."""

    def test_cmd_move_updates_non_knit_target(self, fake_process):
        """Test move command when target is not a knit"""
        # Find commit
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "abc123^{commit}"],
            stdout="abc123\n"
        )
        # Checkout target
        fake_process.register_subprocess(
            ["git", "checkout", "target"],
            stdout=""
        )
        # Merge commit
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "abc123"],
            stdout="Merged\n"
        )
        # Detect and restack - which gs not found
        fake_process.register_subprocess(
            "which gs",
            returncode=1,
            stderr="gs: not found\n"
        )
        # Check if target is a knit
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.target.base-branch"],
            returncode=1,
            stdout=""
        )
        cmd_move("target", "abc123")

    def test_cmd_move_rebuilds_knit_target(self, fake_process):
        """Test move command when target is a knit"""
        # Find commit
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "abc123^{commit}"],
            stdout="abc123\n"
        )
        # Checkout target
        fake_process.register_subprocess(
            ["git", "checkout", "target"],
            stdout=""
        )
        # Merge commit
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "abc123"],
            stdout="Merged\n"
        )
        # Detect and restack - which gs not found
        fake_process.register_subprocess(
            "which gs",
            returncode=1,
            stderr="gs: not found\n"
        )
        # Check if target is a knit - it is
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.target.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.target.feature-branches"],
            stdout="feature/a\n"
        )
        # Rebuild the knit
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "target-tmp"],
            returncode=1,
            stderr="not found\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "target-tmp", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "target-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "feature/a"],
            stdout="Merged\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-f", "target", "target-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "target"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "target-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            stdout=""
        )
        cmd_move("target", "abc123")


class TestRebuildCommand:
    """Test rebuild command logic."""

    def test_cmd_rebuild_with_gs_available(self, fake_process):
        """Test rebuild with git-spice available"""
        # First resolve_working_branch call
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="work\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        # Second get_config call in cmd_rebuild
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        # Rebuild the knit
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "work-tmp"],
            returncode=1,
            stderr="not found\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "work-tmp", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "b1"],
            stdout="Merged\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-f", "work", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "work"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            stdout=""
        )
        # After rebuild, detect_and_restack is called
        fake_process.register_subprocess(
            "which gs",
            stdout="/usr/local/bin/gs\n"
        )
        fake_process.register_subprocess(
            "gs --version",
            stdout="gs version 0.13.0\n"
        )
        fake_process.register_subprocess(
            ["git", "gs", "stack", "restack"],
            stdout=""
        )
        cmd_rebuild("work")


class TestRestackCommand:
    """Test restack command logic."""

    def test_cmd_restack_with_git_spice(self, fake_process):
        """Test restack when git-spice is available"""
        # Get current branch
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="work\n"
        )
        # Get config
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        # Try to detect and restack
        fake_process.register_subprocess(
            "which gs",
            stdout="/usr/local/bin/gs\n"
        )
        fake_process.register_subprocess(
            "gs --version",
            stdout="gs version 0.13.0\n"
        )
        fake_process.register_subprocess(
            ["git", "gs", "stack", "restack"],
            stdout=""
        )
        cmd_restack("work")


class TestCLIRemoveError:
    """Test remove command error handling."""

    def test_remove_with_knit_error(self, fake_process):
        """Test remove when KnitError is raised"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="work\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        # The remove operation will fail with branch not in knit
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "work-tmp"],
            returncode=1,
            stderr="not found\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "work-tmp", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "b1"],
            stdout="Merged\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-f", "work", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "work"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "work-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            stdout=""
        )
        result = runner.invoke(cli, split("remove -w work b2"))
        # This should fail with exit code
        check(result.exit_code != 0)


class TestCLIAddNotExistError:
    """Test add command when branch doesn't exist."""

    def test_add_branch_not_exist(self, fake_process):
        """Test add when feature branch doesn't exist"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="work\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexist"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        result = runner.invoke(cli, split("add -w work nonexist"))
        check(result.exit_code != 0)
        check("does not exist" in result.output or "error" in result.output.lower())
