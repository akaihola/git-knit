# git-knit: Merged Branch Workflow Tool

## Table of Contents

- [Overview](#overview)
- [Motivation](#motivation)
- [Concept](#concept)
- [Metadata Storage](#metadata-storage)
- [Command Reference](#command-reference)
- [Usage Examples](#usage-examples)
- [Implementation Details](#implementation-details)
- [Edge Cases](#edge-cases)

---

## Overview

`git knit` enables a development workflow where multiple feature branches are merged into working branches, allowing you to work on all changes simultaneously. You can have multiple working branches, each merging different sets of feature branches. Commits made in a working branch can then be routed back to their originating feature branches, with automatic reconstruction of the merged view.

---

## Motivation

When working on a set of stacked PRs (e.g., `b1`, `b2`, `b3`), developers often need to:

1. See and test all changes together (merged view)
2. Make changes that logically belong to a specific feature branch
3. Have those changes automatically applied to that branch
4. Quickly refresh the merged view to see all changes together

Current Git workflows require manual cherry-picking and branch reconstruction for each commit. This tool automates this process.

---

## Concept

### Core Workflow

```
main (base)
  ├─ b1 (feature branch 1)
  ├─ b2 (feature branch 2)  # may depend on b1 or be independent
  └─ b3 (feature branch 3)  # may depend on b1/b2 or be independent

w = main + merge(b1) + merge(b2) + merge(b3)
```

> Note: Feature branches (`b1`, `b2`, `b3`) may or may not be stacked. For example:
>
> - `b1` and `b2` could both branch from `main` independently
> - `b2` could branch from `b1` (main→b1→b2) while `b3` branches from `main`
> - The knit merges all branches into a unified view regardless of their relationship

1. User works on branch `w` (the merged view)
2. User runs `git knit move b2` (to move a commit from w to b2)
3. Tool:
   - Cherry-picks HEAD commit from `w` to `b2`
   - Optionally restacks dependent branches (e.g., `b3`) using [git-spice]
   - Rebuilds `w` by resetting to base and re-merging all branches
4. User continues working on `w` with all changes visible

### Multiple Working Branches

You can have multiple working branches, each with their own set of feature branches:

```
develop (base)
  ├─ feature-a (feature branch)
  └─ feature-b (feature branch)

w1 = develop + merge(feature-a) + merge(feature-b)
w2 = develop + merge(feature-a)
```

This allows you to maintain different working contexts, such as:

- A full-stacked knit with all feature branches merged
- A partial knit with only specific features
- Separate knits for different base branches (e.g., `main` vs `develop`)

### Key Principles

- **Multiple Working Branches**: Support for multiple working branches per repository
- **Context Inference**: When a working branch is checked out, commands automatically target that knit
- **Explicit Target**: Commands can target a specific working branch via `--working-branch` flag
- **Commit Routing**: Each commit is explicitly routed to a target branch in the knit
- **Automatic Reconstruction**: The merged view is automatically rebuilt after each routed commit
- **Conflict Reuse**: Leverages [`git rerere`](https://git-scm.com/book/en/v2/Git-Tools-Rerere) to remember and replay conflict resolutions
- **Optional git-spice**: Supports `git-spice restack` if available, gracefully degrades if not

---

## Metadata Storage

### Git Config Section

All metadata is stored in the [local Git configuration] under the `knit` section, with each working branch namespaced separately:

```ini
[knit "w"]
    baseBranch = main
    branches = b1:b2:b3

[knit "work"]
    baseBranch = develop
    branches = feature-a:feature-b
```

### Config Keys

| Key                                | Description                                            | Example           |
| ---------------------------------- | ------------------------------------------------------ | ----------------- |
| `knit.<working-branch>.baseBranch` | Base branch for this working branch                    | `main`, `develop` |
| `knit.<working-branch>.branches`   | Colon-separated list of feature branches for this knit | `b1:b2:b3`        |

### Configuration Commands

```bash
# Read all working branches
git config --local --get-regexp '^knit\..*\.baseBranch'

# Read metadata for a specific working branch
git config --local --get knit.w.baseBranch
git config --local --get knit.w.branches

# Write metadata
git config --local knit.w.baseBranch "main"
git config --local knit.w.branches "b1:b2:b3"

# Delete a working branch's metadata
git config --local --remove-section knit.w

# Check if knit is initialized (any working branches exist)
git config --local --get-regexp '^knit\..*\.baseBranch' >/dev/null
```

### Rationale for Git Config

- **Native to Git**: No external files or dependencies
- **Persistent**: Travels with the repository (in `.git/config`)
- **Script-friendly**: Easy to read/write from shell
- **Namespace-safe**: Uses `knit.` prefix to avoid conflicts
- **Multi-knit support**: Subsections allow multiple independent knits
- **No working directory pollution**: Metadata lives in `.git/`, not project root

---

## Command Reference

### `git knit init <working-branch> <base-branch> [branch...]`

Initialize a new knit configuration.

**Arguments:**

- `working-branch`: Name for the merged working branch (e.g., `w`)
- `base-branch`: Base branch (e.g., `main`)
- `branch...`: Zero or more feature branches to include in knit

**Behavior:**

1. Validate that `base-branch` exists
2. Create `working-branch` from `base-branch` if it doesn't exist
3. Store metadata in Git config
4. Merge all specified branches into `working-branch` (if any provided)
5. Check out `working-branch`

**Error Conditions:**

- Knit already initialized in this repository
- `base-branch` does not exist
- `working-branch` is the current branch (would create circular dependency)

**Example:**

```bash
git knit init w main b1 b2 b3
# Creates: w = main + merge(b1) + merge(b2) + merge(b3)
```

---

### `git knit add <branch> [--working-branch <name>]`

Add a feature branch to the knit.

**Arguments:**

- `branch`: Feature branch to add
- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. Verify knit is initialized
2. Determine target working branch:
   - If `--working-branch` specified, use that
   - If on a working branch (checked out), use that
   - Otherwise error
3. Verify working branch is not checked out if specified explicitly and different from current branch
4. Validate that `branch` exists
5. Check `branch` is not already in the knit
6. Append `branch` to `knit.<working-branch>.branches` config
7. Switch to working branch (if not already there)
8. Merge `branch` into working branch

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Working branch not found in knit metadata
- Branch does not exist
- Branch already in knit

**Example:**

```bash
# On working branch w
git knit add b4
# Now knit = b1:b2:b3:b4
# Automatically merges b4 into w

# From any branch
git knit add b4 --working-branch w
# Switches to w, adds b4, merges it in
```

---

### `git knit remove <branch> [--working-branch <name>]`

Remove a feature branch from the knit.

**Arguments:**

- `branch`: Feature branch to remove
- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. Verify knit is initialized
2. Determine target working branch:
   - If `--working-branch` specified, use that
   - If on a working branch (checked out), use that
   - Otherwise error
3. Verify working branch is not checked out if specified explicitly and different from current branch
4. Check `branch` is in the knit
5. Remove `branch` from `knit.<working-branch>.branches` config
6. Switch to working branch (if not already there)
7. Rebuild working branch with remaining branches

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Working branch not found in knit metadata
- Branch not in knit

**Example:**

```bash
# On working branch w
git knit remove b2
# Knit = b1:b3
# w = main + merge(b1) + merge(b3)

# From any branch
git knit remove b2 --working-branch w
# Switches to w, removes b2, rebuilds
```

---

### `git knit commit <target-branch> [message] [--working-branch <name>]`

Commit current uncommitted changes to a target feature branch.

**Arguments:**

- `target-branch`: Feature branch to commit the changes to
- `message`: Optional commit message (prompts if omitted)
- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. **Pre-commit Validation:**
   - Verify knit is initialized
   - Determine target working branch:
     - If `--working-branch` specified, use that
     - If on a working branch (checked out), use that
     - Otherwise error
   - Verify working branch is currently checked out
   - Verify `target-branch` exists and is in the knit
   - Check for uncommitted changes in working tree (fail if none present)

2. **Stage and Commit:**
   - Stage all uncommitted changes: `git add -A`
   - Checkout target branch: `git checkout "$target_branch"`
   - Create commit: `git commit -m "$message"`
   - Return to working branch: `git checkout "$working_branch"`
   - Reset working branch to clean state: `git reset --hard HEAD`

3. **Merge Target Branch:**
   - Merge the newly committed changes back into working branch
   - Conflicts are handled via standard Git merge resolution

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Not on working branch
- No uncommitted changes in working tree
- Target branch not in knit
- Commit fails (e.g., pre-commit hook)

**Example:**

```bash
# Working on w, made some changes
git knit commit b2 "fix memory leak in parser"
# - Changes are committed directly to b2
# - b2 is merged back into w
```

---

### `git knit move <target-branch> <commit-ref> [--working-branch <name>]`

Move a committed change from the working branch to a target feature branch.

**Arguments:**

- `target-branch`: Feature branch to move the commit to
- `commit-ref`: Reference to commit to move - either:
  - A substring matching the commit message
  - A commit hash prefix (minimum unique prefix required)
- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. **Pre-move Validation:**
   - Verify knit is initialized
   - Determine target working branch:
     - If `--working-branch` specified, use that
     - If on a working branch (checked out), use that
     - Otherwise error
   - Verify working branch is currently checked out
   - Verify `target-branch` exists and is in the knit
   - Check for uncommitted changes in working tree (fail if present)

2. **Find Commit:**
   - Search for commit matching `commit-ref`:
     - First, check if `commit-ref` matches a commit hash prefix
     - If not, search commit messages for substring match
   - If multiple matches found, list them and ask user to specify more precisely
   - If no match found, error

3. **Cherry-pick to Target:**

   ```bash
   git checkout "$target_branch"
   git cherry-pick "$commit_hash"
   ```

   - If conflicts occur:
     - Abort cherry-pick
     - Instruct user to resolve conflicts and retry
     - Recommend enabling `git rerere` for automatic resolution

4. **Restack Dependent Branches (if git-spice available):**

   ```bash
   # Detect git-spice by checking for gs command
   if command -v gs >/dev/null 2>&1; then
       # Check if it's git-spice, not GhostScript
       if gs --help 2>&1 | grep -q "git-spice"; then
           gs stack restack
       fi
   fi
   ```

5. **Rebuild Working Branch:**

   ```bash
   # Note: git branch -D won't work on current branch
   git checkout "$base_branch"
   git branch -D "$working_branch"
   git checkout -b "$working_branch" "$base_branch"

   # Merge all feature branches
   for branch in $knit_branches; do
       git merge "$branch"
   done
   ```

6. **Cleanup Old Commit:**
   - The original commit on working branch is effectively replaced
   - No explicit cleanup needed since working branch was recreated

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Not on working branch
- Uncommitted changes in working tree
- Target branch not in knit
- Commit reference not found or ambiguous
- Cherry-pick conflicts (graceful failure, user instructed)

**Example:**

```bash
# Committed a change to w, now want to move it to b2
git knit move b2 "fix memory leak"
# - Finds commit with message containing "fix memory leak"
# - Cherry-picks to b2
# - Restacks b3 if git-spice installed
# - Rebuilds w

# Or use commit hash prefix
git knit move b2 a1b2c
# - Cherry-picks commit with hash starting with a1b2c
```

---

### `git knit rebuild [--working-branch <name>]`

Force reconstruction of a working branch from all its feature branches.

**Arguments:**

- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. Verify knit is initialized
2. Determine target working branch:
   - If `--working-branch` specified, use that
   - If on a working branch (checked out), use that
   - Otherwise error
3. Get current branch
4. If on working branch:
   - Switch to base branch
   - Delete working branch
   - Recreate from base
   - Merge all feature branches
   - Check out working branch
5. If on other branch:
   - Only rebuild working branch (don't switch)

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Working branch not found in knit metadata
- Uncommitted changes on working branch (abort)

**Use Cases:**

- Manual conflict resolution corrupted the merge
- Feature branches were updated outside the tool
- User wants a clean merge state

**Example:**

```bash
# On working branch w
git knit rebuild
# Rebuilds w from scratch using b1, b2, b3

# From any branch
git knit rebuild --working-branch w
# Rebuilds w without checking it out
```

---

### `git knit restack [--working-branch <name>]`

Restack dependent branches using git-spice.

**Arguments:**

- `--working-branch <name>`: Target working branch (optional, inferred from current branch if on a working branch)

**Behavior:**

1. Verify knit is initialized
2. Determine target working branch:
   - If `--working-branch` specified, use that
   - If on a working branch (checked out), use that
   - Otherwise error
3. Check if git-spice is available (not GhostScript)
4. If available:
   ```bash
   gs stack restack
   ```
5. If not available:
   - Print warning: "git-spice not found, skipping restack"
   - Exit gracefully (not an error)

**Error Conditions:**

- Knit not initialized
- Working branch not specified and not currently on a working branch
- Working branch not found in knit metadata

**Note:** This command is provided as a convenience. Restacking is also automatically done during `git knit move` if git-spice is available.

**Example:**

```bash
# On working branch w
git knit restack
# Runs: gs stack restack

# From any branch
git knit restack --working-branch w
```

---

### `git knit status [--working-branch <name>]`

Display current knit configuration and state.

**Arguments:**

- `--working-branch <name>`: Target working branch (optional, shows all working branches if omitted)

**Behavior:**

When `--working-branch` is specified:

```
git-knit Configuration: w
=========================
Base Branch:      main
Feature Branches: b1, b2, b3

Current Branch:   w
Is Clean:         yes
```

When no arguments specified (shows all working branches):

```
git-knit Working Branches
=========================

w:
  Base Branch:      main
  Feature Branches: b1, b2, b3

work:
  Base Branch:      develop
  Feature Branches: feature-a, feature-b

Current Branch:     w
Is Clean:           yes
```

**Fields:**

- Base Branch: Base branch for the working branch
- Feature Branches: List of feature branches (from config)
- Current Branch: Currently checked-out branch
- Is Clean: Whether working tree has uncommitted changes

**Example:**

```bash
# Show all working branches
git knit status

# Show specific working branch
git knit status --working-branch w
```

---

## Usage Examples

### Example 1: Single Working Branch Workflow

```bash
# Initialize knit
git knit init w main b1 b2 b3

# Work on merged branch (already checked out)
# ... make changes to parser.py ...

# Commit changes directly to b2
git knit commit b2 "fix memory leak in parser"

# ... make more changes ...

# Commit changes directly to b1
git knit commit b1 "add error handling"

# Already committed a change to w, want to move it to b3
git knit move b3 "optimize query"  # matches commit message
# or
git knit move b3 a1b2c  # matches commit hash prefix

# Add a new branch to knit
git knit add b4

# Work continues on w with all changes visible
```

### Example 2: Multiple Working Branches

```bash
# Initialize first working branch (full stack)
git knit init w main b1 b2 b3

# Initialize second working branch (partial stack)
git knit init work main b1 b2

# Work on full stack
git checkout w
git knit commit b3 "add new feature"

# Switch to partial stack
git checkout work
git knit commit b2 "fix bug in feature 2"

# Show all working branches
git knit status
```

### Example 3: Adding Branch Mid-Workflow

```bash
# Working on existing knit on branch w
git knit status --working-branch w
# Shows: b1, b2, b3

# Need to work on a new feature
git checkout -b b4 main
# ... make changes ...
git commit -m "new feature"

# Switch back to working branch to add b4
git checkout w
git knit add b4
# Now w includes b4 automatically

# Add b4 to the other working branch too
git knit add b4 --working-branch work
```

### Example 4: Removing a Branch

```bash
# b3 was merged to main, no longer needed
git knit remove b3
# w rebuilt with only b1, b2, b4

# Remove from specific working branch
git knit remove b2 --working-branch work
```

### Example 5: Manual Merge Recovery

```bash
# Something went wrong, w has conflicts
git knit rebuild
# Clean rebuild from b1, b2, b3, b4

# Rebuild a specific working branch
git knit rebuild --working-branch work
```

### Example 6: Context Inference

```bash
# Currently on w - no need to specify working branch
git checkout w
git knit commit b1 "fix"
# Automatically uses w

# Currently on b1 (feature branch) - must specify working branch
git checkout b1
git knit commit b1 "fix" --working-branch w
# Explicitly targets w's knit

# From non-working, non-feature branch
git checkout main
git knit status
# Shows all working branches
git knit rebuild --working-branch work
# Must specify which working branch to rebuild
```

---

## Implementation Details

### Detecting git-spice vs GhostScript

Both tools may be available as `gs`. The tool must distinguish them:

```bash
# Check if gs command exists
if command -v gs >/dev/null 2>&1; then
    # Check if it's git-spice (has "git-spice" in help)
    if gs --help 2>&1 | grep -q "git-spice"; then
        echo "git-spice detected"
        gs stack restack
    else
        echo "gs exists but is not git-spice (likely GhostScript)"
    fi
else
    echo "git-spice not found, skipping restack"
fi
```

### Branch Order Preservation

The colon-separated list in `knit.<working-branch>.branches` preserves order:

- Earlier branches are merged first
- Later branches depend on earlier ones (if applicable)
- Order matters for `gs stack restack`
- Each working branch maintains its own independent branch order

### Merge Strategy

Default to `git merge` (no special strategy):

- Let Git's default merge algorithm handle it
- Trust `git rerere` for conflict resolution
- Users can configure merge strategy globally via `.git/config` if needed

### Conflict Handling

During cherry-pick or merge operations:

1. If conflict occurs, **abort immediately**
2. Print clear error message explaining what happened
3. Instruct user to:
   - Resolve conflicts manually
   - `git cherry-pick --continue` or `git merge --continue`
   - Or abort and retry
4. Recommend enabling `git rerere` if not already:
   ```bash
   git config --local rerere.enabled true
   ```

### Safety Checks

**Before Destructive Operations:**

- Check for uncommitted changes (abort if present)
- Verify current branch (prevent accidental deletion of wrong branch)
- Confirm knit is initialized

**Before Commit Routing:**

- Verify target branch is in knit (prevent routing to unrelated branch)
- Verify working branch is checked out (prevent routing from wrong place)

### Working Directory Cleanliness

When switching branches during operations:

- Use `git checkout --quiet` to reduce noise
- Always return to working branch at end of command
- Fail early if uncommitted changes detected

### Exit Codes

| Code | Meaning                                                         |
| ---- | --------------------------------------------------------------- |
| 0    | Success                                                         |
| 1    | General error (knit not initialized, branch not found, etc.)    |
| 2    | Uncommitted changes (operation not safe)                        |
| 3    | Conflict during cherry-pick or merge (user intervention needed) |

### Working Branch Resolution

Most commands support an optional `--working-branch` flag. Resolution logic:

1. **Explicit flag provided**: Use the specified working branch
2. **Current branch is a working branch**: Infer from current checkout
3. **Neither**: Error - must specify working branch

```bash
# Get current branch name
current_branch=$(git rev-parse --abbrev-ref HEAD)

# Check if current branch is a working branch
if git config --local --get "knit.${current_branch}.baseBranch" >/dev/null 2>&1; then
    working_branch="$current_branch"
else
    # Not on a working branch
    if [ -z "$explicit_working_branch" ]; then
        echo "Error: Not on a working branch. Use --working-branch <name>"
        exit 1
    fi
    working_branch="$explicit_working_branch"
fi

# Validate working branch exists in metadata
if ! git config --local --get "knit.${working_branch}.baseBranch" >/dev/null 2>&1; then
    echo "Error: Working branch '$working_branch' not found in knit metadata"
    exit 1
fi
```

### List All Working Branches

```bash
# Get all working branch names
git config --local --get-regexp '^knit\..*\.baseBranch' | sed 's/^knit\.\(.*\)\.baseBranch.*/\1/'
```

---

## Edge Cases

### Case 1: Empty Knit

**Scenario:** User runs `git knit init w main` with no feature branches.

**Behavior:**

- Valid initialization (knit is empty)
- `w` is just a clone of `main`
- Subsequent `git knit add` operations work normally

### Case 2: Feature Branch Updated Externally

**Scenario:** `b1` is updated by another process (e.g., `git pull`).

**Behavior:**

- `w` becomes stale (doesn't include new `b1` commits)
- User can run `git knit rebuild` to refresh
- Or, next `git knit commit` will rebuild `w` as part of operation

### Case 3: Dependency Chain

**Scenario:** `b3` depends on `b2`, which depends on `b1`.

**Behavior:**

- Stored as `knit.w.branches=b1:b2:b3` (order preserved)
- `gs stack restack` (if available) handles dependencies
- Without git-spice, user must manually rebase `b3` after `b2` changes
- The knit automatically merges branches in order to maintain dependency relationships
- Each working branch maintains its own independent dependency chains

### Case 4: Working Branch Name Conflict

**Scenario:** User already has a branch named `w`.

**Behavior:**

- `git knit init` detects existing branch
- Asks user: "Branch 'w' already exists. Use existing branch as working branch? [y/N]"
- If yes: Use existing branch (must have correct base)
- If no: Abort with error

### Case 5: Commit Routing to Wrong Branch

**Scenario:** User accidentally runs `git knit commit b1` when they meant `b2`.

**Behavior:**

- Tool performs the operation (can't detect intent)
- User can fix by:
  - `git reset --hard HEAD~1` on `b1` (undo cherry-pick)
  - Run `git knit commit b2` (correct branch)
  - Tool will rebuild `w` automatically

### Case 6: git-spice Partial Installation

**Scenario:** `gs` exists but is GhostScript, not git-spice.

**Behavior:**

- Detection logic correctly identifies GhostScript
- Skips restack with warning
- Rest of workflow proceeds normally

### Case 7: Branch Deletion During Operation

**Scenario:** User deletes `b2` (feature branch) while it's in the knit.

**Behavior:**

- `git knit commit b2` fails (branch not found)
- User must run `git knit remove b2` to update knit metadata
- Or restore `b2` from backup/remote

### Case 8: Large Number of Feature Branches

**Scenario:** User has 10+ branches in knit.

**Behavior:**

- Rebuilding `w` takes longer (10 merges)
- Still works, but user may want to split knits
- Consider performance optimization: batch merges if slow

### Case 9: Merge Commit on Working Branch

**Scenario:** User manually merges another branch into `w`.

**Behavior:**

- Tool detects that `w` has unexpected commits
- `git knit commit` still works (cherry-picks from HEAD)
- But merge commit may confuse dependency tracking
- Warning: "Working branch has merge commits. Consider running 'git knit rebuild'."

### Case 10: Repository with Submodules

**Scenario:** Repository uses Git submodules.

**Behavior:**

- Standard Git operations work with submodules
- No special handling needed in tool
- User may need to run `git submodule update` after `git knit rebuild`

---

## Appendix: Configuration File Example

```ini
# .git/config
[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true

[knit "w"]
    baseBranch = main
    branches = b1:b2:b3:b4

[knit "work"]
    baseBranch = develop
    branches = feature-a:feature-b

[rerere]
    enabled = true
    autoupdate = true
```

---

## Appendix: Dependency Check Script

```bash
#!/bin/bash
# Checks if git-spice is available (not GhostScript)

check_git_spice() {
    # Check if gs exists
    if ! command -v gs >/dev/null 2>&1; then
        return 1
    fi

    # Check if it's git-spice
    if gs --help 2>&1 | grep -q "git-spice"; then
        return 0
    fi

    # It's GhostScript or something else
    return 1
}

if check_git_spice; then
    echo "git-spice is available"
    gs stack restack
else
    echo "git-spice not available, skipping restack"
fi
```

[git-spice]: https://abhinav.github.io/git-spice/
[local Git configuration]: https://git-scm.com/docs/git-config#FILES
