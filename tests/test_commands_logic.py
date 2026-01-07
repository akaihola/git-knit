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


def test_cmd_init_creates_knit(fake_process):
    """Test init command logic"""
    fake_process.register_subprocess(
        ["git", "branch", "main-working", "main"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.base_branch", "main"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/a"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "config", "knit.main-working.feature_branches", "feature/b"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        stdout="Merge made\n"
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/b"],
        stdout="Merge made\n"
    )

    cmd_init("main-working", "main", ["feature/a", "feature/b"])


def test_cmd_status(fake_process, capsys):
    """Test status command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base_branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        stdout="feature/a\nfeature/b\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base_branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        stdout="feature/a\nfeature/b\n"
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
        ["git", "checkout", "feature/target"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "abc123def456"],
        stdout="Merge made\n"
    )
    # detect_and_restack
    fake_process.register_subprocess(
        "which gs",
        returncode=1,
        stderr="not found\n"
    )
    # get_config for rebuild
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.feature/target.base_branch"],
        returncode=1,
        stdout=""
    )

    cmd_move("feature/target", "abc123")


def test_cmd_rebuild(fake_process):
    """Test rebuild command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base_branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        stdout="feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base_branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        stdout="feature/a\n"
    )
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "stash", "push", "-u"],
        stdout="Saved\n"
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        returncode=1,
        stderr="not found\n"
    )
    fake_process.register_subprocess(
        ["git", "branch", "main-working-tmp", "main"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working-tmp"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        stdout="Merge made\n"
    )
    fake_process.register_subprocess(
        ["git", "rev-list", "main..HEAD"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "branch", "-f", "main-working", "main-working-tmp"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        stdout=""
    )
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        stdout=""
    )

    cmd_rebuild(None)


def test_cmd_restack(fake_process):
    """Test restack command logic"""
    fake_process.register_subprocess(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main-working\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.base_branch"],
        stdout="main\n"
    )
    fake_process.register_subprocess(
        ["git", "config", "--get", "knit.main-working.feature_branches"],
        returncode=1,
        stdout=""
    )
    fake_process.register_subprocess(
        "which gs",
        stdout="/usr/local/bin/gs\n"
    )
    fake_process.register_subprocess(
        "gs --version",
        stdout="gs version 0.13.0\n"
    )
    fake_process.register_subprocess(
        ["git", "gs", "stack", "restack"],
        stdout=""
    )

    cmd_restack(None)
