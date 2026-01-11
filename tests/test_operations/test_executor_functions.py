import pytest
from textwrap import dedent

from pytest_check import check

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
    get_config_value,
    set_config_value,
    unset_config_value,
    list_config_keys,
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
        stdout=""
    )
    create_branch("feature/new", "main")

def test_create_branch_from_current(fake_process):
    """Test creating a new branch from current HEAD"""
    fake_process.register_subprocess(
        ["git", "branch", "feature/new"],
        stdout=""
    )
    create_branch("feature/new")

def test_checkout_branch(fake_process):
    """Test checking out a branch"""
    fake_process.register_subprocess(
        ["git", "checkout", "feature/test"],
        stdout=""
    )
    checkout("feature/test")

def test_delete_branch(fake_process):
    """Test deleting a branch"""
    fake_process.register_subprocess(
        ["git", "branch", "-d", "feature/test"],
        stdout=""
    )
    delete_branch("feature/test", force=False)

def test_delete_branch_force(fake_process):
    """Test force deleting a branch"""
    fake_process.register_subprocess(
        ["git", "branch", "-D", "feature/test"],
        stdout=""
    )
    delete_branch("feature/test", force=True)

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
        stdout="Saved working directory and index state\n"
    )
    stash_push()

    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        stdout=""
    )
    stash_pop()

def test_get_commits_between(fake_process):
    """Test getting commits between two refs"""
    fake_process.register_subprocess(
        ["git", "rev-list", "base..feature"],
        stdout=dedent(
            """\
            abc123
            def456
            """
        ),
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
        stdout=dedent(
            """\
            tree xyz789
            parent abc111
            parent abc222
            author ...
            """
        ),
    )
    assert is_merge_commit("abc123") is True

def test_is_merge_commit_false(fake_process):
    """Test merge commit detection - not merge"""
    fake_process.register_subprocess(
        ["git", "cat-file", "-p", "abc123"],
        stdout=dedent(
            """\
            tree xyz789
            parent abc111
            author ...
            """
        ),
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
    # First, register the failed hash lookup
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "test message^{commit}"],
        returncode=1,
        stdout=""
    )
    # Then register the log search that returns one result
    fake_process.register_subprocess(
        ["git", "log", "--all", "--grep=test message", "--format=%H"],
        stdout="abc123\n"
    )
    # Returns first match
    commit = find_commit("test message")
    assert commit == "abc123"

def test_get_config_value_success(fake_process):
    """Test getting a git config value successfully"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "user.name"],
        stdout="John Doe\n"
    )
    result = get_config_value("user", "name")
    assert result == "John Doe"


def test_get_config_value_not_found(fake_process):
    """Test getting a non-existent config value"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "user.nonexistent"],
        returncode=1,
        stdout=""
    )
    result = get_config_value("user", "nonexistent")
    assert result is None


def test_set_config_value(fake_process):
    """Test setting a git config value"""
    fake_process.register_subprocess(
        ["git", "config", "test.key", "value"],
        stdout=""
    )
    set_config_value("test", "key", "value")


def test_unset_config_value(fake_process):
    """Test unsetting a git config value"""
    fake_process.register_subprocess(
        ["git", "config", "--unset", "test.key"],
        stdout=""
    )
    unset_config_value("test", "key")


def test_list_config_keys_empty(fake_process):
    """Test listing config keys when none exist"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^test\\."],
        returncode=1,
        stdout=""
    )
    result = list_config_keys("test")
    assert result == []


def test_list_config_keys_with_values(fake_process):
    """Test listing config keys with values"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^test\\."],
        stdout=dedent(
            """\
            test.key1 value1
            test.key2 value2
            """
        ),
    )
    result = list_config_keys("test")
    check("key1" in result)
    check("key2" in result)
