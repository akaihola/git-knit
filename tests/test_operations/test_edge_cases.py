"""Edge case tests for full coverage of git-knit operations."""

import pytest
from textwrap import dedent
from pytest_check import check

from git_knit.operations.executor_functions import (
    find_commit,
    get_local_working_branch_commits,
)
from git_knit.operations.config_functions import (
    add_branch,
    remove_branch,
    get_config,
    resolve_working_branch,
    delete_config,
)
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
    get_local_commits,
)
from git_knit.errors import (
    CommitNotFoundError,
    AmbiguousCommitError,
    BranchNotFoundError,
    BranchNotInKnitError,
    WorkingBranchNotSetError,
)


class TestCommitFinding:
    """Test commit finding edge cases."""

    def test_find_commit_not_found(self, fake_process):
        """Test finding commit when it doesn't exist"""
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexistent^{commit}"],
            returncode=1,
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "log", "--all", "--grep=nonexistent", "--format=%H"],
            stdout=""
        )
        with pytest.raises(CommitNotFoundError):
            find_commit("nonexistent")

    def test_find_commit_ambiguous(self, fake_process):
        """Test finding commit when multiple matches exist"""
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "partial^{commit}"],
            returncode=1,
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "log", "--all", "--grep=partial", "--format=%H"],
            stdout="abc123\ndef456\n"
        )
        with pytest.raises(AmbiguousCommitError):
            find_commit("partial")


class TestLocalWorkingBranchCommits:
    """Test getting local commits from working branch."""

    def test_get_local_commits_empty(self, fake_process):
        """Test getting local commits when none exist"""
        # Get commits between base and HEAD
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout=""
        )
        result = get_local_working_branch_commits("main", ["feature/a", "feature/b"])
        assert result == []

    def test_get_local_commits_with_merge_commits(self, fake_process):
        """Test filtering out merge commits from local commits"""
        # Get commits between base and HEAD
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout="abc123\ndef456\n"
        )
        # Check if abc123 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "abc123"],
            stdout=dedent(
                """\
                tree xyz789
                parent abc111
                parent abc222
                author ...
                """
            )
        )
        # Check if def456 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "def456"],
            stdout=dedent(
                """\
                tree xyz789
                parent abc111
                author ...
                """
            )
        )
        # Check if def456 is in feature/a
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "def456", "feature/a"],
            returncode=1
        )
        # Check if def456 is in feature/b
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "def456", "feature/b"],
            returncode=1
        )
        result = get_local_working_branch_commits("main", ["feature/a", "feature/b"])
        assert result == ["def456"]

    def test_get_local_commits_with_feature_commits(self, fake_process):
        """Test filtering out commits that are in feature branches"""
        # Get commits between base and HEAD
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout="abc123\n"
        )
        # Check if abc123 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "abc123"],
            stdout=dedent(
                """\
                tree xyz789
                parent abc111
                author ...
                """
            )
        )
        # Check if abc123 is in feature/a
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "abc123", "feature/a"],
            returncode=0
        )
        result = get_local_working_branch_commits("main", ["feature/a", "feature/b"])
        assert result == []


class TestAddBranchErrors:
    """Test add_branch error cases."""

    def test_add_nonexistent_branch(self, fake_process):
        """Test adding a branch that doesn't exist"""
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "nonexistent"],
            returncode=1,
            stderr="fatal: not a valid object name\n"
        )
        with pytest.raises(BranchNotFoundError):
            add_branch("main-working", "nonexistent")

    def test_add_branch_to_unconfigured_knit(self, fake_process):
        """Test adding a branch to a knit that doesn't exist"""
        fake_process.register_subprocess(
            ["git", "rev-parse", "--verify", "feature/a"],
            stdout=""
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.invalid.base-branch"],
            returncode=1,
            stdout=""
        )
        with pytest.raises(ValueError):
            add_branch("invalid", "feature/a")


class TestRemoveBranchErrors:
    """Test remove_branch error cases."""

    def test_remove_branch_not_in_knit(self, fake_process):
        """Test removing a branch that's not in the knit"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            stdout="feature/a\n"
        )
        with pytest.raises(BranchNotInKnitError):
            remove_branch("main-working", "feature/b")

    def test_remove_branch_from_unconfigured_knit(self, fake_process):
        """Test removing a branch from an unconfigured knit"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.invalid.base-branch"],
            returncode=1,
            stdout=""
        )
        with pytest.raises(ValueError):
            remove_branch("invalid", "feature/a")


class TestConfigEdgeCases:
    """Test config_functions edge cases."""

    def test_delete_unconfigured_knit(self, fake_process):
        """Test deleting a knit that doesn't exist"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.invalid.base-branch"],
            returncode=1,
            stdout=""
        )
        with pytest.raises(ValueError):
            delete_config("invalid")

    def test_resolve_working_branch_not_configured(self, fake_process):
        """Test resolving a working branch that's not configured"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.invalid.base-branch"],
            returncode=1,
            stdout=""
        )
        with pytest.raises(ValueError):
            resolve_working_branch("invalid")

    def test_resolve_working_branch_current_not_configured(self, fake_process):
        """Test resolving from current branch when it's not a knit"""
        fake_process.register_subprocess(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main.base-branch"],
            returncode=1,
            stdout=""
        )
        with pytest.raises(WorkingBranchNotSetError):
            resolve_working_branch(None)

    def test_get_config_with_no_feature_branches(self, fake_process):
        """Test getting config when no feature branches are configured"""
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.base-branch"],
            stdout="main\n"
        )
        fake_process.register_subprocess(
            ["git", "config", "--get", "knit.main-working.feature-branches"],
            returncode=1,
            stdout=""
        )
        config = get_config("main-working")
        assert config is not None
        check(config.working_branch == "main-working")
        check(config.base_branch == "main")
        check(config.feature_branches == ())


class TestOperationsFunctionsErrors:
    """Test operations_functions error handling."""

    def test_rebuild_merge_conflict(self, fake_process):
        """Test rebuild when merge conflict occurs"""
        # Check working tree is clean
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        # Stash push
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        # Try to delete temp branch (doesn't exist)
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            returncode=1,
            stderr="error: branch 'main-working-tmp' not found\n"
        )
        # Create temp branch
        fake_process.register_subprocess(
            ["git", "branch", "main-working-tmp", "main"],
            stdout=""
        )
        # Checkout temp branch
        fake_process.register_subprocess(
            ["git", "checkout", "main-working-tmp"],
            stdout=""
        )
        # Merge feature with conflict
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "feature/a"],
            returncode=1,
            stdout="CONFLICT (content): Merge conflict in file.py\n"
        )
        # Abort merge
        fake_process.register_subprocess(
            ["git", "merge", "--abort"],
            stdout=""
        )
        # Delete temp branch (in finally)
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            returncode=1,
            stderr="error: branch 'main-working-tmp' not found\n"
        )
        # Stash pop (in finally)
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            returncode=1,
            stderr="error: stash not found\n"
        )

        from git_knit.errors import GitConflictError
        with pytest.raises(GitConflictError):
            rebuild_working_branch("main-working", "main", ["feature/a"])

    def test_rebuild_cherry_pick_conflict(self, fake_process):
        """Test rebuild when cherry-pick conflict occurs"""
        # Check working tree is clean
        fake_process.register_subprocess(
            ["git", "status", "--porcelain"],
            stdout=""
        )
        # Stash push
        fake_process.register_subprocess(
            ["git", "stash", "push", "-u"],
            stdout="Saved\n"
        )
        # Try to delete temp branch (doesn't exist)
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            returncode=1,
            stderr="error: branch 'main-working-tmp' not found\n"
        )
        # Create temp branch
        fake_process.register_subprocess(
            ["git", "branch", "main-working-tmp", "main"],
            stdout=""
        )
        # Checkout temp branch
        fake_process.register_subprocess(
            ["git", "checkout", "main-working-tmp"],
            stdout=""
        )
        # Merge feature (success)
        fake_process.register_subprocess(
            ["git", "merge", "--no-ff", "feature/a"],
            stdout="Merge made\n"
        )
        # Get commits between
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout="abc123\n"
        )
        # Check if abc123 is merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "abc123"],
            stdout="tree xyz789\nparent abc111\nauthor ...\n"
        )
        # Check if abc123 is in feature/a
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "abc123", "feature/a"],
            returncode=1
        )
        # Cherry-pick with conflict
        fake_process.register_subprocess(
            ["git", "cherry-pick", "abc123"],
            returncode=1,
            stdout="CONFLICT (content): Cherry-pick conflict\n"
        )
        # Abort cherry-pick
        fake_process.register_subprocess(
            ["git", "cherry-pick", "--abort"],
            stdout=""
        )
        # Delete temp branch (in finally)
        fake_process.register_subprocess(
            ["git", "branch", "-D", "main-working-tmp"],
            returncode=1,
            stderr="error: branch 'main-working-tmp' not found\n"
        )
        # Stash pop (in finally)
        fake_process.register_subprocess(
            ["git", "stash", "pop"],
            returncode=1,
            stderr="error: stash not found\n"
        )

        from git_knit.errors import GitConflictError
        with pytest.raises(GitConflictError):
            rebuild_working_branch("main-working", "main", ["feature/a"])

    def test_detect_and_restack_gs_version_check_fails(self, fake_process):
        """Test detect_and_restack when gs --version fails"""
        # Try "which gs"
        fake_process.register_subprocess(
            "which gs",
            stdout="/usr/local/bin/gs\n"
        )
        # Check version - fails (not git-spice)
        fake_process.register_subprocess(
            "gs --version",
            returncode=1,
            stderr="error\n"
        )
        # Should not raise, just return
        detect_and_restack()


class TestGetLocalCommits:
    """Test get_local_commits function."""

    def test_get_local_commits_mixed_types(self, fake_process):
        """Test filtering mix of merge, feature, and local commits"""
        # Get commits between base and HEAD
        fake_process.register_subprocess(
            ["git", "rev-list", "main..HEAD"],
            stdout="commit1\ncommit2\ncommit3\n"
        )
        # Check if commit1 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "commit1"],
            stdout="tree xyz\nparent a\nparent b\nauthor ...\n"
        )
        # Check if commit2 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "commit2"],
            stdout="tree xyz\nparent a\nauthor ...\n"
        )
        # Check if commit2 is in feature/a
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "commit2", "feature/a"],
            returncode=0
        )
        # Check if commit3 is a merge commit
        fake_process.register_subprocess(
            ["git", "cat-file", "-p", "commit3"],
            stdout="tree xyz\nparent a\nauthor ...\n"
        )
        # Check if commit3 is in feature/a
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "commit3", "feature/a"],
            returncode=1
        )
        # Check if commit3 is in feature/b
        fake_process.register_subprocess(
            ["git", "merge-base", "--is-ancestor", "commit3", "feature/b"],
            returncode=1
        )
        result = get_local_commits("main", ["feature/a", "feature/b"])
        assert result == ["commit3"]
