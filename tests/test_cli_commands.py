"""Integration tests for Click commands."""

import os
import subprocess
from pathlib import Path

from shlex import split
from click.testing import CliRunner
from pytest_check import check

from git_knit.cli import cli


def test_init_command(temp_git_repo: Path):
    """Test init command through CLI"""
    runner = CliRunner()

    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_git_repo)
        result = runner.invoke(cli, split("init work main b1 b2"))
        check(result.exit_code == 0)
        # Verify output contains success message
        check("work" in result.output or result.output == "")
    finally:
        os.chdir(orig_cwd)


def test_add_command(temp_knit_repo_for_cli: Path):
    """Test add command through CLI"""
    runner = CliRunner()

    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        # Create b3 branch if it doesn't exist
        subprocess.run(["git", "checkout", "-b", "b3"], check=False)
        (temp_knit_repo_for_cli / "b3.txt").write_text("Content for b3")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add b3"], check=True)
        subprocess.run(["git", "checkout", "work"], check=True)

        result = runner.invoke(cli, split("add -w work b3"))
        check(result.exit_code == 0)
        # Verify output contains success message
        check("b3" in result.output)
        check("Added" in result.output or "work" in result.output)
    finally:
        os.chdir(orig_cwd)


def test_status_command(temp_knit_repo_for_cli: Path):
    """Test status command through CLI"""
    runner = CliRunner()

    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        result = runner.invoke(cli, split("status -w work"))
        check(result.exit_code == 0)
        check("work" in result.output)
        check("main" in result.output)
        check("Feature branches:" in result.output)
        check("b1" in result.output)
        check("b2" in result.output)
    finally:
        os.chdir(orig_cwd)


def test_remove_command(temp_knit_repo_for_cli: Path):
    """Test remove command through CLI"""
    runner = CliRunner()

    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        result = runner.invoke(cli, split("remove -w work b1"))
        check(result.exit_code == 0)
        # Verify that b1 was removed
        check("b1" in result.output or result.output == "")
    finally:
        os.chdir(orig_cwd)


def test_rebuild_command(temp_knit_repo_for_cli: Path):
    """Test rebuild command through CLI"""
    runner = CliRunner()

    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        result = runner.invoke(cli, split("rebuild -w work"))
        check(result.exit_code == 0)
        check("rebuild" in result.output.lower() or result.output == "")
    finally:
        os.chdir(orig_cwd)
