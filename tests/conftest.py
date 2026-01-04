import subprocess
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner

from git_knit.cli import cli
from git_knit.operations import GitExecutor, KnitConfigManager


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with a main branch."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    (tmp_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)
    
    # Rename master to main
    subprocess.run(["git", "branch", "-m", "master", "main"], cwd=tmp_path, check=True)

    yield tmp_path


@pytest.fixture
def temp_git_repo_with_branches(
    temp_git_repo: Path,
) -> dict[str, Path | list[str]]:
    """Create a temporary repo with multiple branches."""
    branches = ["b1", "b2", "b3"]

    for branch in branches:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add {branch}"], cwd=temp_git_repo, check=True
        )

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

    executor = GitExecutor(cwd=temp_git_repo)
    manager = KnitConfigManager(executor)
    manager.init_knit("work", "main", ["b1", "b2"])
    executor.create_branch("work", "main")
    executor.checkout("work")
    return temp_git_repo
