import os
import subprocess
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with a main branch and b3 branch."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "rerere.enabled", "false"], cwd=tmp_path, check=True
    )

    (tmp_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    cur = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if cur != "main":
        subprocess.run(["git", "branch", "-m", cur, "main"], cwd=tmp_path, check=True)

    # Create b3 branch for testing
    subprocess.run(["git", "checkout", "-b", "b3"], cwd=tmp_path, check=True)
    (tmp_path / "b3.txt").write_text("Content for b3")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add b3"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=tmp_path, check=True)

    yield tmp_path


@pytest.fixture
def temp_git_repo_with_branches(
    temp_git_repo: Path,
) -> dict[str, Path | list[str]]:
    """Create a temporary repo with multiple branches."""
    branches = ["b1", "b2"]

    for branch in branches:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add {branch}"], cwd=temp_git_repo, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    return {"repo": temp_git_repo, "branches": branches}


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_knit_repo(temp_git_repo):
    """Create a temporary repo with a knit configured."""
    # Create branches b1, b2 first
    for branch in ["b1", "b2"]:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", f"Add {branch}"], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    # Use git commands directly instead of old classes
    from git_knit.operations.config_functions import init_knit
    from git_knit.operations.executor_functions import create_branch, checkout

    # Change to repo directory for git commands
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_git_repo)
        init_knit("work", "main", ["b1", "b2"])
        create_branch("work", "main")
        checkout("work")
    finally:
        os.chdir(orig_cwd)

    return temp_git_repo


@pytest.fixture
def temp_knit_repo_for_cli(temp_git_repo: Path) -> Path:
    """Create a temporary repo with knit configured for CLI testing."""
    from git_knit.operations.config_functions import init_knit
    from git_knit.operations.executor_functions import create_branch, checkout

    # Create branches b1 and b2
    for branch in ["b1", "b2"]:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add {branch}"], cwd=temp_git_repo, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    # Initialize knit using pure functions
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_git_repo)
        init_knit("work", "main", ["b1", "b2"])
        create_branch("work", "main")
        checkout("work")
    finally:
        os.chdir(orig_cwd)

    return temp_git_repo
