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


def test_run_always_returns_completed_process(temp_git_repo):
    """Test that run() always returns CompletedProcess, even with capture=False."""
    executor = GitExecutor(cwd=temp_git_repo)
    result = executor.run(["status"], capture=False)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0


def test_get_branch_parent_linear(temp_git_repo):
    executor = GitExecutor(cwd=temp_git_repo)
    assert executor.get_branch_parent("main") is None


def test_get_branch_parent_no_merge_commit(temp_git_repo):
    """Test get_branch_parent when no merge commit found."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.create_branch("feature", "main")
    executor.checkout("feature")
    assert executor.get_branch_parent("feature") is None


def test_get_branch_parent_multiple_merges(temp_git_repo):
    """Test get_branch_parent finds the most recent merge."""
    subprocess.run(["git", "checkout", "-b", "b1"], cwd=temp_git_repo, check=True)
    (temp_git_repo / "b1.txt").write_text("B1 content")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add b1"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    subprocess.run(["git", "checkout", "-b", "b2"], cwd=temp_git_repo, check=True)
    (temp_git_repo / "b2.txt").write_text("B2 content")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add b2"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, check=True)

    executor = GitExecutor(cwd=temp_git_repo)
    executor.create_branch("work", "main")
    executor.checkout("work")

    executor.merge_branch("b1")

    executor.merge_branch("b2")

    parent = executor.get_branch_parent("work")
    assert parent == "b2"


def test_get_branch_parent_fallback_to_sha(temp_git_repo, monkeypatch):
    """Test get_branch_parent falls back to SHA when name-rev fails."""
    executor = GitExecutor(cwd=temp_git_repo)
    executor.create_branch("b1", "main")
    executor.checkout("b1")
    (temp_git_repo / "b1.txt").write_text("b1")
    executor.run(["add", "."])
    executor.run(["commit", "-m", "b1"])
    executor.checkout("main")

    subprocess.run(["git", "merge", "--no-ff", "b1"], cwd=temp_git_repo, check=True)

    original_run = subprocess.run

    def mock_run(args, **kwargs):
        if "name-rev" in args:
            result = type("obj", (), {})()
            result.returncode = 1
            return result
        return original_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    parent = executor.get_branch_parent("main")
    assert parent is not None


class TestGitExecutorListConfigKeys:
    """Test list_config_keys edge cases."""

    def test_list_config_keys_no_output(self, temp_git_repo):
        """Test list_config_keys when config returns no output."""
        executor = GitExecutor(cwd=temp_git_repo)
        keys = executor.list_config_keys("knit.nonexistent")
        assert keys == []

    def test_list_config_keys_with_values(self, temp_git_repo):
        """Test list_config_keys with actual config values."""
        executor = GitExecutor(cwd=temp_git_repo)
        executor.run(["config", "--local", "knit.test.key1", "value1"])
        executor.run(["config", "--local", "knit.test.key2", "value2"])

        keys = executor.list_config_keys("knit.test")
        assert "knit.test.key1" in keys
        assert "knit.test.key2" in keys

    def test_list_config_keys_empty_stdout(self, temp_git_repo, monkeypatch):
        """Test list_config_keys when stdout is empty but command succeeds."""
        executor = GitExecutor(cwd=temp_git_repo)

        original_run = executor.run

        def mock_run(args, **kwargs):
            if "--get-regexp" in args and "empty" in args:
                result = type("obj", (), {})()
                result.returncode = 0
                result.stdout = ""
                return result
            return original_run(args, **kwargs)

        monkeypatch.setattr(executor, "run", mock_run)

        keys = executor.list_config_keys("empty")
        assert keys == []


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

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return subprocess.CompletedProcess(
                    args=["gs", "--help"],
                    returncode=0,
                    stdout="git-spice version 0.1.0",
                    stderr="",
                )
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.detect() == "git-spice"

    def test_detect_ghostscript(self, temp_git_repo, monkeypatch):
        """Test detecting GhostScript (should be ignored)."""
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return subprocess.CompletedProcess(
                    args=["gs", "--help"],
                    returncode=0,
                    stdout="GPL Ghostscript 9.50",
                    stderr="",
                )
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.detect() == "ghostscript"

    def test_detect_not_found(self, temp_git_repo, monkeypatch):
        """Test detecting when gs is not found."""
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.detect() == "not-found"

    def test_restack_if_available_true(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return subprocess.CompletedProcess(
                    args=["gs", "--help"],
                    returncode=0,
                    stdout="git-spice version 0.1.0",
                    stderr="",
                )
            if args[0] == ["gs", "stack", "restack"]:
                return subprocess.CompletedProcess(
                    args=["gs", "stack", "restack"],
                    returncode=0,
                    stdout="",
                    stderr="",
                )
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.restack_if_available() is True

    def test_restack_if_available_false(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                raise FileNotFoundError("gs not found")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.restack_if_available() is False

    def test_restack_if_available_error(self, temp_git_repo, monkeypatch):
        """Test restack returns False when CalledProcessError is raised."""
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return subprocess.CompletedProcess(
                    args=["gs", "--help"],
                    returncode=0,
                    stdout="git-spice version 0.1.0",
                    stderr="",
                )
            if args[0] == ["gs", "stack", "restack"]:
                raise subprocess.CalledProcessError(1, ["gs", "stack", "restack"])
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert detector.restack_if_available() is False

    def test_detect_unknown(self, temp_git_repo, monkeypatch):
        detector = GitSpiceDetector()

        def fake_run(*args, **kwargs):
            if args[0] == ["gs", "--help"]:
                return subprocess.CompletedProcess(
                    args=["gs", "--help"],
                    returncode=0,
                    stdout="some other tool",
                    stderr="",
                )
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
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

    def test_rebuild_with_uncommitted_changes(self, temp_git_repo_with_branches):
        """Test rebuild preserves uncommitted changes."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("b1")

        (repo / "uncommitted.txt").write_text("uncommitted work")

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"))

        assert (repo / "uncommitted.txt").read_text() == "uncommitted work"
        assert executor.get_current_branch() == "work"

    def test_rebuild_with_working_branch_commits(self, temp_git_repo_with_branches):
        """Test rebuild preserves local commits on working branch."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("b1")

        (repo / "local1.txt").write_text("local work 1")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit 1"])

        (repo / "local2.txt").write_text("local work 2")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit 2"])

        log_result = executor.run(["log", "--oneline", "main..work"], capture=True)
        local_commit_count = len(
            [l for l in log_result.stdout.split("\n") if "Local" in l]
        )
        assert local_commit_count == 2

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"))

        log_result = executor.run(["log", "--oneline", "main..work"], capture=True)
        assert "Local commit 1" in log_result.stdout
        assert "Local commit 2" in log_result.stdout

    def test_rebuild_with_both_commits_and_changes(self, temp_git_repo_with_branches):
        """Test rebuild preserves both commits and uncommitted changes."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("b1")

        (repo / "committed.txt").write_text("committed work")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])

        (repo / "uncommitted.txt").write_text("uncommitted work")

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"))

        assert (repo / "committed.txt").read_text() == "committed work"
        assert (repo / "uncommitted.txt").read_text() == "uncommitted work"

    def test_rebuild_excludes_feature_branch_commits(self, temp_git_repo_with_branches):
        """Test rebuild only preserves local commits, not feature branch commits."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("b1")

        log_before = executor.run(["log", "--oneline", "-n", "5"], capture=True).stdout
        assert "Add b1" in log_before

        rebuilder = KnitRebuilder(executor)
        rebuilder.rebuild(manager.get_config("work"))

        log_after = executor.run(["log", "--oneline", "-n", "5"], capture=True).stdout
        assert "Add b1" in log_after

    def test_rebuild_conflict_handling(self, temp_git_repo):
        """Test rebuild leaves conflict state when cherry-pick conflicts."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)

        executor.create_branch("feature", "main")
        executor.checkout("feature")
        (temp_git_repo / "conflict.txt").write_text("line1\nline2\nline3\n")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Add conflict file in feature"])
        executor.checkout("main")

        manager.init_knit("work", "main", ["feature"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("feature")

        (temp_git_repo / "conflict.txt").write_text("line1\nLOCAL MOD\nline3\n")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])

        executor.checkout("feature")
        (temp_git_repo / "conflict.txt").write_text("line1\nFEATURE MOD\nline3\n")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Update conflict file"])
        executor.checkout("main")

        rebuilder = KnitRebuilder(executor)
        config = manager.get_config("work")

        with pytest.raises(GitConflictError, match="Cherry-pick conflict"):
            rebuilder.rebuild(config)

        assert executor.get_current_branch() == "work.rebuilt"
        content = (temp_git_repo / "conflict.txt").read_text()
        assert "<<<<<<" in content

    def test_rebuild_preserves_original_on_conflict(self, temp_git_repo):
        """Test rebuild leaves original branch untouched when conflict occurs."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)

        executor.create_branch("feature", "main")
        executor.checkout("feature")
        (temp_git_repo / "file.txt").write_text("feature content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Feature commit"])
        executor.checkout("main")

        manager.init_knit("work", "main", ["feature"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("feature")

        (temp_git_repo / "file.txt").write_text("local content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])
        local_commit = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()

        executor.checkout("feature")
        (temp_git_repo / "file.txt").write_text("updated feature content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Updated feature"])
        executor.checkout("main")

        rebuilder = KnitRebuilder(executor)
        config = manager.get_config("work")

        with pytest.raises(GitConflictError, match="Cherry-pick conflict"):
            rebuilder.rebuild(config)

        assert executor.branch_exists("work")
        work_tip = executor.run(
            ["rev-parse", "refs/heads/work"], capture=True
        ).stdout.strip()
        assert work_tip == local_commit
        assert executor.get_current_branch() == "work.rebuilt"

    def test_rebuild_creates_and_cleans_backup(self, temp_git_repo):
        """Test rebuild leaves original branch untouched when conflict occurs."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)

        executor.create_branch("feature", "main")
        executor.checkout("feature")
        (temp_git_repo / "file.txt").write_text("feature content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Feature commit"])
        executor.checkout("main")

        manager.init_knit("work", "main", ["feature"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("feature")

        (temp_git_repo / "local.txt").write_text("local content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])
        local_commit = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()

        executor.checkout("feature")
        (temp_git_repo / "file.txt").write_text("updated feature content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Updated feature"])
        executor.checkout("main")

        rebuilder = KnitRebuilder(executor)
        config = manager.get_config("work")

        with pytest.raises(GitConflictError, match="Cherry-pick conflict"):
            rebuilder.rebuild(config)

        assert executor.branch_exists("work")
        work_tip = executor.run(
            ["rev-parse", "refs/heads/work"], capture=True
        ).stdout.strip()
        assert work_tip != local_commit
        assert executor.get_current_branch() == "work.rebuilt"

    def test_rebuild_creates_and_cleans_backup(self, temp_git_repo):
        """Test rebuild creates backup branch and cleans it up on success."""
        executor = GitExecutor(cwd=temp_git_repo)
        manager = KnitConfigManager(executor)

        executor.create_branch("feature", "main")
        executor.checkout("feature")
        (temp_git_repo / "file.txt").write_text("feature content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Feature commit"])
        executor.checkout("main")

        manager.init_knit("work", "main", ["feature"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("feature")

        (temp_git_repo / "local.txt").write_text("local content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])

        rebuilder = KnitRebuilder(executor)
        config = manager.get_config("work")
        rebuilder.rebuild(config)

        assert executor.get_current_branch() == "work"
        assert not executor.branch_exists("work.rebuilt")
        assert not executor.branch_exists("knit/backup/work-")
        assert executor.get_current_branch() == "work"

    def test_stash_operations(self, temp_git_repo):
        """Test stash push and pop operations."""
        executor = GitExecutor(cwd=temp_git_repo)

        (temp_git_repo / "file.txt").write_text("content")
        assert not executor.is_clean_working_tree()

        executor.stash_push("test stash")
        assert executor.is_clean_working_tree()

        (temp_git_repo / "other.txt").write_text("other")
        executor.stash_push("second stash")

        executor.stash_pop()
        assert (temp_git_repo / "other.txt").read_text() == "other"

    def test_get_commits_between(self, temp_git_repo):
        """Test getting commits between two refs."""
        executor = GitExecutor(cwd=temp_git_repo)

        executor.create_branch("feature", "main")
        executor.checkout("feature")
        (temp_git_repo / "f1.txt").write_text("f1")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Feature 1"])
        (temp_git_repo / "f2.txt").write_text("f2")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Feature 2"])

        commits = executor.get_commits_between("main", "feature")
        assert len(commits) == 2
        assert "Feature 1" not in "".join(commits)
        assert "Feature 2" not in "".join(commits)

    def test_is_ancestor(self, temp_git_repo):
        """Test checking if commit is ancestor."""
        executor = GitExecutor(cwd=temp_git_repo)

        (temp_git_repo / "file.txt").write_text("content")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "New commit"])

        commit_hash = executor.run(["rev-parse", "HEAD"], capture=True).stdout.strip()
        assert executor.is_ancestor(commit_hash, "HEAD")
        assert not executor.is_ancestor("HEAD~5", "HEAD")

    def test_get_merge_base(self, temp_git_repo):
        """Test getting merge base."""
        executor = GitExecutor(cwd=temp_git_repo)

        executor.create_branch("branch1", "main")
        executor.checkout("branch1")
        (temp_git_repo / "b1.txt").write_text("b1")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Branch 1"])
        executor.checkout("main")

        executor.create_branch("branch2", "main")
        executor.checkout("branch2")
        (temp_git_repo / "b2.txt").write_text("b2")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Branch 2"])

        merge_base = executor.get_merge_base("branch1", "branch2")
        main_hash = executor.run(["rev-parse", "main"], capture=True).stdout.strip()
        assert merge_base == main_hash

    def test_get_local_working_branch_commits(self, temp_git_repo_with_branches):
        """Test filtering out feature branch commits."""
        repo = temp_git_repo_with_branches["repo"]
        executor = GitExecutor(cwd=repo)
        manager = KnitConfigManager(executor)
        manager.init_knit("work", "main", ["b1"])
        executor.create_branch("work", "main")
        executor.checkout("work")
        executor.merge_branch("b1")

        (repo / "local.txt").write_text("local work")
        executor.run(["add", "."])
        executor.run(["commit", "-m", "Local commit"])

        local_commits = executor.get_local_working_branch_commits(
            "work", "main", ("b1",)
        )
        assert len(local_commits) == 1

        log_result = executor.run(
            ["log", "-n", "1", local_commits[0], "--format=%s"], capture=True
        )
        assert "Local commit" in log_result.stdout
