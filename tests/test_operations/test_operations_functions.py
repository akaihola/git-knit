import pytest
from git_knit.operations.operations_functions import (
    rebuild_working_branch,
    detect_and_restack,
)
from git_knit.errors import GitConflictError, UncommittedChangesError


def test_rebuild_working_branch_requires_clean_tree(fake_process):
    """Test that rebuild fails with uncommitted changes"""
    fake_process.register_subprocess(
        ["git", "status", "--porcelain"],
        stdout="M file.txt\n"
    )

    with pytest.raises(UncommittedChangesError):
        rebuild_working_branch("main-working", "main", ["feature/a"])


def test_rebuild_working_branch_basic(fake_process):
    """Test basic rebuild with no local commits"""
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
    # Merge feature
    fake_process.register_subprocess(
        ["git", "merge", "--no-ff", "feature/a"],
        stdout="Merge made\n"
    )
    # Get commits between
    fake_process.register_subprocess(
        ["git", "rev-list", "main..HEAD"],
        stdout=""
    )
    # Update working branch atomically
    fake_process.register_subprocess(
        ["git", "branch", "-f", "main-working", "main-working-tmp"],
        stdout=""
    )
    # Checkout working branch
    fake_process.register_subprocess(
        ["git", "checkout", "main-working"],
        stdout=""
    )
    # Delete temp branch
    fake_process.register_subprocess(
        ["git", "branch", "-D", "main-working-tmp"],
        stdout=""
    )
    # Stash pop
    fake_process.register_subprocess(
        ["git", "stash", "pop"],
        stdout=""
    )

    rebuild_working_branch("main-working", "main", ["feature/a"])


def test_detect_and_restack_with_gs(fake_process):
    """Test detecting and using git-spice for restacking"""
    # Try "which gs"
    fake_process.register_subprocess(
        "which gs",
        stdout="/usr/local/bin/gs\n"
    )
    # Check version
    fake_process.register_subprocess(
        "gs --version",
        stdout="gs version 0.13.0\n"
    )
    # Run restack (git command)
    fake_process.register_subprocess(
        ["git", "gs", "stack", "restack"],
        stdout=""
    )

    detect_and_restack()


def test_detect_and_restack_without_gs(fake_process):
    """Test detect_and_restack when git-spice not available"""
    # Try "which gs" - not found
    fake_process.register_subprocess(
        "which gs",
        returncode=1,
        stderr="gs: not found\n"
    )

    # Should not raise, just skip
    detect_and_restack()


def test_detect_and_restack_not_git_spice(fake_process):
    """Test detect_and_restack when gs is not git-spice"""
    # Try "which gs" - found (ghostscript)
    fake_process.register_subprocess(
        "which gs",
        stdout="/usr/bin/gs\n"
    )
    # Check version - no git-spice signature
    fake_process.register_subprocess(
        "gs --version",
        stdout="GPL Ghostscript 10.0\n"
    )

    # Should not raise, just skip
    detect_and_restack()
