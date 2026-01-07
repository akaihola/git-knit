# Functional Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert git-knit from OOP (classes) to a functional programming style with pure functions for all operations, maintaining 100% test coverage and all existing behavior.

**Architecture:** Refactor into 5 layers: (1) Pure git execution functions, (2) Pure git config functions, (3) Composition functions for workflows, (4) Command logic functions extracted from Click handlers, (5) Thin Click CLI wrappers. Remove all classes except `KnitConfig` dataclass and keep custom exception classes.

**Tech Stack:** Python 3.13, Click 8.3, pytest with 100% coverage requirement, git subprocess operations

---

## Phase 1: Foundation - Create Pure Git Execution Functions

### Task 1: Create executor_functions.py with low-level git operations

**Files:**
- Create: `src/git_knit/operations/executor_functions.py`
- Reference: `src/git_knit/operations/executor.py` (will be deleted)
- Test: `tests/test_operations/test_executor_functions.py`

**Step 1: Write test file structure**

Create `tests/test_operations/test_executor_functions.py`:

```python
import subprocess
import pytest
from git_knit.operations.executor_functions import (
    run_git_command,
    get_current_branch,
    branch_exists,
    create_branch,
    checkout,
    delete_branch,
    merge_branch,
    cherry_pick,
    stash_push,
    stash_pop,
    get_commits_between,
    get_merge_base,
    is_ancestor,
    is_merge_commit,
    find_commit,
)

def test_run_git_command_success(fake_process):
    """Test successful git command execution"""
    fake_process.register_subprocess(
        ["git", "status"],
        stdout="On branch main\n"
    )
    result = run_git_command(["status"])
    assert result.returncode == 0
    assert "On branch main" in result.stdout

def test_run_git_command_failure(fake_process):
    """Test git command that fails"""
    fake_process.register_subprocess(
        ["git", "status"],
        returncode=128,
        stderr="fatal: not a git repository\n"
    )
    with pytest.raises(Exception):  # Will be GitError in implementation
        run_git_command(["status"])

def test_get_current_branch(fake_process):
    """Test getting current branch name"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main\n"
    )
    branch = get_current_branch()
    assert branch == "main"

def test_branch_exists_true(fake_process):
    """Test branch existence check - exists"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "feature/test"],
        returncode=0
    )
    assert branch_exists("feature/test") is True

def test_branch_exists_false(fake_process):
    """Test branch existence check - doesn't exist"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "nonexistent"],
        returncode=1
    )
    assert branch_exists("nonexistent") is False

def test_create_branch_from_base(fake_process):
    """Test creating a new branch from a base point"""
    fake_process.register_subprocess(
        ["git", "branch", "feature/new", "main"],
        returncode=0
    )
    create_branch("feature/new", "main")
    fake_process.assert_called()

def test_create_branch_from_current(fake_process):
    """Test creating a new branch from current HEAD"""
    fake_process.register_subprocess(
        ["git", "branch", "feature/new"],
        returncode=0
    )
    create_branch("feature/new")
    fake_process.assert_called()

def test_checkout_branch(fake_process):
    """Test checking out a branch"""
    fake_process.register_subprocess(
        ["git", "checkout", "feature/test"],
        returncode=0
    )
    checkout("feature/test")
    fake_process.assert_called()

def test_delete_branch(fake_process):
    """Test deleting a branch"""
    fake_process.register_subprocess(
        ["git", "branch", "-d", "feature/test"],
        returncode=0
    )
    delete_branch("feature/test", force=False)
    fake_process.assert_called()

def test_delete_branch_force(fake_process):
    """Test force deleting a branch"""
    fake_process.register_subprocess(
        ["git", "branch", "-D", "feature/test"],
        returncode=0
    )
    delete_branch("feature/test", force=True)
    fake_process.assert_called()

def test_merge_branch_success(fake_process):
    """Test successful merge"""
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/test"],
        returncode=0,
        stdout="Merge made by the 'ort' strategy.\n"
    )
    result = merge_branch("feature/test")
    assert result.returncode == 0

def test_merge_branch_conflict(fake_process):
    """Test merge with conflict"""
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/test"],
        returncode=1,
        stderr="CONFLICT (content): Merge conflict in file.txt\n"
    )
    with pytest.raises(Exception):  # Will be GitConflictError
        merge_branch("feature/test")

def test_cherry_pick_success(fake_process):
    """Test successful cherry-pick"""
    fake_process.register_subprocess(
        ["git", "cherry-pick", "abc123"],
        returncode=0,
        stdout="[main abc1234] Commit message\n"
    )
    result = cherry_pick("abc123")
    assert result.returncode == 0

def test_stash_push_and_pop(fake_process):
    """Test stashing and popping changes"""
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        returncode=0,
        stdout="Saved working directory and index state\n"
    )
    stash_push()

    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        returncode=0
    )
    stash_pop()
    fake_process.assert_called()

def test_get_commits_between(fake_process):
    """Test getting commits between two refs"""
    fake_process.register_subprocess(
        ["git", "rev-list", "base..feature"],
        stdout="abc123\ndef456\n"
    )
    commits = get_commits_between("base", "feature")
    assert commits == ["abc123", "def456"]

def test_get_merge_base(fake_process):
    """Test finding merge base"""
    fake_process.register_subprocess(
        ["git", "merge-base", "main", "feature"],
        stdout="abc123\n"
    )
    base = get_merge_base("main", "feature")
    assert base == "abc123"

def test_is_ancestor_true(fake_process):
    """Test ancestor check - is ancestor"""
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "abc123", "def456"],
        returncode=0
    )
    assert is_ancestor("abc123", "def456") is True

def test_is_ancestor_false(fake_process):
    """Test ancestor check - not ancestor"""
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "abc123", "def456"],
        returncode=1
    )
    assert is_ancestor("abc123", "def456") is False

def test_is_merge_commit_true(fake_process):
    """Test merge commit detection - is merge"""
    fake_process.register_subprocess(
        ["git", "cat-file", "-p", "abc123"],
        stdout="tree xyz789\nparent abc111\nparent abc222\nauthor ...\n"
    )
    assert is_merge_commit("abc123") is True

def test_is_merge_commit_false(fake_process):
    """Test merge commit detection - not merge"""
    fake_process.register_subprocess(
        ["git", "cat-file", "-p", "abc123"],
        stdout="tree xyz789\nparent abc111\nauthor ...\n"
    )
    assert is_merge_commit("abc123") is False

def test_find_commit_by_hash(fake_process):
    """Test finding commit by hash"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "abc123^{commit}"],
        stdout="abc123def456\n"
    )
    commit = find_commit("abc123")
    assert commit == "abc123def456"

def test_find_commit_by_message(fake_process):
    """Test finding commit by message pattern"""
    fake_process.register_subprocess(
        ["git", "log", "--all", "--grep=test message", "--format=%H"],
        stdout="abc123\ndef456\n"
    )
    # Returns first match
    commit = find_commit("test message")
    assert commit is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_operations/test_executor_functions.py -v`
Expected: FAIL - module doesn't exist yet

**Step 3: Create executor_functions.py with all functions**

Create `src/git_knit/operations/executor_functions.py`:

```python
"""Pure functions for executing git commands."""

import subprocess
from typing import Optional

from git_knit.errors import (
    GitConflictError,
    BranchNotFoundError,
    CommitNotFoundError,
    AmbiguousCommitError,
)


def run_git_command(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Execute a git command and return the result.

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout/stderr

    Returns:
        CompletedProcess with returncode, stdout, stderr

    Raises:
        GitConflictError: If merge/cherry-pick conflict detected
        RuntimeError: If git command fails and check=True
    """
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
    )

    if check and result.returncode != 0:
        if "CONFLICT" in result.stderr or "conflict" in result.stdout:
            raise GitConflictError(
                f"Conflict during git operation: {' '.join(args)}"
            )
        raise RuntimeError(
            f"Git command failed: {' '.join(args)}\n{result.stderr}"
        )

    return result


def get_current_branch() -> str:
    """Get the name of the currently checked out branch."""
    result = run_git_command(
        ["rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
    )
    return result.stdout.strip()


def branch_exists(branch: str) -> bool:
    """Check if a branch exists."""
    result = run_git_command(
        ["rev-parse", "--verify", branch],
        check=False,
    )
    return result.returncode == 0


def create_branch(branch: str, start_point: Optional[str] = None) -> None:
    """Create a new branch."""
    args = ["branch", branch]
    if start_point:
        args.append(start_point)
    run_git_command(args, check=True)


def checkout(branch: str) -> None:
    """Check out a branch."""
    run_git_command(["checkout", branch], check=True)


def delete_branch(branch: str, force: bool = False) -> None:
    """Delete a branch."""
    flag = "-D" if force else "-d"
    run_git_command(["branch", flag, branch], check=True)


def merge_branch(branch: str) -> subprocess.CompletedProcess:
    """Merge a branch into the current branch."""
    return run_git_command(["merge", "--no-ff", branch], check=True)


def cherry_pick(commit: str) -> subprocess.CompletedProcess:
    """Cherry-pick a commit into the current branch."""
    return run_git_command(["cherry-pick", commit], check=True)


def stash_push() -> None:
    """Stash uncommitted changes."""
    run_git_command(["stash", "push", "-u"], check=True)


def stash_pop() -> None:
    """Pop stashed changes."""
    run_git_command(["stash", "pop"], check=True)


def get_commits_between(base: str, target: str) -> list[str]:
    """Get commits between two refs (base..target)."""
    result = run_git_command(
        ["rev-list", f"{base}..{target}"],
        check=True,
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def get_merge_base(branch1: str, branch2: str) -> str:
    """Get the merge base of two branches."""
    result = run_git_command(
        ["merge-base", branch1, branch2],
        check=True,
    )
    return result.stdout.strip()


def is_ancestor(commit: str, branch: str) -> bool:
    """Check if commit is an ancestor of branch."""
    result = run_git_command(
        ["merge-base", "--is-ancestor", commit, branch],
        check=False,
    )
    return result.returncode == 0


def is_merge_commit(commit: str) -> bool:
    """Check if a commit is a merge commit."""
    result = run_git_command(
        ["cat-file", "-p", commit],
        check=True,
    )
    # Merge commits have 2 parent lines
    parent_count = result.stdout.count("\nparent ")
    return parent_count >= 2


def find_commit(ref: str) -> Optional[str]:
    """Find a commit by hash or message pattern."""
    # First try as a commit hash
    result = run_git_command(
        ["rev-parse", "--verify", f"{ref}^{{commit}}"],
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    # Try as a message pattern
    result = run_git_command(
        ["log", "--all", f"--grep={ref}", "--format=%H"],
        check=True,
    )
    commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    if not commits:
        raise CommitNotFoundError(f"Commit not found: {ref}")
    if len(commits) > 1:
        raise AmbiguousCommitError(f"Multiple commits match: {ref}")

    return commits[0]


def get_local_working_branch_commits(
    base_branch: str,
    feature_branches: list[str],
) -> list[str]:
    """
    Get commits in working branch that are not merge commits or from base/feature branches.
    """
    # Get all commits in working branch that aren't in base
    all_commits = get_commits_between(base_branch, "HEAD")

    # Filter out merge commits and commits from feature branches
    local_commits = []
    for commit in all_commits:
        if is_merge_commit(commit):
            continue

        # Check if commit is in any feature branch
        is_from_feature = False
        for feature in feature_branches:
            if is_ancestor(commit, feature):
                is_from_feature = True
                break

        if not is_from_feature:
            local_commits.append(commit)

    return local_commits


def is_clean_working_tree() -> bool:
    """Check if working tree is clean (no uncommitted changes)."""
    result = run_git_command(
        ["status", "--porcelain"],
        check=True,
    )
    return result.stdout.strip() == ""


def get_config_value(section: str, key: str) -> Optional[str]:
    """Get a git config value."""
    result = run_git_command(
        ["config", "--get", f"{section}.{key}"],
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def set_config_value(section: str, key: str, value: str) -> None:
    """Set a git config value."""
    run_git_command(
        ["config", f"{section}.{key}", value],
        check=True,
    )


def unset_config_value(section: str, key: str) -> None:
    """Unset a git config value."""
    run_git_command(
        ["config", "--unset", f"{section}.{key}"],
        check=True,
    )


def list_config_keys(section: str) -> list[str]:
    """List all keys in a git config section."""
    result = run_git_command(
        ["config", "--get-regexp", f"^{section}\\."],
        check=False,
    )
    if result.returncode != 0:
        return []

    keys = []
    for line in result.stdout.strip().split("\n"):
        if line:
            key = line.split(" ")[0].replace(f"{section}.", "")
            keys.append(key)
    return keys
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_operations/test_executor_functions.py -v`
Expected: PASS - all executor function tests pass

**Step 5: Commit**

```bash
git add src/git_knit/operations/executor_functions.py tests/test_operations/test_executor_functions.py
git commit -m "feat: create pure git execution functions layer"
```

---

## Phase 2: Config Layer - Convert to Pure Functions

### Task 2: Create config_functions.py with pure config operations

**Files:**
- Create: `src/git_knit/operations/config_functions.py`
- Reference: `src/git_knit/operations/config.py` (will be refactored)
- Test: `tests/test_operations/test_config_functions.py`

**Step 1: Write comprehensive tests**

Create `tests/test_operations/test_config_functions.py`:

```python
import pytest
from git_knit.operations.config_functions import (
    init_knit,
    add_branch,
    remove_branch,
    get_config,
    list_working_branches,
    resolve_working_branch,
    delete_config,
)
from git_knit.operations.config import KnitConfig
from git_knit.errors import (
    WorkingBranchNotSetError,
    BranchNotInKnitError,
    AlreadyInKnitError,
)


def test_init_knit_creates_config(fake_process):
    """Test initializing a knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.base_branch", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/b"],
        returncode=0
    )

    init_knit("main-working", "main", ["feature/a", "feature/b"])
    # Verify calls were made
    fake_process.assert_called()


def test_add_branch_to_knit(fake_process):
    """Test adding a branch to knit"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        stdout="feature/a\nfeature/b\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/c"],
        returncode=0
    )

    add_branch("main-working", "feature/c")
    fake_process.assert_called()


def test_add_duplicate_branch_fails(fake_process):
    """Test that adding duplicate branch raises error"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\n"
    )

    with pytest.raises(AlreadyInKnitError):
        add_branch("main-working", "feature/a")


def test_remove_branch_from_knit(fake_process):
    """Test removing a branch from knit"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\nknit.main-working.feature_branches feature/b\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/b"],
        returncode=0
    )

    remove_branch("main-working", "feature/a")
    fake_process.assert_called()


def test_remove_nonexistent_branch_fails(fake_process):
    """Test removing branch not in knit raises error"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\n"
    )

    with pytest.raises(BranchNotInKnitError):
        remove_branch("main-working", "feature/nonexistent")


def test_get_config_returns_knit_config(fake_process):
    """Test retrieving knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\nknit.main-working.feature_branches feature/b\n"
    )

    config = get_config("main-working")
    assert config is not None
    assert config.working_branch == "main-working"
    assert config.base_branch == "main"
    assert config.feature_branches == ["feature/a", "feature/b"]


def test_get_config_not_found_returns_none(fake_process):
    """Test retrieving non-existent configuration returns None"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.nonexistent\\."],
        returncode=1
    )

    config = get_config("nonexistent")
    assert config is None


def test_list_working_branches(fake_process):
    """Test listing all working branches"""
    fake_process.register_subprocess(
        ["git", "config", "--name-only", "--get-regexp", "^knit\\..*\\.base_branch"],
        stdout="knit.main-working.base_branch\nknit.dev-working.base_branch\n"
    )

    branches = list_working_branches()
    assert branches == ["main-working", "dev-working"]


def test_resolve_working_branch_explicit(fake_process):
    """Test resolving working branch when explicitly provided"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.my-branch\\."],
        stdout="knit.my-branch.base_branch main\n"
    )

    branch = resolve_working_branch("my-branch")
    assert branch == "my-branch"


def test_resolve_working_branch_current(fake_process):
    """Test resolving working branch from current branch"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="my-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.my-working\\."],
        stdout="knit.my-working.base_branch main\n"
    )

    branch = resolve_working_branch(None)
    assert branch == "my-working"


def test_resolve_working_branch_not_set_fails(fake_process):
    """Test resolving working branch fails if not set"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="random-branch\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.random-branch\\."],
        returncode=1
    )

    with pytest.raises(WorkingBranchNotSetError):
        resolve_working_branch(None)


def test_delete_config(fake_process):
    """Test deleting a knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.my-working\\."],
        stdout="knit.my-working.base_branch main\nknit.my-working.feature_branches feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset-all", "knit.my-working.base_branch"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset-all", "knit.my-working.feature_branches"],
        returncode=0
    )

    delete_config("my-working")
    fake_process.assert_called()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_operations/test_config_functions.py -v`
Expected: FAIL - module doesn't exist yet

**Step 3: Create config_functions.py**

Create `src/git_knit/operations/config_functions.py`:

```python
"""Pure functions for managing knit configuration."""

from typing import Optional

from git_knit.errors import (
    BranchNotFoundError,
    BranchNotInKnitError,
    AlreadyInKnitError,
    WorkingBranchNotSetError,
)
from git_knit.operations.config import KnitConfig
from git_knit.operations.executor_functions import (
    get_current_branch,
    branch_exists,
    get_config_value,
    set_config_value,
    unset_config_value,
    list_config_keys,
)


def _get_section(working_branch: str) -> str:
    """Get the git config section name for a working branch."""
    return f"knit.{working_branch}"


def init_knit(
    working_branch: str,
    base_branch: str,
    feature_branches: list[str],
) -> None:
    """Initialize a new knit configuration."""
    section = _get_section(working_branch)
    set_config_value(section, "base_branch", base_branch)
    for branch in feature_branches:
        set_config_value(section, "feature_branches", branch)


def add_branch(working_branch: str, branch: str) -> None:
    """Add a feature branch to a knit configuration."""
    if not branch_exists(branch):
        raise BranchNotFoundError(f"Branch not found: {branch}")

    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    if branch in config.feature_branches:
        raise AlreadyInKnitError(f"Branch already in knit: {branch}")

    section = _get_section(working_branch)
    set_config_value(section, "feature_branches", branch)


def remove_branch(working_branch: str, branch: str) -> None:
    """Remove a feature branch from a knit configuration."""
    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    if branch not in config.feature_branches:
        raise BranchNotInKnitError(f"Branch not in knit: {branch}")

    # Reconstruct feature_branches without the removed one
    section = _get_section(working_branch)
    unset_config_value(section, "feature_branches")
    for fb in config.feature_branches:
        if fb != branch:
            set_config_value(section, "feature_branches", fb)


def get_config(working_branch: str) -> Optional[KnitConfig]:
    """Retrieve the knit configuration for a working branch."""
    section = _get_section(working_branch)

    base_branch = get_config_value(section, "base_branch")
    if base_branch is None:
        return None

    # Get all feature branches for this working branch
    # Note: git config returns multiple values for the same key
    feature_branches_str = get_config_value(section, "feature_branches")
    if feature_branches_str is None:
        feature_branches = []
    else:
        # Parse comma-separated or newline-separated values
        feature_branches = [fb.strip() for fb in feature_branches_str.split("\n") if fb.strip()]

    return KnitConfig(
        working_branch=working_branch,
        base_branch=base_branch,
        feature_branches=feature_branches,
    )


def list_working_branches() -> list[str]:
    """List all configured working branches."""
    keys = list_config_keys("knit")
    working_branches = set()
    for key in keys:
        # Keys are like "main-working.base_branch"
        if key.endswith(".base_branch"):
            working_branch = key.replace(".base_branch", "")
            working_branches.add(working_branch)
    return sorted(list(working_branches))


def resolve_working_branch(working_branch: Optional[str]) -> str:
    """Resolve the working branch from explicit argument or current branch."""
    if working_branch:
        config = get_config(working_branch)
        if config is None:
            raise ValueError(f"Working branch not configured: {working_branch}")
        return working_branch

    # Try to infer from current branch
    current_branch = get_current_branch()
    config = get_config(current_branch)
    if config:
        return current_branch

    raise WorkingBranchNotSetError(
        f"Cannot determine working branch. Current branch '{current_branch}' is not a knit. "
        "Use --working-branch to specify."
    )


def delete_config(working_branch: str) -> None:
    """Delete a knit configuration."""
    config = get_config(working_branch)
    if config is None:
        raise ValueError(f"Working branch not configured: {working_branch}")

    section = _get_section(working_branch)
    unset_config_value(section, "base_branch")
    unset_config_value(section, "feature_branches")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_operations/test_config_functions.py -v`
Expected: PASS - all config function tests pass

**Step 5: Commit**

```bash
git add src/git_knit/operations/config_functions.py tests/test_operations/test_config_functions.py
git commit -m "feat: create pure git config functions layer"
```

---

## Phase 3: Composition Functions - Complex Workflows

### Task 3: Create operations_functions.py for higher-level workflows

**Files:**
- Create: `src/git_knit/operations/operations_functions.py`
- Reference: `src/git_knit/operations/rebuilder.py` (logic to extract)
- Reference: `src/git_knit/operations/spice_detector.py` (logic to extract)
- Test: `tests/test_operations/test_operations_functions.py`

**Step 1: Write comprehensive workflow tests**

Create `tests/test_operations/test_operations_functions.py`:

```python
import pytest
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
)
from git_knit.errors import GitConflictError, UncommittedChangesError


def test_rebuild_working_branch_success(fake_process):
    """Test successfully rebuilding a working branch"""
    # Setup: create working branch from base
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout=""  # Clean working tree
    )
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=1  # Doesn't exist yet
    )
    fake_process.register_subprocess(
        ["git", "branch", "main-working-tmp", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working-tmp"],
        returncode=0
    )
    # Merge feature branches
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/b"],
        returncode=0
    )
    # Cherry-pick local commits
    fake_process.register_subprocess(
        ["git", "rev-list", "main..main-working"],
        stdout="abc123\ndef456\n"
    )
    fake_process.register_subprocess(
        ["git", "cat-file", "-p", "abc123"],
        stdout="tree xyz\nparent base\nauthor ...\n"  # Not a merge
    )
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "abc123", "feature/a"],
        returncode=1  # Not in feature/a
    )
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "abc123", "feature/b"],
        returncode=1  # Not in feature/b
    )
    fake_process.register_subprocess(
        ["git", "cherry-pick", "abc123"],
        returncode=0
    )
    # Same checks for def456
    fake_process.register_subprocess(
        ["git", "cat-file", "-p", "def456"],
        stdout="tree xyz\nparent base\nauthor ...\n"
    )
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "def456", "feature/a"],
        returncode=1
    )
    fake_process.register_subprocess(
        ["git", "merge-base", "--is-ancestor", "def456", "feature/b"],
        returncode=1
    )
    fake_process.register_subprocess(
        ["git", "cherry-pick", "def456"],
        returncode=0
    )
    # Atomic update
    fake_process.register_subprocess(
        ["git", "branch", "-f", "main-working", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        returncode=0
    )
    # Cleanup
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=0
    )
    # Restore stash
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        returncode=0
    )

    rebuild_working_branch("main-working", "main", ["feature/a", "feature/b"])
    fake_process.assert_called()


def test_rebuild_with_uncommitted_changes_fails(fake_process):
    """Test that rebuild fails with uncommitted changes"""
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout="M file.txt\n"  # Uncommitted changes
    )

    with pytest.raises(UncommittedChangesError):
        rebuild_working_branch("main-working", "main", ["feature/a"])


def test_rebuild_with_conflict(fake_process):
    """Test rebuild handling merge conflicts"""
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=1
    )
    fake_process.register_subprocess(
        ["git", "branch", "main-working-tmp", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        returncode=1,
        stderr="CONFLICT (content): Merge conflict in file.txt\n"
    )
    fake_process.register_subprocess(
        ["git", "merge", "--abort"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        returncode=0
    )

    with pytest.raises(GitConflictError):
        rebuild_working_branch("main-working", "main", ["feature/a"])


def test_detect_and_restack_with_git_spice(fake_process):
    """Test detecting and using git-spice for restacking"""
    fake_process.register_subprocess(
        ["which", "gs"],
        stdout="/usr/local/bin/gs\n"
    )
    fake_process.register_subprocess(
        ["gs", "--version"],
        stdout="gs version 0.13.0 - ...\n"  # git-spice signature
    )
    fake_process.register_subprocess(
        ["gs", "stack", "restack"],
        returncode=0
    )

    detect_and_restack()
    fake_process.assert_called()


def test_detect_and_restack_without_git_spice(fake_process):
    """Test detect_and_restack when git-spice not available"""
    fake_process.register_subprocess(
        ["which", "gs"],
        returncode=1  # Not found
    )

    # Should not raise, just skip
    detect_and_restack()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_operations/test_operations_functions.py -v`
Expected: FAIL - module doesn't exist yet

**Step 3: Create operations_functions.py**

Create `src/git_knit/operations/operations_functions.py`:

```python
"""Pure functions for complex git workflows."""

import subprocess
from typing import Optional

from git_knit.errors import UncommittedChangesError, GitConflictError
from git_knit.operations.executor_functions import (
    is_clean_working_tree,
    stash_push,
    stash_pop,
    create_branch,
    delete_branch,
    checkout,
    merge_branch,
    cherry_pick,
    get_commits_between,
    is_merge_commit,
    is_ancestor,
    run_git_command,
)


def rebuild_working_branch(
    working_branch: str,
    base_branch: str,
    feature_branches: list[str],
) -> None:
    """
    Rebuild a working branch from scratch while preserving local commits.

    Process:
    1. Verify working tree is clean
    2. Stash uncommitted changes
    3. Create temporary branch from base
    4. Merge feature branches
    5. Cherry-pick local (non-merge, non-feature) commits
    6. Atomically update working branch
    7. Restore stashed changes

    Args:
        working_branch: Name of working branch to rebuild
        base_branch: Base branch to rebuild from
        feature_branches: List of feature branches to merge

    Raises:
        UncommittedChangesError: If working tree has uncommitted changes
        GitConflictError: If merge/cherry-pick conflicts occur
    """
    # Step 1: Verify clean working tree
    if not is_clean_working_tree():
        raise UncommittedChangesError("Working tree has uncommitted changes")

    # Step 2: Stash changes (in case there are any despite the check)
    stash_push()

    tmp_branch = f"{working_branch}-tmp"
    try:
        # Step 3: Clean up any leftover tmp branch
        try:
            delete_branch(tmp_branch, force=True)
        except Exception:
            pass  # Doesn't exist

        # Step 3: Create temporary branch from base
        create_branch(tmp_branch, base_branch)
        checkout(tmp_branch)

        # Step 4: Merge feature branches
        for feature in feature_branches:
            try:
                merge_branch(feature)
            except Exception as e:
                # Clean up on conflict
                run_git_command(["merge", "--abort"], check=False)
                raise GitConflictError(f"Conflict merging {feature}: {e}")

        # Step 5: Cherry-pick local commits
        local_commits = get_local_commits(base_branch, feature_branches)
        for commit in local_commits:
            try:
                cherry_pick(commit)
            except Exception as e:
                run_git_command(["cherry-pick", "--abort"], check=False)
                raise GitConflictError(f"Conflict cherry-picking {commit}: {e}")

        # Step 6: Atomically update working branch
        run_git_command(["branch", "-f", working_branch, tmp_branch], check=True)
        checkout(working_branch)

    finally:
        # Cleanup: delete temporary branch
        try:
            delete_branch(tmp_branch, force=True)
        except Exception:
            pass

        # Restore stashed changes
        try:
            stash_pop()
        except Exception:
            pass


def get_local_commits(base_branch: str, feature_branches: list[str]) -> list[str]:
    """Get commits that are local to working branch (not from base or features)."""
    commits = get_commits_between(base_branch, "HEAD")
    local = []

    for commit in commits:
        # Skip merge commits
        if is_merge_commit(commit):
            continue

        # Skip commits that are in any feature branch
        is_from_feature = False
        for feature in feature_branches:
            if is_ancestor(commit, feature):
                is_from_feature = True
                break

        if not is_from_feature:
            local.append(commit)

    return local


def detect_and_restack() -> None:
    """
    Detect if git-spice is available and restack if it is.

    Silently succeeds if git-spice is not available.
    """
    # Check if 'gs' is available and is git-spice
    result = run_git_command(
        ["which", "gs"],
        check=False,
    )
    if result.returncode != 0:
        return  # Not available

    # Verify it's git-spice, not ghostscript
    result = run_git_command(
        ["gs", "--version"],
        check=False,
    )
    if result.returncode != 0 or "git-spice" not in result.stdout:
        return  # Not git-spice

    # Restack
    run_git_command(["gs", "stack", "restack"], check=True)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_operations/test_operations_functions.py -v`
Expected: PASS - all composition function tests pass

**Step 5: Commit**

```bash
git add src/git_knit/operations/operations_functions.py tests/test_operations/test_operations_functions.py
git commit -m "feat: create composition functions for complex workflows"
```

---

## Phase 4: Command Logic Functions

### Task 4: Create commands_logic.py with extracted command logic

**Files:**
- Create: `src/git_knit/commands_logic.py`
- Reference: `src/git_knit/commands/*.py` (logic to extract)
- Test: `tests/test_commands_logic.py`

**Step 1: Write command logic tests**

Create `tests/test_commands_logic.py`:

```python
import pytest
from git_knit.commands_logic import (
    cmd_init,
    cmd_add,
    cmd_remove,
    cmd_status,
    cmd_move,
    cmd_rebuild,
    cmd_restack,
)
from git_knit.operations.config import KnitConfig
from git_knit.errors import (
    BranchNotFoundError,
    WorkingBranchNotSetError,
)


def test_cmd_init_creates_knit(fake_process):
    """Test init command logic"""
    fake_process.register_subprocess(
        ["git", "branch", "main-working", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.base_branch", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/b"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/b"],
        returncode=0
    )

    cmd_init("main-working", "main", ["feature/a", "feature/b"])
    fake_process.assert_called()


def test_cmd_add_to_knit(fake_process):
    """Test add command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "feature/c"],
        returncode=0  # Exists
    )
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/c"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/c"],
        returncode=0
    )

    cmd_add(None, "feature/c")  # None = infer from current
    fake_process.assert_called()


def test_cmd_remove_from_knit(fake_process):
    """Test remove command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\nknit.main-working.feature_branches feature/b\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset-all", "knit.main-working.feature_branches"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/b"],
        returncode=0
    )
    # Rebuild
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=1
    )
    fake_process.register_subprocess(
        ["git", "branch", "main-working-tmp", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/b"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "rev-list", "main..main-working"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "branch", "-f", "main-working", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        returncode=0
    )

    cmd_remove(None, "feature/a")
    fake_process.assert_called()


def test_cmd_status(fake_process, capsys):
    """Test status command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\nknit.main-working.feature_branches feature/b\n"
    )

    cmd_status(None)
    captured = capsys.readouterr()
    assert "main-working" in captured.out
    assert "main" in captured.out
    assert "feature/a" in captured.out
    assert "feature/b" in captured.out


def test_cmd_move_commit(fake_process):
    """Test move command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "abc123^{commit}"],
        stdout="abc123def456\n"
    )
    fake_process.register_subprocess(
        ["git", "cherry-pick", "abc123"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["which", "gs"],
        returncode=1  # git-spice not available
    )
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="feature/target\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.feature/target\\."],
        returncode=1  # Not a knit, skip rebuild
    )

    cmd_move("feature/target", "abc123")
    fake_process.assert_called()


def test_cmd_rebuild(fake_process):
    """Test rebuild command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\nknit.main-working.feature_branches feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=1
    )
    fake_process.register_subprocess(
        ["git", "branch", "main-working-tmp", "main"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "rev-list", "main..main-working"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "branch", "-f", "main-working", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=0
    )
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        returncode=0
    )

    cmd_rebuild(None)
    fake_process.assert_called()


def test_cmd_restack(fake_process):
    """Test restack command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\.main-working\\."],
        stdout="knit.main-working.base_branch main\n"
    )
    fake_process.register_subprocess(
        ["which", "gs"],
        stdout="/usr/local/bin/gs\n"
    )
    fake_process.register_subprocess(
        ["gs", "--version"],
        stdout="gs version 0.13.0\n"
    )
    fake_process.register_subprocess(
        ["gs", "stack", "restack"],
        returncode=0
    )

    cmd_restack(None)
    fake_process.assert_called()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_commands_logic.py -v`
Expected: FAIL - module doesn't exist yet

**Step 3: Create commands_logic.py**

Create `src/git_knit/commands_logic.py`:

```python
"""Pure functions for command implementations."""

from typing import Optional

import click

from git_knit.operations.config import KnitConfig
from git_knit.operations.config_functions import (
    init_knit,
    add_branch,
    remove_branch,
    get_config,
    resolve_working_branch,
)
from git_knit.operations.executor_functions import (
    create_branch,
    checkout,
    merge_branch,
    find_commit,
)
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
)


def cmd_init(
    working_branch: str,
    base_branch: str,
    feature_branches: list[str],
) -> None:
    """Initialize a new knit configuration."""
    create_branch(working_branch, base_branch)
    checkout(working_branch)
    init_knit(working_branch, base_branch, feature_branches)

    for branch in feature_branches:
        merge_branch(branch)


def cmd_add(
    working_branch: Optional[str],
    branch: str,
) -> None:
    """Add a branch to a knit."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)

    add_branch(wb, branch)

    checkout(wb)
    merge_branch(branch)


def cmd_remove(
    working_branch: Optional[str],
    branch: str,
) -> None:
    """Remove a branch from a knit and rebuild."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)

    remove_branch(wb, branch)

    # Rebuild after removing
    rebuild_working_branch(wb, config.base_branch, config.feature_branches)


def cmd_status(
    working_branch: Optional[str],
) -> None:
    """Display knit configuration."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)

    click.echo(f"Working branch: {config.working_branch}")
    click.echo(f"Base branch: {config.base_branch}")
    click.echo("Feature branches:")
    for branch in config.feature_branches:
        click.echo(f"  - {branch}")


def cmd_move(
    target_branch: str,
    commit_ref: str,
) -> None:
    """Move a commit to a different branch."""
    commit = find_commit(commit_ref)

    checkout(target_branch)
    merge_branch(commit)

    detect_and_restack()

    # If target is a knit, rebuild it
    config = get_config(target_branch)
    if config:
        rebuild_working_branch(target_branch, config.base_branch, config.feature_branches)


def cmd_rebuild(
    working_branch: Optional[str],
) -> None:
    """Force rebuild a knit from scratch."""
    wb = resolve_working_branch(working_branch)
    config = get_config(wb)

    rebuild_working_branch(wb, config.base_branch, config.feature_branches)


def cmd_restack(
    working_branch: Optional[str],
) -> None:
    """Restack branches using git-spice."""
    wb = resolve_working_branch(working_branch)
    detect_and_restack()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_commands_logic.py -v`
Expected: PASS - all command logic tests pass

**Step 5: Commit**

```bash
git add src/git_knit/commands_logic.py tests/test_commands_logic.py
git commit -m "feat: extract command logic into pure functions"
```

---

## Phase 5: Refactor Click Commands to Use Pure Functions

### Task 5: Update Click commands to call pure functions

**Files:**
- Modify: `src/git_knit/commands/init.py`
- Modify: `src/git_knit/commands/add.py`
- Modify: `src/git_knit/commands/remove.py`
- Modify: `src/git_knit/commands/commit.py`
- Test: `tests/test_commands/test_basic_commands.py` (existing, should still pass)

**Step 1: Refactor init.py**

Modify `src/git_knit/commands/init.py` - replace content with:

```python
"""Initialize a new knit configuration."""

import click

from git_knit.commands_logic import cmd_init
from git_knit.errors import KnitError


@click.command()
@click.argument("working_branch")
@click.argument("base_branch")
@click.argument("feature_branches", nargs=-1, required=True)
def init(working_branch: str, base_branch: str, feature_branches: tuple[str, ...]) -> None:
    """Initialize a new knit with working and feature branches."""
    try:
        cmd_init(working_branch, base_branch, list(feature_branches))
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)
```

**Step 2: Refactor add.py**

Modify `src/git_knit/commands/add.py` - replace content with:

```python
"""Add a branch to an existing knit."""

import click

from git_knit.commands_logic import cmd_add
from git_knit.commands._shared import resolve_working_branch_param
from git_knit.errors import KnitError


@click.command()
@click.option(
    "--working-branch",
    callback=resolve_working_branch_param,
    help="Working branch name (defaults to current branch)",
)
@click.argument("branch")
def add(working_branch: str, branch: str) -> None:
    """Add a branch to an existing knit."""
    try:
        cmd_add(working_branch, branch)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)
```

**Step 3: Refactor remove.py**

Modify `src/git_knit/commands/remove.py` - replace content with:

```python
"""Remove a branch from a knit."""

import click

from git_knit.commands_logic import cmd_remove, cmd_status
from git_knit.commands._shared import resolve_working_branch_param
from git_knit.errors import KnitError


@click.command()
@click.option(
    "--working-branch",
    callback=resolve_working_branch_param,
    help="Working branch name (defaults to current branch)",
)
@click.argument("branch")
def remove(working_branch: str, branch: str) -> None:
    """Remove a branch from a knit and rebuild."""
    try:
        cmd_remove(working_branch, branch)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)


@click.command()
@click.option(
    "--working-branch",
    callback=resolve_working_branch_param,
    help="Working branch name (defaults to current branch)",
)
def status(working_branch: str) -> None:
    """Display knit configuration."""
    try:
        cmd_status(working_branch)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)
```

**Step 4: Refactor commit.py**

Modify `src/git_knit/commands/commit.py` - replace content with:

```python
"""Complex operations: move, rebuild, and restack commands."""

import click

from git_knit.commands_logic import cmd_move, cmd_rebuild, cmd_restack
from git_knit.commands._shared import resolve_working_branch_param
from git_knit.errors import KnitError


@click.command()
@click.argument("target_branch")
@click.argument("commit")
def move(target_branch: str, commit: str) -> None:
    """Move a commit to a different branch."""
    try:
        cmd_move(target_branch, commit)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)


@click.command()
@click.option(
    "--working-branch",
    callback=resolve_working_branch_param,
    help="Working branch name (defaults to current branch)",
)
def rebuild(working_branch: str) -> None:
    """Force rebuild a knit from scratch."""
    try:
        cmd_rebuild(working_branch)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)


@click.command()
@click.option(
    "--working-branch",
    callback=resolve_working_branch_param,
    help="Working branch name (defaults to current branch)",
)
def restack(working_branch: str) -> None:
    """Restack branches using git-spice."""
    try:
        cmd_restack(working_branch)
    except KnitError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(e.exit_code)
```

**Step 5: Run existing command tests**

Run: `pytest tests/test_commands/ -v`
Expected: PASS - all existing command tests still pass

**Step 6: Commit**

```bash
git add src/git_knit/commands/init.py src/git_knit/commands/add.py src/git_knit/commands/remove.py src/git_knit/commands/commit.py
git commit -m "refactor: update Click commands to use pure functions"
```

---

## Phase 6: Cleanup - Remove Old Class-Based Code

### Task 6: Delete old OOP classes and update imports

**Files:**
- Delete: `src/git_knit/operations/executor.py`
- Delete: `src/git_knit/operations/rebuilder.py`
- Delete: `src/git_knit/operations/spice_detector.py`
- Modify: `src/git_knit/operations/config.py` (keep only `KnitConfig` dataclass)
- Modify: `src/git_knit/operations/__init__.py` (update exports)
- Modify: `src/git_knit/__init__.py` (update exports if needed)

**Step 1: Update config.py to keep only KnitConfig**

Read current `src/git_knit/operations/config.py`:

```python
# Keep only:

from dataclasses import dataclass

@dataclass(frozen=True)
class KnitConfig:
    """Immutable configuration for a knit."""
    working_branch: str
    base_branch: str
    feature_branches: list[str]

# Delete: KnitConfigManager class
```

**Step 2: Update operations/__init__.py**

Modify exports to only include new functions and KnitConfig:

```python
"""Operations package with pure functions for git operations."""

from git_knit.operations.config import KnitConfig
from git_knit.operations.config_functions import (
    init_knit,
    add_branch,
    remove_branch,
    get_config,
    list_working_branches,
    resolve_working_branch,
    delete_config,
)
from git_knit.operations.executor_functions import (
    run_git_command,
    get_current_branch,
    branch_exists,
    create_branch,
    checkout,
    delete_branch,
    merge_branch,
    cherry_pick,
    stash_push,
    stash_pop,
    get_commits_between,
    get_merge_base,
    is_ancestor,
    is_merge_commit,
    find_commit,
    get_local_working_branch_commits,
    is_clean_working_tree,
)
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
)

__all__ = [
    "KnitConfig",
    "init_knit",
    "add_branch",
    "remove_branch",
    "get_config",
    "list_working_branches",
    "resolve_working_branch",
    "delete_config",
    "run_git_command",
    "get_current_branch",
    "branch_exists",
    "create_branch",
    "checkout",
    "delete_branch",
    "merge_branch",
    "cherry_pick",
    "stash_push",
    "stash_pop",
    "get_commits_between",
    "get_merge_base",
    "is_ancestor",
    "is_merge_commit",
    "find_commit",
    "get_local_working_branch_commits",
    "is_clean_working_tree",
    "rebuild_working_branch",
    "detect_and_restack",
]
```

**Step 3: Update commands/_shared.py**

Modify `src/git_knit/commands/_shared.py` to use new functions:

```python
"""Shared command utilities."""

import click

from git_knit.operations.config_functions import resolve_working_branch


def resolve_working_branch_param(ctx, param, value):
    """Click callback to resolve working branch from flag or current context."""
    return resolve_working_branch(value)
```

**Step 4: Delete old files**

Run: `rm src/git_knit/operations/executor.py src/git_knit/operations/rebuilder.py src/git_knit/operations/spice_detector.py`

**Step 5: Refactor config.py to only have KnitConfig**

Modify `src/git_knit/operations/config.py`:

```python
"""Knit configuration data structure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnitConfig:
    """Immutable configuration for a knit working branch."""
    working_branch: str
    base_branch: str
    feature_branches: list[str]
```

**Step 6: Run all tests**

Run: `pytest --tb=short -v`
Expected: All 99+ tests pass with improved coverage

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: remove old OOP classes, keep only pure functions"
```

---

## Phase 7: Verify 100% Coverage

### Task 7: Achieve 100% test coverage

**Files:**
- All test files
- All source files

**Step 1: Run tests with coverage report**

Run: `pytest --cov=src/git_knit --cov-report=html`
Expected: Coverage < 100%

**Step 2: Identify missing coverage**

Analyze output to find uncovered lines and branches.

**Step 3: Write additional tests**

Add tests to `tests/` for any uncovered code paths.

**Step 4: Run tests until 100% coverage**

Run: `pytest --tb=short -v`
Expected: All tests pass with 100% coverage

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: achieve 100% coverage for functional refactoring"
```

---

## Summary

This plan systematically converts git-knit from OOP to functional style:

1. **Foundation**: Pure git execution functions in `executor_functions.py`
2. **Config Layer**: Pure config management in `config_functions.py`
3. **Composition**: Higher-order workflow functions in `operations_functions.py`
4. **Commands**: Extracted pure command logic in `commands_logic.py`
5. **CLI**: Thin Click wrappers that call pure functions
6. **Cleanup**: Remove all class-based code except exceptions and `KnitConfig`
7. **Coverage**: Achieve 100% test coverage

All existing behavior is preserved while transforming the codebase to use pure functions instead of classes.
