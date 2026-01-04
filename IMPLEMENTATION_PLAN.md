# git-knit Implementation Plan

## Overview

This document outlines the implementation strategy for `git-knit`, a Python CLI tool that enables a merged branch workflow where multiple feature branches are combined into working branches.

## Technology Stack & Design Decisions

### Core Dependencies (Minimal)

| Dependency | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Python** | >=3.10 | Runtime | Use modern language features |
| **pytest** | >=9.0 | Testing | Native subtests support |
| **pytest-subprocess** | ^1.6 | Testing | Mock git commands reliably |
| **click** | ^8.1 | CLI | Industry standard, minimal deps |
| No gitpython/pygit2 | - | Git ops | Use subprocess directly to minimize dependencies |

### Project Structure

```
git-knit/
├── pyproject.toml              # Project config, deps, build system
├── README.md                   # User documentation
├── IMPLEMENTATION_PLAN.md      # This file
├── specification.md            # Original specification
├── .gitignore
├── .python-version             # Pin Python version
├── src/
│   └── git_knit/               # Package directory
│       ├── __init__.py         # Public API
│       ├── cli.py              # Click-based CLI entry point
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── add.py          # git knit add
│       │   ├── commit.py       # git knit commit
│       │   ├── init.py         # git knit init
│       │   ├── move.py         # git knit move
│       │   ├── remove.py       # git knit remove
│       │   ├── rebuild.py      # git knit rebuild
│       │   ├── restack.py      # git knit restack
│       │   └── status.py       # git knit status
│       ├── errors.py           # Custom exceptions
│       └── operations.py       # Core business logic
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures
    ├── test_commands/
    │   ├── __init__.py
    │   ├── test_add.py
    │   ├── test_commit.py
    │   ├── test_init.py
    │   ├── test_move.py
    │   ├── test_remove.py
    │   ├── test_rebuild.py
    │   ├── test_restack.py
    │   └── test_status.py
    └── test_operations.py
```

## Key Design Principles

### 1. Minimal Dependencies
- **Click** for CLI (well-maintained, small footprint)
- **Subprocess** for Git operations (no GitPython to avoid git binary dep)
- **Rich error messages** with clear actionable guidance

### 2. Modern Python Features (3.10+)

**Type Hints:**
```python
from typing import Literal, Never

def resolve_working_branch(
    explicit: str | None = None
) -> str:
    """Resolve working branch from context or explicit flag."""
```

**Pattern Matching:**
```python
match result.stdout:
    case "git-spice"*:
        return GitSpiceType.GIT_SPICE
    case "Ghostscript"* | "GPL Ghostscript"*:
        return GitSpiceType.GHOSTSCRIPT
    case _:
        return GitSpiceType.UNKNOWN
```

**Dataclasses for State:**
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class KnitConfig:
    """Immutable configuration for a working branch."""
    working_branch: str
    base_branch: str
    feature_branches: tuple[str, ...]
```

### 3. Error Handling

Custom exception hierarchy:
```python
class KnitError(Exception):
    """Base exception for all knit errors."""
    exit_code: int = 1

class KnitNotInitializedError(KnitError):
    """Raised when knit is not initialized."""
    pass

class UncommittedChangesError(KnitError):
    """Raised when operation requires clean working tree."""
    exit_code: int = 2

class GitConflictError(KnitError):
    """Raised when git operation encounters conflicts."""
    exit_code: int = 3
```

### 4. Testing Strategy

**Pytest 9+ Features:**
- Native `subtests` fixture for parameterized scenarios
- `tmp_path` fixture for real Git repository testing
- `pytest-subprocess` for reliable Git command mocking

**Test Coverage:**
- Unit tests for business logic (operations.py)
- Integration tests for full workflows
- Subtests for multiple scenario variants
- 100% line coverage target

## Implementation Phases

### Phase 1: Project Setup & Foundation

**Deliverables:**
1. `pyproject.toml` with uv-build backend
2. Project structure with `src/` layout
3. Click CLI entry point
4. Error types and base operations

**Configuration:**
```toml
[project]
name = "git-knit"
version = "0.1.0"
description = "Merged branch workflow tool for Git"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Author", email = "author@example.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Version Control :: Git",
]

dependencies = [
    "click>=8.1.0,<9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.0,<10.0.0",
    "pytest-subprocess>=1.6.0,<2.0.0",
    "pytest-cov>=6.0.0,<7.0.0",
]

[project.scripts]
git-knit = "git_knit.cli:cli"

[build-system]
requires = ["uv_build>=0.9.21,<0.10.0"]
build-backend = "uv_build"

[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=git_knit",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html",
]

[tool.coverage.run]
source = ["src/git_knit"]
branch = true

[tool.coverage.report]
fail_under = 100
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Phase 2: Core Operations Layer

**File:** `src/git_knit/operations.py`

**Key Classes/Functions:**
```python
class GitExecutor:
    """Execute git commands with proper error handling."""
    
    def run(
        self,
        args: list[str],
        check: bool = True,
        capture: bool = False,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str] | None:
        """Run a git command safely."""
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
    
    def is_clean_working_tree(self) -> bool:
        """Check if working tree has uncommitted changes."""
    
    def merge_branch(self, branch: str) -> None:
        """Merge a branch into current HEAD."""
    
    def cherry_pick(self, commit: str) -> None:
        """Cherry-pick a commit."""
    
    def find_commit(self, ref: str, message: bool = False) -> str:
        """Find commit hash by reference or message substring."""


class KnitConfigManager:
    """Manage knit metadata in git config."""
    
    def init_knit(
        self,
        working_branch: str,
        base_branch: str,
        feature_branches: list[str],
    ) -> None:
        """Initialize a new knit configuration."""
    
    def add_branch(self, working_branch: str, branch: str) -> None:
        """Add a feature branch to knit."""
    
    def remove_branch(self, working_branch: str, branch: str) -> None:
        """Remove a feature branch from knit."""
    
    def get_config(self, working_branch: str) -> KnitConfig:
        """Get configuration for a working branch."""
    
    def list_working_branches(self) -> list[str]:
        """List all configured working branches."""
    
    def is_initialized(self) -> bool:
        """Check if any knit is configured."""
    
    def resolve_working_branch(self, explicit: str | None = None) -> str:
        """Resolve working branch from context or explicit flag."""


class GitSpiceDetector:
    """Detect if git-spice is available (not GhostScript)."""
    
    def detect(self) -> Literal["git-spice", "ghostscript", "not-found", "unknown"]:
        """Detect gs binary type."""
    
    def restack_if_available(self) -> bool:
        """Run gs stack restack if git-spice is available."""
        # Returns True if restack was executed


class KnitRebuilder:
    """Rebuild working branches from scratch."""
    
    def rebuild(self, config: KnitConfig, checkout: bool = True) -> None:
        """Rebuild working branch by deleting and recreating it."""
```

### Phase 3: Command Implementations

**Command Pattern:**
Each command follows this structure:
```python
import click

@click.command()
@click.argument("working-branch")
@click.argument("base-branch")
@click.argument("branches", nargs=-1)
def init(working_branch: str, base_branch: str, branches: tuple[str, ...]) -> None:
    """Initialize a new knit configuration.
    
    WORKING_BRANCH: Name for the merged working branch
    BASE_BRANCH: Base branch (e.g., main)
    BRANCHES: Feature branches to include
    """
    executor = GitExecutor()
    config_manager = KnitConfigManager(executor)
    
    # Validation
    if not executor.branch_exists(base_branch):
        raise click.ClickException(f"Base branch '{base_branch}' does not exist")
    
    if executor.get_current_branch() == working_branch:
        raise click.ClickException(
            f"Cannot initialize knit on current branch '{working_branch}'"
        )
    
    # Create working branch if needed
    if not executor.branch_exists(working_branch):
        executor.create_branch(working_branch, base_branch)
    else:
        click.confirm(
            f"Branch '{working_branch}' already exists. Use it as working branch?",
            abort=True,
        )
    
    # Store configuration
    config_manager.init_knit(working_branch, base_branch, list(branches))
    
    # Merge feature branches
    executor.checkout(working_branch)
    for branch in branches:
        if not executor.branch_exists(branch):
            raise click.ClickException(f"Feature branch '{branch}' does not exist")
        click.echo(f"Merging {branch} into {working_branch}...")
        executor.merge_branch(branch)
    
    click.echo(f"Knit initialized: {working_branch} = {base_branch} + {', '.join(branches)}")
```

**Working Branch Resolution Helper:**
```python
def resolve_working_branch_param(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> str:
    """Resolve working branch from flag or current branch."""
    executor = ctx.ensure_object(GitExecutor)
    config_manager = ctx.ensure_object(KnitConfigManager)
    
    try:
        return config_manager.resolve_working_branch(value)
    except KnitError as e:
        raise click.ClickException(str(e))
```

### Phase 4: CLI Entry Point

**File:** `src/git_knit/cli.py`

```python
import click
from .commands import (
    add,
    commit,
    init,
    move,
    remove,
    rebuild,
    restack,
    status,
)

@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Git-knit: Merged branch workflow tool.
    
    Work on multiple feature branches simultaneously by merging them
    into a working branch, then route commits back to their sources.
    """
    ctx.ensure_object(dict)
    # Shared objects will be injected by subcommands
    executor = GitExecutor()
    ctx.obj["executor"] = executor
    ctx.obj["config_manager"] = KnitConfigManager(executor)

cli.add_command(init.init)
cli.add_command(add.add)
cli.add_command(remove.remove)
cli.add_command(commit.commit)
cli.add_command(move.move)
cli.add_command(rebuild.rebuild)
cli.add_command(restack.restack)
cli.add_command(status.status)

if __name__ == "__main__":
    cli()
```

### Phase 5: Testing Infrastructure

**File:** `tests/conftest.py`

```python
import subprocess
from pathlib import Path
from typing import Generator

import pytest

@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with a main branch."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)
    
    yield tmp_path


@pytest.fixture
def temp_git_repo_with_branches(temp_git_repo: Path) -> dict[str, Path]:
    """Create a temporary repo with multiple branches."""
    # Create feature branches
    for branch in ["b1", "b2", "b3"]:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", f"Add {branch}"], cwd=temp_git_repo, check=True)
    
    # Return to main
    subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)
    
    return {"repo": temp_git_repo, "branches": ["b1", "b2", "b3"]}
```

**Example Test with Subtests:**

```python
# tests/test_operations.py
from git_knit.operations import KnitConfigManager

def test_resolve_working_branch(subtests, temp_git_repo_with_branches):
    """Test working branch resolution with subtests."""
    repo = temp_git_repo_with_branches["repo"]
    executor = GitExecutor(cwd=repo)
    config_manager = KnitConfigManager(executor)
    
    # Initialize a knit
    config_manager.init_knit("w", "main", ["b1", "b2"])
    
    test_cases = [
        ("on_working_branch", "w", None, "w"),
        ("explicit_flag", None, "work", "work"),
        ("from_other_branch", "main", "w", "w"),
    ]
    
    for name, current_branch, explicit, expected in test_cases:
        with subtests.test(
            msg=name,
            current_branch=current_branch,
            explicit=explicit,
            expected=expected,
        ):
            if current_branch:
                executor.checkout(current_branch)
            
            result = config_manager.resolve_working_branch(explicit)
            assert result == expected
```

### Phase 6: Edge Case Handling

**Implementation Checklist:**

1. **Empty Knit** (no feature branches)
   - [ ] Allow `git knit init w main` with no branches
   - [ ] Ensure `w` is just a clone of `main`

2. **Feature Branch Updated Externally**
   - [ ] Detect stale working branch
   - [ ] Provide guidance to run `git knit rebuild`

3. **Dependency Chain**
   - [ ] Preserve branch order in config
   - [ ] Merge in order: `b1:b2:b3` means merge b1, then b2, then b3

4. **Working Branch Name Conflict**
   - [ ] Prompt user if working branch already exists
   - [ ] Verify base matches if reusing

5. **Conflict Handling**
   - [ ] Abort immediately on conflicts
   - [ ] Clear error message
   - [ ] Recommend `git rerere` for automation

6. **git-spice Detection**
   - [ ] Check `gs --help` for "git-spice" substring
   - [ ] Distinguish from GhostScript
   - [ ] Graceful degradation if not found

7. **Large Number of Branches**
   - [ ] Efficient config storage (colon-separated)
   - [ ] Batch merge operations if needed

8. **Merge Commits on Working Branch**
   - [ ] Detect unexpected commits
   - [ ] Warn user to run `git knit rebuild`

## Implementation Order

### Week 1: Foundation
1. Project setup (`pyproject.toml`, directory structure)
2. Core error types
3. `GitExecutor` class with basic operations
4. Test infrastructure fixtures

### Week 2: Configuration Management
5. `KnitConfigManager` class
6. Config read/write operations
7. Working branch resolution logic
8. Tests for config layer

### Week 3: Commands (Part 1)
9. `git knit init` command
10. `git knit add` command
11. `git knit remove` command
12. `git knit status` command
13. Comprehensive tests for these commands

### Week 4: Commands (Part 2)
14. `git knit commit` command
15. `git knit move` command
16. `git knit rebuild` command
17. `git knit restack` command
18. Comprehensive tests for these commands

### Week 5: Polish & Coverage
19. Integration tests for full workflows
20. Edge case handling
21. Error message refinement
22. Documentation (README, examples)
23. Achieve 100% test coverage

## Build & Installation

### Development Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <repo-url>
cd git-knit

# Create virtual environment and install dependencies
uv sync --all-extras

# Run tests
uv run pytest
```

### Building Distribution
```bash
# Build wheel and source distribution
uv build

# Install locally
uv pip install dist/git_knit-0.1.0-py3-none-any.whl
```

### Running as Git Command
The tool can be invoked as `git-knit` or integrated with git as `git knit`:

**Option 1: As standalone command**
```bash
git-knit init w main b1 b2
```

**Option 2: As git subcommand (symlink)**
```bash
# Create symlink to git binary directory
ln -s $(which git-knit) $(git --exec-path)/git-knit

# Now can use as:
git knit init w main b1 b2
```

## Success Criteria

1. ✅ All commands from specification implemented
2. ✅ 100% test coverage (lines and branches)
3. ✅ Zero external dependencies beyond Click
4. ✅ Clear, actionable error messages
5. ✅ Comprehensive documentation
6. ✅ Full pytest 9+ subtests usage
7. ✅ Modern Python 3.10+ features throughout
8. ✅ Works on Python 3.10, 3.11, 3.12
9. ✅ Clean, elegant codebase with type hints

## Notes & Considerations

- **Performance**: Branch order matters for merge operations
- **Safety**: Always check for uncommitted changes before destructive ops
- **Idempotency**: Commands should be safe to re-run where possible
- **Testing**: Use real Git repos via `tmp_path` for integration tests
- **Mocking**: Use `pytest-subprocess` for unit tests to avoid Git binary dependency
- **Documentation**: Include examples for each command in README

---

*This plan provides a comprehensive roadmap for implementing git-knit with modern Python practices, minimal dependencies, and complete test coverage.*
