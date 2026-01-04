"""Custom exceptions for git-knit."""


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


class BranchNotFoundError(KnitError):
    """Raised when a branch does not exist."""

    pass


class BranchNotInKnitError(KnitError):
    """Raised when a branch is not part of a knit."""

    pass


class AlreadyInKnitError(KnitError):
    """Raised when a branch is already in the knit."""

    pass


class WorkingBranchNotSetError(KnitError):
    """Raised when working branch cannot be determined."""

    pass


class CommitNotFoundError(KnitError):
    """Raised when a commit reference cannot be found."""

    pass


class AmbiguousCommitError(KnitError):
    """Raised when a commit reference matches multiple commits."""

    pass
