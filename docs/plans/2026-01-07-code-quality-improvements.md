# Code Quality Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve code quality, test coverage, and adherence to Python best practices across the functional refactoring.

**Architecture:**
- Modernize test fixtures to use real git repos in temp directories
- Refactor tests to use shlex.split() for readability and pytest-check for multi-assertions
- Fix type annotations (Optional vs None return types, tuple vs list for immutable fields)
- Remove unused variables and imports
- Enable and achieve 100% test coverage across all modules
- Unskip CLI integration tests by setting them up properly

**Tech Stack:** pytest, pytest-check, shlex, textwrap, ruff, ty (mypy), Python 3.10+ type hints

---

## Task 1: Add pytest-check and refactor test assertions

**Files:**
- Modify: `pyproject.toml` - add pytest-check dependency
- Modify: `tests/test_coverage_gaps.py` - use pytest-check for multi-assertions
- Modify: `tests/test_commands_logic.py` - use pytest-check for multi-assertions
- Modify: `tests/test_cli_commands.py` - use shlex.split() and refactor

**Step 1: Review pytest.toml for dependencies**

Run: `grep -A 10 "\[project\]" pyproject.toml`

Expected: Shows current dependencies section

**Step 2: Add pytest-check to dependencies**

Read the pyproject.toml file and add "pytest-check" to the dev dependencies if not present.

**Step 3: Update test_coverage_gaps.py for pytest-check**

Replace separate assert statements with single function calls using pytest-check pattern:

```python
from pytest_check import check

def test_list_config_keys_with_values(fake_process):
    """Test listing config keys with values"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^test\\."],
        stdout="test.key1 value1\ntest.key2 value2\n"
    )
    result = list_config_keys("test")
    check("key1" in result)
    check("key2" in result)
```

**Step 4: Update test_commands_logic.py for pytest-check**

Find multi-assert tests and convert to use pytest-check:

```python
from pytest_check import check

def test_cmd_status(fake_process):
    """Test status command"""
    # ... setup ...
    cmd_status("work")
    # Use check() instead of multiple asserts
    check(fake_process.call_count >= 1)
```

**Step 5: Update test_cli_commands.py for shlex.split()**

Import shlex and refactor runner.invoke calls:

```python
from shlex import split
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(cli, split("init main-working main b1 b2"))
assert result.exit_code == 0
```

**Step 6: Run tests to verify**

Run: `pytest tests/test_coverage_gaps.py tests/test_commands_logic.py tests/test_cli_commands.py -v`

Expected: All pass with pytest-check integration working

**Step 6b: Run ruff check on modified test files**

Run: `ruff check tests/test_coverage_gaps.py tests/test_commands_logic.py tests/test_cli_commands.py --fix`

Expected: Any auto-fixable issues resolved

**Step 7: Commit**

```bash
git add pyproject.toml tests/test_coverage_gaps.py tests/test_commands_logic.py tests/test_cli_commands.py
git commit -m "test: refactor assertions to use pytest-check and shlex.split()"
```

---

## Task 2: Fix type annotations for KnitConfig and Optional returns

**Files:**
- Modify: `src/git_knit/operations/config.py` - change feature_branches to tuple
- Modify: `src/git_knit/operations/config_functions.py` - return None instead of Optional, fix type issues
- Modify: `src/git_knit/commands_logic.py` - update to match new types

**Step 1: Update KnitConfig to use tuple for immutability**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class KnitConfig:
    """Immutable configuration for a knit working branch."""

    working_branch: str
    base_branch: str
    feature_branches: tuple[str, ...]
```

Rationale: Frozen dataclass with tuple enforces immutability better than list.

**Step 2: Run the config.py update**

Just modify the file per Step 1.

**Step 3: Update config_functions.py - get_config return type**

Change return type from `Optional[KnitConfig]` to use direct None comparison.
Update constructors to pass tuple instead of list:

```python
def get_config(working_branch: str) -> KnitConfig | None:
    """Retrieve the knit configuration for a working branch."""
    section = _get_section(working_branch)

    base_branch = get_config_value(section, "base_branch")
    if base_branch is None:
        return None

    feature_branches_str = get_config_value(section, "feature_branches")
    feature_branches_list = [
        fb.strip()
        for fb in (feature_branches_str or "").split("\n")
        if fb.strip()
    ]

    return KnitConfig(
        working_branch=working_branch,
        base_branch=base_branch,
        feature_branches=tuple(feature_branches_list),
    )
```

**Step 4: Update all callers of get_config**

Search for patterns like `config.feature_branches` and ensure they work with tuple.
Most iteration patterns (for loops) work with both list and tuple, so minimal changes needed.

Pattern: `for branch in config.feature_branches:` works with tuple as-is.

**Step 5: Update test fixtures to use tuple**

In conftest.py and test files, when creating KnitConfig directly, use tuple:

```python
config = KnitConfig(
    working_branch="work",
    base_branch="main",
    feature_branches=("b1", "b2")  # tuple instead of list
)
```

**Step 6: Run tests to verify**

Run: `pytest tests/ -v`

Expected: All tests pass with new type annotations

**Step 7: Commit**

```bash
git add src/git_knit/operations/config.py src/git_knit/operations/config_functions.py tests/
git commit -m "fix: use KnitConfig.feature_branches as tuple for immutability"
```

---

## Task 3: Remove unused variables and imports

**Files:**
- Modify: `src/git_knit/commands_logic.py` - remove unused `config` variables
- Modify: `tests/test_coverage_gaps.py` - remove unused imports
- Modify: `tests/conftest.py` - remove unused imports

**Step 1: Identify unused variables in commands_logic.py**

Read the file and find patterns like:
```python
config = get_config(wb)  # This variable is never used
```

In cmd_add, cmd_remove: config is retrieved but only used to access feature_branches later.

**Step 2: Remove unused config variables**

```python
def cmd_add(working_branch: Optional[str], branch: str) -> None:
    """Add a branch to a knit."""
    wb = resolve_working_branch(working_branch)

    add_branch(wb, branch)  # config not needed, add_branch checks internally

    checkout(wb)
    merge_branch(branch)
```

**Step 3: Check test_coverage_gaps.py for unused imports**

Look for imports that aren't used. Keep only what's needed.

**Step 4: Check conftest.py for unused imports**

Remove imports like CliRunner if not used in fixtures.

**Step 5: Run tests to verify**

Run: `pytest tests/ -v`

Expected: All pass, no warnings about unused variables

**Step 6: Run linter check with ruff**

Run: `ruff check src/git_knit/commands_logic.py tests/test_coverage_gaps.py tests/conftest.py --fix`

Expected: Auto-fixes applied for any issues

**Step 7: Run ruff check again to verify**

Run: `ruff check src/git_knit/commands_logic.py tests/test_coverage_gaps.py tests/conftest.py`

Expected: No remaining issues

**Step 8: Commit**

```bash
git add src/git_knit/commands_logic.py tests/test_coverage_gaps.py tests/conftest.py
git commit -m "refactor: remove unused variables and imports"
```

---

## Task 4: Create real git repo integration tests and unskip CLI tests

**Files:**
- Modify: `tests/conftest.py` - enhance temp_git_repo and temp_knit_repo fixtures
- Modify: `tests/test_cli_commands.py` - unskip tests and refactor to use real repos

**Step 1: Enhance temp_git_repo fixture to create b3 branch**

Add to conftest.py temp_git_repo fixture (after creating main):

```python
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
    subprocess.run(
        ["git", "config", "rerere.enabled", "false"], cwd=tmp_path, check=True
    )

    (tmp_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run([git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

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
```

**Step 2: Update temp_git_repo_with_branches fixture**

Ensure it also creates the full test setup needed for CLI tests.

**Step 3: Create dedicated temp_knit_repo_for_cli fixture**

```python
@pytest.fixture
def temp_knit_repo_for_cli(temp_git_repo: Path) -> Path:
    """Create a temporary repo with knit configured for CLI testing."""
    # Create branches b1, b2
    for branch in ["b1", "b2"]:
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_git_repo, check=True)
        (temp_git_repo / f"{branch}.txt").write_text(f"Content for {branch}")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run([
            "git", "commit", "-m", f"Add {branch}"
        ], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    # Initialize knit using CLI
    from git_knit.operations.config_functions import init_knit
    from git_knit.operations.executor_functions import create_branch, checkout

    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_git_repo)
        init_knit("work", "main", ["b1", "b2"])
        create_branch("work", "main")
        checkout("work")
    finally:
        os.chdir(orig_cwd)

    return temp_git_repo
```

**Step 4: Refactor test_init_command to use real repo**

```python
def test_init_command(temp_git_repo: Path):
    """Test init command through CLI"""
    runner = CliRunner()

    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_git_repo)
        result = runner.invoke(cli, split("init work main b1 b2"))
        assert result.exit_code == 0
    finally:
        os.chdir(orig_cwd)
```

**Step 5: Refactor test_add_command to use real repo**

```python
def test_add_command(temp_knit_repo_for_cli: Path):
    """Test add command through CLI"""
    runner = CliRunner()

    # First create b3 if not exists
    import subprocess
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        subprocess.run(["git", "checkout", "-b", "b3"], check=False)
        (temp_knit_repo_for_cli / "b3.txt").write_text("Content for b3")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add b3"], check=True)
        subprocess.run(["git", "checkout", "work"], check=True)

        result = runner.invoke(cli, split("add -w work b3"))
        assert result.exit_code == 0
    finally:
        os.chdir(orig_cwd)
```

**Step 6: Remove @pytest.mark.skip from all CLI tests**

Replace the skip decorators with proper implementation using the fixtures.

**Step 7: Run tests to verify**

Run: `pytest tests/test_cli_commands.py -v`

Expected: All 5 tests pass (no skips)

**Step 8: Commit**

```bash
git add tests/conftest.py tests/test_cli_commands.py
git commit -m "test: unskip CLI integration tests with real git repos"
```

---

## Task 5: Improve multiline strings readability

**Files:**
- Modify: `tests/test_operations/test_executor_functions.py` - use textwrap.dedent where needed
- Modify: `tests/test_operations/test_config_functions.py` - use textwrap.dedent where needed

**Step 1: Identify multiline strings in executor_functions tests**

Look for patterns with `\n` in the middle of strings in stdout:

```python
fake_process.register_subprocess(
    ["git", "log", "--oneline"],
    stdout="abc123 Commit 1\ndef456 Commit 2\n"  # Hard to read
)
```

**Step 2: Refactor using textwrap.dedent**

```python
from textwrap import dedent

def test_some_test(fake_process):
    """Test description"""
    fake_process.register_subprocess(
        ["git", "log", "--oneline"],
        stdout=dedent(
            """\
            abc123 Commit 1
            def456 Commit 2
            """
        )
    )
```

**Step 3: Apply to all test files with multiline output**

Search for `\n` patterns in test files and convert appropriate ones.

**Step 4: Run tests to verify**

Run: `pytest tests/test_operations/ -v`

Expected: All pass, output is more readable in source

**Step 5: Commit**

```bash
git add tests/test_operations/test_executor_functions.py tests/test_operations/test_config_functions.py
git commit -m "test: improve multiline string readability with textwrap.dedent()"
```

---

## Task 6: Achieve 100% test coverage

**Files:**
- Modify: `tests/test_cli_commands.py` - add assertions to verify output
- Modify: `tests/test_operations/test_executor_functions.py` - cover missed lines
- Modify: `tests/test_operations/test_operations_functions.py` - cover missed lines
- Create: `tests/test_operations/test_edge_cases.py` - new edge case tests

**Step 1: Run coverage report with detailed output**

Run: `pytest --cov=src/git_knit --cov-report=term-missing tests/ -v`

Expected: Shows exactly which lines are not covered

**Step 2: Add tests for uncovered executor_functions.py lines**

Review coverage report for executor_functions.py lines 167, 169, 182-200, 250.

For each uncovered line, write a test. Example:

```python
def test_merge_branch_with_conflict(fake_process):
    """Test merge conflict detection"""
    fake_process.register_subprocess(
        ["git", "merge", "feature"],
        returncode=1,
        stdout="CONFLICT (content): Merge conflict in file.py\n"
    )
    with pytest.raises(GitConflictError):
        merge_branch("feature")
```

**Step 3: Add tests for uncovered operations_functions.py lines**

Cover lines 72-75, 80-84, 94-95, 100-101, 111-122, 152.

Example for git-spice detection:

```python
def test_detect_and_restack_no_spice(fake_process):
    """Test detect_and_restack when git-spice not installed"""
    # Register subprocess.run to return command not found
    with pytest.raises(Exception):  # Or handle as needed
        detect_and_restack()
```

**Step 4: Add complete assertions to CLI tests**

Update CLI tests to verify not just exit code but also output:

```python
def test_status_command(temp_knit_repo_for_cli: Path):
    """Test status command through CLI"""
    runner = CliRunner()
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(temp_knit_repo_for_cli)
        result = runner.invoke(cli, split("status -w work"))
        assert result.exit_code == 0
        check("work" in result.output)
        check("main" in result.output)
        check("Feature branches:" in result.output)
    finally:
        os.chdir(orig_cwd)
```

**Step 5: Create test_edge_cases.py for corner cases**

```python
"""Edge case tests for full coverage."""

def test_list_working_branches_empty():
    """Test listing branches when none configured"""
    # Mock list_config_keys to return empty
    result = list_working_branches()
    assert result == []
```

**Step 6: Run full coverage report**

Run: `pytest --cov=src/git_knit --cov-report=term-missing tests/ -v`

Expected: Total coverage 100%

**Step 7: Commit**

```bash
git add tests/test_operations/test_executor_functions.py tests/test_operations/test_operations_functions.py tests/test_cli_commands.py tests/test_operations/test_edge_cases.py
git commit -m "test: achieve 100% code coverage"
```

---

## Task 7: Type checking and code quality validation

**Files:**
- All Python files in src/ and tests/

**Step 1: Run type checking with ty (mypy)**

Run: `ty check src/git_knit/operations/config.py src/git_knit/operations/config_functions.py src/git_knit/commands_logic.py`

Expected: No type errors (should be clean after Task 2)

**Step 2: Run linting with ruff**

Run: `ruff check src/ tests/ --fix`

Expected: Auto-fixes applied for auto-fixable issues

**Step 3: Verify linting results**

Run: `ruff check src/ tests/`

Expected: No issues (or only non-auto-fixable ones that are acceptable)

**Step 4: Run full test suite**

Run: `pytest tests/ -v`

Expected: All tests still pass after linting

**Step 5: Review any remaining issues**

Review ruff output for any issues that need manual fixes.

**Step 6: Commit formatting changes**

```bash
git add src/ tests/ pyproject.toml
git commit -m "chore: apply ruff linting and ty type checking"
```

---

## Final Verification

After all tasks complete:

Run: `pytest tests/ -v --cov=src/git_knit --cov-report=term`

Expected output should show:
```
51 passed (or more if new tests added)
0 skipped (or only skipped if intentional)
100% coverage
```

Then create a final summary commit if needed:

```bash
git log --oneline -7  # Show last 7 commits
```
