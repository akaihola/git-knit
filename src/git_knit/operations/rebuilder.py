"""Rebuild working branches from scratch."""

from git_knit.errors import BranchNotFoundError, GitConflictError
from git_knit.operations.config import KnitConfig
from git_knit.operations.executor import GitExecutor


class KnitRebuilder:
    """Rebuild working branches from scratch."""

    def __init__(self, executor: GitExecutor):
        self.executor = executor

    def rebuild(self, config: KnitConfig, checkout: bool = True) -> None:
        """Safely rebuild working branch while preserving local commits and uncommitted changes.

        Strategy:
        - Stash uncommitted changes if any
        - Create a temporary rebuilt branch from base
        - Merge feature branches into temp
        - Cherry-pick local commits (non-merge commits reachable from working but not from base/features)
        - If all succeed, atomically update working branch to point to temp (branch -f)
        - Restore stash on success
        - On conflict leave temp and backup branch for manual recovery
        """
        current = self.executor.get_current_branch()
        was_on_working = current == config.working_branch

        stash_created = (
            self.executor.stash_push()
            if not self.executor.is_clean_working_tree()
            else False
        )

        backup_branch: str | None = None
        temp_branch = f"{config.working_branch}.rebuilt"

        try:
            saved_local_commits: list[str] = []
            if self.executor.branch_exists(config.working_branch):
                saved_local_commits = self.executor.get_local_working_branch_commits(
                    config.working_branch, config.base_branch, config.feature_branches
                )

                if was_on_working:
                    self.executor.checkout(config.base_branch)

                sha_res = self.executor.run(
                    ["rev-parse", f"refs/heads/{config.working_branch}"],
                    capture=True,
                    check=False,
                )
                if sha_res and sha_res.returncode == 0 and sha_res.stdout.strip():
                    short = sha_res.stdout.strip()[:7]
                    backup_branch = f"knit/backup/{config.working_branch}-{short}"
                    self.executor.create_branch(backup_branch, sha_res.stdout.strip())

            self.executor.create_branch(temp_branch, config.base_branch)
            self.executor.checkout(temp_branch)

            for branch in config.feature_branches:
                if not self.executor.branch_exists(branch):
                    raise BranchNotFoundError(
                        f"Feature branch '{branch}' does not exist"
                    )
                self.executor.merge_branch(branch)

            if saved_local_commits:
                import sys

                print(
                    f"DEBUG: Cherry-picking {len(saved_local_commits)} local commits",
                    file=sys.stderr,
                )
                for commit in saved_local_commits:
                    print(f"DEBUG: Cherry-pick {commit[:8]}", file=sys.stderr)
                    try:
                        self.executor.cherry_pick(commit)
                    except GitConflictError as e:
                        raise GitConflictError(
                            f"Cherry-pick conflict for commit '{commit[:8]}': {e}"
                        )

            self.executor.run(["branch", "-f", config.working_branch, temp_branch])

            if checkout or was_on_working:
                self.executor.checkout(config.working_branch)
            elif self.executor.get_current_branch() == temp_branch:
                self.executor.checkout(config.base_branch)

            if self.executor.branch_exists(temp_branch):
                self.executor.delete_branch(temp_branch, force=True)
            if backup_branch and self.executor.branch_exists(backup_branch):
                self.executor.delete_branch(backup_branch, force=True)

            if stash_created:
                self.executor.stash_pop()

        except GitConflictError:
            raise
        except Exception:
            raise
