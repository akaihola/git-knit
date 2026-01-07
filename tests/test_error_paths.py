"""Tests for uncovered error paths in commands."""

from pytest_check import check
from click.testing import CliRunner
from shlex import split

from git_knit.cli import cli


class TestAddCommandKnitErrorPath:
    """Test add command KnitError exception path."""

    def test_add_knit_error_raised(self, fake_process):
        """Test add command when KnitError is raised and caught"""
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
            ["git", "rev-parse", "--verify", "b1"],
            stdout=""
        )
        # Second get_config for add_branch
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.work.feature-branches"],
            stdout="b1\n"
        )
        # b1 already in knit - will raise AlreadyInKnitError which is caught as KnitError
        result = runner.invoke(cli, split("add -w work b1"))
        check(result.exit_code != 0)
        check("already" in result.output.lower() or "error" in result.output.lower())


class TestInitCommandErrorPaths:
    """Test init command error paths."""

    def test_init_base_branch_not_exist(self, fake_process):
        """Test init when base branch doesn't exist"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexist"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        result = runner.invoke(cli, split("init work nonexist b1"))
        check(result.exit_code != 0)

    def test_init_feature_branch_not_exist(self, fake_process):
        """Test init when feature branch doesn't exist"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="other\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "b1"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexist"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        result = runner.invoke(cli, split("init work main b1 nonexist"))
        check(result.exit_code != 0)

    def test_init_on_working_branch(self, fake_process):
        """Test init when working branch is current"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="work\n"
        )
        result = runner.invoke(cli, split("init work main b1"))
        check(result.exit_code != 0)


class TestRemoveCommandErrorPaths:
    """Test remove command error paths through CLI."""

    def test_remove_knit_error_raised(self, fake_process):
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
        # KnitError path: removal of branch that doesn't exist
        result = runner.invoke(cli, split("remove -w work b2"))
        check(result.exit_code != 0)
