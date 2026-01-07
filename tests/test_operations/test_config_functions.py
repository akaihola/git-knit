import pytest
from git_knit.operations.config_functions import (
    init_knit,
    add_branch,
    remove_branch,
    get_config,
    list_working_branches,
    resolve_working_branch,
    delete_config,
    _get_section,
)
from git_knit.errors import (
    WorkingBranchNotSetError,
    BranchNotInKnitError,
    AlreadyInKnitError,
)


def test_init_knit_creates_config(fake_process):
    """Test initializing a knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.base-branch", "main"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature-branches", "feature/a"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature-branches", "feature/b"],
        stdout=""
    )

    init_knit("main-working", "main", ["feature/a", "feature/b"])


def test_add_branch_to_knit(fake_process):
    """Test adding a branch to knit"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "feature/c"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature-branches"],
        stdout="feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature-branches", "feature/c"],
        stdout=""
    )

    add_branch("main-working", "feature/c")


def test_add_duplicate_branch_fails(fake_process):
    """Test that adding duplicate branch raises error"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--verify", "feature/a"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature-branches"],
        stdout="feature/a\n"
    )

    with pytest.raises(AlreadyInKnitError):
        add_branch("main-working", "feature/a")


def test_remove_branch_from_knit(fake_process):
    """Test removing a branch from knit"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature-branches"],
        stdout="feature/a\nfeature/b\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset", "knit.main-working.feature-branches"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature-branches", "feature/b"],
        stdout=""
    )

    remove_branch("main-working", "feature/a")


def test_remove_nonexistent_branch_fails(fake_process):
    """Test removing branch not in knit raises error"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature-branches"],
        stdout="feature/a\n"
    )

    with pytest.raises(BranchNotInKnitError):
        remove_branch("main-working", "feature/nonexistent")


def test_get_config_returns_knit_config(fake_process):
    """Test retrieving knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature-branches"],
        stdout="feature/a\nfeature/b\n"
    )

    config = get_config("main-working")
    assert config is not None
    assert config.working_branch == "main-working"
    assert config.base_branch == "main"
    assert config.feature_branches == ("feature/a", "feature/b")


def test_get_config_not_found_returns_none(fake_process):
    """Test retrieving non-existent configuration returns None"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.nonexistent.base-branch"],
        returncode=1,
        stdout=""
    )

    config = get_config("nonexistent")
    assert config is None


def test_list_working_branches(fake_process):
    """Test listing all working branches"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^knit\\."],
        stdout="knit.main-working.base-branch main\nknit.dev-working.base-branch dev\n"
    )

    branches = list_working_branches()
    assert branches == ["dev-working", "main-working"]


def test_resolve_working_branch_explicit(fake_process):
    """Test resolving working branch when explicitly provided"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.my-branch.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.my-branch.feature-branches"],
        returncode=1,
        stdout=""
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
        ["git", "config", "--get", "knit.my-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.my-working.feature-branches"],
        returncode=1,
        stdout=""
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
        ["git", "config", "--get", "knit.random-branch.base-branch"],
        returncode=1,
        stdout=""
    )

    with pytest.raises(WorkingBranchNotSetError):
        resolve_working_branch(None)


def test_delete_config(fake_process):
    """Test deleting a knit configuration"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.my-working.base-branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.my-working.feature-branches"],
        returncode=1,
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset", "knit.my-working.base-branch"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "--unset", "knit.my-working.feature-branches"],
        stdout=""
    )

    delete_config("my-working")


def test_get_section():
    """Test the _get_section helper function"""
    result = _get_section("my-branch")
    assert result == "knit.my-branch"
