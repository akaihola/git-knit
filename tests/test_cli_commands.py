"""Integration tests for Click commands."""

import pytest
from shlex import split
from click.testing import CliRunner

from git_knit.cli import cli


@pytest.mark.skip(reason="Requires git repo setup")
def test_init_command(temp_git_repo_with_branches):
    """Test init command through CLI"""
    runner = CliRunner()
    result = runner.invoke(cli, split("init main-working main b1 b2"))
    assert result.exit_code == 0


@pytest.mark.skip(reason="Requires git repo setup")
def test_add_command(temp_knit_repo):
    """Test add command through CLI"""
    runner = CliRunner()
    result = runner.invoke(cli, split("add -w work b3"))
    assert result.exit_code == 0


@pytest.mark.skip(reason="Requires git repo setup")
def test_status_command(temp_knit_repo):
    """Test status command through CLI"""
    runner = CliRunner()
    result = runner.invoke(cli, split("status -w work"))
    assert result.exit_code == 0
    assert "work" in result.output


@pytest.mark.skip(reason="Requires git repo setup")
def test_remove_command(temp_knit_repo):
    """Test remove command through CLI"""
    runner = CliRunner()
    result = runner.invoke(cli, split("remove -w work b1"))
    assert result.exit_code == 0


@pytest.mark.skip(reason="Requires git repo setup")
def test_rebuild_command(temp_knit_repo):
    """Test rebuild command through CLI"""
    runner = CliRunner()
    result = runner.invoke(cli, split("rebuild -w work"))
    assert result.exit_code == 0
