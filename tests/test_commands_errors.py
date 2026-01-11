"""Tests for command error handling and edge cases."""

import pytest
from pytest_check import check
from click.testing import CliRunner
from shlex import split

from git_knit.cli import cli
from git_knit.commands_logic import (
    cmd_add,
    cmd_remove,
)
from git_knit.errors import (
    BranchNotFoundError,
    AlreadyInKnitError,
)


class TestAddCommandErrors:
    """Test add command error handling."""

    def test_cmd_add_nonexistent_branch(self, fake_process):
        """Test cmd_add fails when branch doesn't exist"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexistent"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        with pytest.raises(BranchNotFoundError):
            cmd_add("main-working", "nonexistent")

    def test_cmd_add_duplicate_branch(self, fake_process):
        """Test cmd_add fails when branch already in knit"""
        # First call in cmd_add -> resolve_working_branch -> get_config
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        # Second call in add_branch -> branch_exists check
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "feature/a"],
            stdout=""
        )
        # Third call in add_branch -> get_config
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        with pytest.raises(AlreadyInKnitError):
            cmd_add("main-working", "feature/a")


class TestRemoveCommandErrors:
    """Test remove command error handling."""

    def test_cmd_remove_branch_not_in_knit(self, fake_process):
        """Test cmd_remove fails when branch not in knit"""
        # First get_config call for resolve_working_branch
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        # Second get_config call for remove_branch check
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        # Following commands for the rebuild that happens after remove
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            returncode=1,
            stderr="not found\n"
        )
        fake_process.register_subprocess(
            ["git", "branch", "main-working-tmp", "main"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "main-working-tmp"],
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
            ["git", "branch", "-f", "main-working", "main-working-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "checkout", "main-working"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "config", "--unset", "knit.main-working.feature-branches"],
            stdout=""
        )

        from git_knit.errors import BranchNotInKnitError
        with pytest.raises(BranchNotInKnitError):
            cmd_remove("main-working", "feature/b")


class TestCLIAddCommandErrors:
    """Test add command CLI error handling."""

    def test_add_nonexistent_branch_via_cli(self, fake_process):
        """Test add command fails when branch doesn't exist"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexistent"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main.base-branch"],
            returncode=1,
            stdout=""
        )

        result = runner.invoke(cli, split("add nonexistent"))
        check(result.exit_code != 0)


class TestCLISharedErrors:
    """Test shared parameter resolution errors."""

    def test_resolve_working_branch_param_no_knit(self, fake_process):
        """Test resolve_working_branch_param when not a knit"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main.base-branch"],
            returncode=1,
            stdout=""
        )

        # Try any command that requires working branch
        result = runner.invoke(cli, split("status"))
        check(result.exit_code != 0)
        check("knit" in result.output.lower() or "error" in result.output.lower())


class TestInitCommandErrors:
    """Test init command error handling."""

    def test_init_nonexistent_base_branch(self, fake_process):
        """Test init fails when base branch doesn't exist"""
        runner = CliRunner()
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexistent"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        result = runner.invoke(cli, split("init work nonexistent b1"))
        check(result.exit_code != 0)
        check("does not exist" in result.output or "error" in result.output.lower())

    def test_init_nonexistent_feature_branch(self, fake_process):
        """Test init fails when feature branch doesn't exist"""
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
            ["git", "rev-parse", "--verify", "nonexistent"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        result = runner.invoke(cli, split("init work main nonexistent"))
        check(result.exit_code != 0)
        check("does not exist" in result.output or "error" in result.output.lower())

    def test_init_on_current_branch(self, fake_process):
        """Test init fails when working branch is current branch"""
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
        check("current" in result.output.lower() or "error" in result.output.lower())


class TestRemoveCommandErrorsCLI:
    """Test remove command error handling via CLI."""

    def test_remove_nonexistent_branch_via_cli(self, fake_process):
        """Test remove command fails when branch doesn't exist in knit"""
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
        # Following commands for the rebuild that happens after remove
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
        check(result.exit_code != 0)
        check("not in knit" in result.output.lower() or "error" in result.output.lower())
