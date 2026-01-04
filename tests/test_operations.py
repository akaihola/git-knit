import subprocess

import pytest

from git_knit.errors import (
    AmbiguousCommitError,
    BranchNotFoundError,
    GitConflictError,
    KnitError,
    UncommittedChangesError,
)
from git_knit.operations import (
    GitExecutor,
    GitSpiceDetector,
    KnitConfig,
    KnitConfigManager,
    KnitRebuilder,
)


def test_get_current_branch(temp_git_repo):
    """Test getting current branch name."""
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.get_current_branch() == "main"


def test_is_clean_working_tree_true(temp_git_repo):
    """Test clean working tree detection."""
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.is_clean_working_tree() is True


def test_is_clean_working_tree_false(temp_git_repo):
    """Test dirty working tree detection."""
    (temp_git_repo / "newfile.txt").write_text("uncommitted changes")
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.is_clean_working_tree() is False


def test_ensure_clean_working_tree_success(temp_git_repo):
    """Test ensure clean with clean working tree."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.ensure_clean_working_tree()


def test_ensure_clean_working_tree_failure(temp_git_repo):
    """Test ensure clean with dirty working tree."""
    (temp_git_repo / "newfile.txt").write_text("uncommitted changes")
    executor = GitExecutor(cwd=temp_git_repo)
    with pytest.raises(UncommittedChangesError):
        executor.ensure_clean_working_tree()


def test_branch_exists_true(temp_git_repo_with_branches):
    """Test branch exists detection for existing branch."""
    repo = temp_git_repo_with_branches["repo"]
    executor = GitExecutor(cwd=repo)
    assert executor.branch_exists("b1") is True


def test_branch_exists_false(temp_git_repo):
    """Test branch exists detection for non-existing branch."""
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.branch_exists("nonexistent") is False


def test_create_and_checkout_branch(temp_git_repo):
    """Test creating and checking out a new branch."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.create_branch("test-branch", "main")
    assert executor.branch_exists("test-branch") is True
    executor.checkout("test-branch")
    assert executor.get_current_branch() == "test-branch"


def test_merge_branch(temp_git_repo_with_branches):
    """Test merging a branch."""
    repo = temp_git_repo_with_branches["repo"]
    executor = GitExecutor(cwd=repo)
    executor.create_branch("work", "main")
    executor.checkout("work")
    executor.merge_branch("b1")
    result = executor.run(["log", "--oneline", "-n", "1"], capture=True)
    assert "b1" in result.stdout


def test_get_config(temp_git_repo):
    """Test getting a git config value."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.run(["config", "test.key", "test-value"])
    assert executor.get_config("test.key") == "test-value"


def test_set_config(temp_git_repo):
    """Test setting a git config value."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.set_config("test.key", "test-value")
    assert executor.get_config("test.key") == "test-value"


def test_list_config_keys(temp_git_repo):
    """Test listing config keys with prefix."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.set_config("knit.test.key1", "value1")
    executor.set_config("knit.test.key2", "value2")
    keys = executor.list_config_keys("knit.test")
    assert set(keys) == {"knit.test.key1", "knit.test.key2"}


def test_merge_conflict(temp_git_repo_with_branches):
    repo = temp_git_repo_with_branches["repo"]
    executor = GitExecutor(cwd=repo)
    executor.create_branch("work", "main")
    executor.checkout("work")

    # Create a base commit on work
    (repo / "file1.txt").write_text("base")
    executor.run(["add", "file1.txt"])
    executor.run(["commit", "-m", "base"])

    executor.create_branch("other", "work")

    # Change file on work
    (repo / "file1.txt").write_text("work change")
    executor.run(["add", "file1.txt"])
    executor.run(["commit", "-m", "work commit"])

    # Change same file on other
    executor.checkout("other")
    (repo / "file1.txt").write_text("other change")
    executor.run(["add", "file1.txt"])
    executor.run(["commit", "-m", "other commit"])

    executor.checkout("work")
    with pytest.raises(GitConflictError):
        executor.merge_branch("other")


def test_get_branch_parent(temp_git_repo_with_branches):
    repo = temp_git_repo_with_branches["repo"]
    executor = GitExecutor(cwd=repo)
    executor.create_branch("work", "main")
    executor.checkout("work")
    executor.merge_branch("b1")
    parent = executor.get_branch_parent(executor.get_current_branch())
    assert parent == "b1"


def test_cherry_pick(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    (temp_git_repo / "cp.txt").write_text("cp content")
    executor.run(["add", "cp.txt"])
    executor.run(["commit", "-m", "cp commit"])
    commit_hash = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()

    executor.create_branch("other", "main~1")
    executor.checkout("other")
    executor.cherry_pick(commit_hash)
    assert (temp_git_repo / "cp.txt").exists()


def test_cherry_pick_conflict(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    (temp_git_repo / "file.txt").write_text("base")
    executor.run(["add", "file.txt"])
    executor.run(["commit", "-m", "base"])

    (temp_git_repo / "file.txt").write_text("cp change")
    executor.run(["add", "file.txt"])
    executor.run(["commit", "-m", "cp commit"])
    commit_hash = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()

    executor.run(["reset", "--hard", "HEAD~1"])
    (temp_git_repo / "file.txt").write_text("local change")
    executor.run(["add", "file.txt"])
    executor.run(["commit", "-m", "local commit"])

    with pytest.raises(GitConflictError):
        executor.cherry_pick(commit_hash)


def test_find_commit(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    (temp_git_repo / "find.txt").write_text("content")
    executor.run(["add", "find.txt"])
    executor.run(["commit", "-m", "target message"])
    commit_hash = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()

    assert executor.find_commit("HEAD") == commit_hash
    assert executor.find_commit("target", message=True) == commit_hash

    with pytest.raises(KnitError):
        executor.find_commit("nonexistent", message=True)


def test_find_commit_ambiguous(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    executor.run(["commit", "--allow-empty", "-m", "ambiguous"])
    executor.run(["commit", "--allow-empty", "-m", "ambiguous"])

    with pytest.raises(AmbiguousCommitError):
        executor.find_commit("ambiguous", message=True)


def test_delete_branch(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    executor.create_branch("to-delete", "main")
    assert executor.branch_exists("to-delete")
    executor.delete_branch("to-delete")
    assert not executor.branch_exists("to-delete")


def test_unset_config(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    executor.set_config("test.unset", "value")
    executor.unset_config("test.unset")
    with pytest.raises(KnitError):
        executor.get_config("test.unset")


def test_get_branch_parent_linear(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.get_branch_parent("main") is None


class TestKnitConfig:
    """Test KnitConfig dataclass."""

    def test_serialize_via_manager(self, temp_git_repo):
        """Test serialization via manager."""
        config = KnitConfig(
            working_branch="work",
            base_branch="main",
            feature_branches=("b1", "b2", "b3"),
        )
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        serialized = manager._serialize_config(config)
        assert serialized == "work:main:b1:b2:b3"

    def test_parse_via_manager(self, temp_git_repo):
        """Test parsing via manager."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        config = manager._parse_config("work:main:b1:b2:b3")
        assert config.working_branch == "work"
        assert config.base_branch == "main"
        assert config.feature_branches == ("b1", "b2", "b3")

    def test_parse_empty(self, temp_git_repo):
        """Test parsing with no feature branches."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        config = manager._parse_config("work:main:")
        assert config.working_branch == "work"
        assert config.base_branch == "main"
        assert config.feature_branches == ()


class TestKnitConfigManager:
    """Test KnitConfigManager."""

    def test_init_knit(self, temp_git_repo):
        """Test initializing a new knit configuration."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1", "b2"])
        config = manager.get_config("work")
        assert config.base_branch == "main"
        assert config.feature_branches == ("b1", "b2")

    def test_add_branch(self, temp_git_repo):
        """Test adding a branch to knit."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        manager.add_branch("work", "b2")
        config = manager.get_config("work")
        assert config.feature_branches == ("b1", "b2")

    def test_remove_branch(self, temp_git_repo):
        """Test removing a branch from knit."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1", "b2", "b3"])
        manager.remove_branch("work", "b2")
        config = manager.get_config("work")
        assert config.feature_branches == ("b1", "b3")

    def test_list_working_branches(self, temp_git_repo):
        """Test listing all working branches."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work1", "main", ["b1"])
        manager.init_knit("work2", "main", ["b2"])
        branches = manager.list_working_branches()
        assert set(branches) == {"work1", "work2"}

    def test_is_initialized_true(self, temp_git_repo):
        """Test is initialized returns True when knit exists."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        assert manager.is_initialized() is True

    def test_is_initialized_false(self, temp_git_repo):
        """Test is initialized returns False when no knit exists."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        assert manager.is_initialized() is False

    def test_resolve_working_branch_explicit(self, temp_git_repo):
        """Test resolving working branch with explicit value."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        assert manager.resolve_working_branch("work") == "work"

    def test_resolve_working_branch_from_current(self, temp_git_repo_with_branches):
        """Test resolving working branch from current branch."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        assert manager.resolve_working_branch(None) == "work"

    def test_resolve_working_branch_not_knit(self, temp_git_repo):
        """Test resolve raises error when current branch is not a knit."""
        from git_knit.errors import KnitError

        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        with pytest.raises(KnitError):
            manager.resolve_working_branch(None)


class TestGitSpiceDetector:
    """Test GitSpiceDetector."""

    def test_detect_git_spice(self, temp_git_repo, monkeypatch):
        """Test detecting git-spice (mocked)."""
        detector = GitSpiceDetector()

        class FakeProcess:
            def __init__(self, stdout: str):
                self.stdout = stdout
                self.stderr = ""
                self.returncode = 0

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return FakeProcess("git-spice version 0.1.0")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.detect() == "git-spice"

    def test_detect_ghostscript(self, temp_git_repo, monkeypatch):
        """Test detecting GhostScript (should be ignored)."""
        detector = GitSpiceDetector()

        class FakeProcess:
            def __init__(self, stdout: str):
                self.stdout = stdout
                self.stderr = ""
                self.returncode = 0

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return FakeProcess("GPL Ghostscript 9.50")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.detect() == "ghostscript"

    def test_detect_not_found(self, temp_git_repo, monkeypatch):
        """Test detecting when gs is not found."""
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.detect() == "not-found"

    def test_detect_ghostscript(self, temp_git_repo, monkeypatch):
        """Test detecting GhostScript (should be ignored)."""
        detector = GitSpiceDetector()

        class FakeProcess:
            def __init__(self, stdout: str):
                self.stdout = stdout
                self.stderr = ""
                self.returncode = 0

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return FakeProcess("GPL Ghostscript 9.50")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.detect() == "ghostscript"

    def test_detect_not_found(self, temp_git_repo, monkeypatch):
        """Test detecting when gs is not found."""
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return subprocess.run(*args, **kwargs)

    def test_restack_if_available_true(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        class FakeProcess:
            def __init__(self):
                self.stdout = "git-spice version 0.1.0"
                self.returncode = 0

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return FakeProcess()
            if args[0] == ["gs", "stack", "restack"]:
                return FakeProcess()
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.restack_if_available() is True

    def test_restack_if_available_false(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr("subprocess.run", fake_run)
        assert detector.restack_if_available() is False

    def test_detect_unknown(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        class FakeProcess:
            def __init__(self):
                self.stdout = "some other tool"
                self.returncode = 0

        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeProcess())
        assert detector.detect() == "unknown"


class TestKnitConfigManagerExtra:
    def test_parse_config_invalid(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        with pytest.raises(KnitError, match="Invalid config format"):
            manager._parse_config("only_one_part")

    def test_add_branch_duplicate(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        with pytest.raises(KnitError, match="already in the knit"):
            manager.add_branch("work", "b1")

    def test_remove_branch_not_found(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        with pytest.raises(BranchNotFoundError):
            manager.remove_branch("work", "nonexistent")

    def test_get_config_no_knit(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        with pytest.raises(KnitError, match="No knit configured"):
            manager.get_config("nonexistent")

    def test_resolve_working_branch_explicit_not_configured(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        with pytest.raises(KnitError, match="not configured"):
            manager.resolve_working_branch("nonexistent")

    def test_resolve_working_branch_single_fallback(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        assert manager.resolve_working_branch(None) == "work"

    def test_delete_config(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        manager.delete_config("work")
        assert not manager.is_initialized()


class TestKnitRebuilderExtra:
    def test_rebuild_missing_feature_branch(self, temp_git_repo):
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["nonexistent"])
        rebuilder = KnitRebuilder(executor)
        config = manager.get_config("work")
        with pytest.raises(BranchNotFoundError):
            rebuilder.rebuild(config)

    def test_rebuild_not_on_working_no_checkout(self, temp_git_repo_with_branches):
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("main")

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"), checkout=False)
        assert executor.get_current_branch() == "main"

    """Test KnitRebuilder."""

    def test_rebuild(self, temp_git_repo_with_branches):
        """Test rebuilding a working branch."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1", "b2"])
        executor.create_branch("work", "main")
        executor.checkout("work")

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"), checkout=False)

        assert executor.get_current_branch() == "work"
        result = executor.run(["log", "--oneline"], capture=True)
        assert "Add b1" in result.stdout or "Add b2" in result.stdout
