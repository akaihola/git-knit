# Git Stack: Merged Branch Workflow Tool

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

`git stack` enables a development workflow where multiple feature branches are merged into a single working branch, allowing you to work on all changes simultaneously. Commits made in the working branch can then be routed back to their originating feature branches, with automatic reconstruction of the merged view.

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
  ├─ b2 (feature branch 2)  
  └─ b3 (feature branch 3)

w = main + merge(b1) + merge(b2) + merge(b3)
```

1. User works on branch `w` (the merged view)
2. User runs `git stack commit b2 "fix bug"` 
3. Tool:
   - Cherry-picks HEAD commit from `w` to `b2`
   - Optionally restacks dependent branches (e.g., `b3`) using git-spice
   - Rebuilds `w` by resetting to base and re-merging all branches
4. User continues working on `w` with all changes visible

### Key Principles

- **Single Working Branch**: Only the working branch (`w`) is checked out during normal development
- **Commit Routing**: Each commit is explicitly routed to a target branch in the stack
- **Automatic Reconstruction**: The merged view (`w`) is automatically rebuilt after each routed commit
- **Conflict Reuse**: Leverages `git rerere` to remember and replay conflict resolutions
- **Optional git-spice**: Supports `git-spice restack` if available, gracefully degrades if not

---

## Metadata Storage

### Git Config Section

All metadata is stored in the local Git configuration under the `stack` section:

```
[stack]
    workingBranch = w
    baseBranch = main
    branches = b1:b2:b3
```

### Config Keys

| Key | Description | Example |
|------|-------------|----------|
| `stack.workingBranch` | Name of the merged working branch | `w` |
| `stack.baseBranch` | Base branch all feature branches originate from | `main` |
| `stack.branches` | Colon-separated list of feature branches | `b1:b2:b3` |

### Configuration Commands

```bash
# Read metadata
git config --local --get stack.workingBranch
git config --local --get stack.baseBranch
git config --local --get stack.branches

# Write metadata
git config --local stack.workingBranch "w"
git config --local stack.baseBranch "main"
git config --local stack.branches "b1:b2:b3"

# Check if stack is initialized
git config --local --get-all stack.workingBranch >/dev/null
```

### Rationale for Git Config

- **Native to Git**: No external files or dependencies
- **Persistent**: Travels with the repository (in `.git/config`)
- **Script-friendly**: Easy to read/write from shell
- **Namespace-safe**: Uses `stack.` prefix to avoid conflicts
- **No working directory pollution**: Metadata lives in `.git/`, not project root

---

## Command Reference

### `git stack init <working-branch> <base-branch> [branch...]`

Initialize a new stack configuration.

**Arguments:**
- `working-branch`: Name for the merged working branch (e.g., `w`)
- `base-branch`: Base branch (e.g., `main`)
- `branch...`: Zero or more feature branches to include in stack

**Behavior:**
1. Validate that `base-branch` exists
2. Create `working-branch` from `base-branch` if it doesn't exist
3. Store metadata in Git config
4. Merge all specified branches into `working-branch` (if any provided)
5. Check out `working-branch`

**Error Conditions:**
- Stack already initialized in this repository
- `base-branch` does not exist
- `working-branch` is the current branch (would create circular dependency)

**Example:**
```bash
git stack init w main b1 b2 b3
# Creates: w = main + merge(b1) + merge(b2) + merge(b3)
```

---

### `git stack add <branch>`

Add a feature branch to the stack.

**Arguments:**
- `branch`: Feature branch to add

**Behavior:**
1. Verify stack is initialized
2. Validate that `branch` exists
3. Check `branch` is not already in the stack
4. Append `branch` to `stack.branches` config
5. Merge `branch` into `workingBranch` (if not currently checked out)

**Error Conditions:**
- Stack not initialized
- Branch does not exist
- Branch already in stack

**Example:**
```bash
git stack add b4
# Now stack = b1:b2:b3:b4
# Automatically merges b4 into w
```

---

### `git stack remove <branch>`

Remove a feature branch from the stack.

**Arguments:**
- `branch`: Feature branch to remove

**Behavior:**
1. Verify stack is initialized
2. Check `branch` is in the stack
3. Remove `branch` from `stack.branches` config
4. Rebuild `workingBranch` with remaining branches

**Error Conditions:**
- Stack not initialized
- Branch not in stack

**Example:**
```bash
git stack remove b2
# Stack = b1:b3
# w = main + merge(b1) + merge(b3)
```

---

### `git stack commit <target-branch> [message]`

Commit changes from working branch to a target feature branch.

**Arguments:**
- `target-branch`: Feature branch to route the commit to
- `message`: Optional commit message (defaults to working branch's HEAD message)

**Behavior:**

1. **Pre-commit Validation:**
   - Verify stack is initialized
   - Verify working branch is currently checked out
   - Verify `target-branch` exists and is in the stack
   - Check for uncommitted changes in working tree (fail if present)

2. **Capture Current State:**
   - Get commit hash of working branch HEAD: `WORKING_COMMIT=$(git rev-parse HEAD)`

3. **Cherry-pick to Target:**
   ```bash
   git checkout "$target_branch"
   git cherry-pick "$WORKING_COMMIT" -m "$commit_msg"
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
   for branch in $stack_branches; do
       git merge "$branch"
   done
   ```

6. **Cleanup Old Commit:**
   - The original commit on `w` is effectively replaced
   - No explicit cleanup needed since `w` was recreated

**Error Conditions:**
- Stack not initialized
- Not on working branch
- Uncommitted changes in working tree
- Target branch not in stack
- Cherry-pick conflicts (graceful failure, user instructed)

**Example:**
```bash
git stack commit b2 "fix memory leak in parser"
# - Cherry-picks to b2
# - Restacks b3 if git-spice installed
# - Rebuilds w
```

---

### `git stack rebuild`

Force reconstruction of the working branch from all feature branches.

**Behavior:**
1. Verify stack is initialized
2. Get current branch
3. If on working branch:
   - Switch to base branch
   - Delete working branch
   - Recreate from base
   - Merge all feature branches
   - Check out working branch
4. If on other branch:
   - Only rebuild working branch (don't switch)

**Error Conditions:**
- Stack not initialized
- Uncommitted changes on working branch (abort)

**Use Cases:**
- Manual conflict resolution corrupted the merge
- Feature branches were updated outside the tool
- User wants a clean merge state

**Example:**
```bash
git stack rebuild
# Rebuilds w from scratch using b1, b2, b3
```

---

### `git stack restack`

Restack dependent branches using git-spice.

**Behavior:**
1. Verify stack is initialized
2. Check if git-spice is available (not GhostScript)
3. If available:
   ```bash
   gs stack restack
   ```
4. If not available:
   - Print warning: "git-spice not found, skipping restack"
   - Exit gracefully (not an error)

**Error Conditions:**
- Stack not initialized

**Note:** This command is provided as a convenience. Restacking is also automatically done during `git stack commit` if git-spice is available.

**Example:**
```bash
git stack restack
# Runs: gs stack restack
```

---

### `git stack status`

Display current stack configuration and state.

**Behavior:**
```
Git Stack Configuration
====================
Working Branch:  w
Base Branch:     main
Feature Branches: b1, b2, b3

Current Branch:   w
Is Clean:        yes
```

**Fields:**
- Working Branch: Name of merged working branch
- Base Branch: Base branch
- Feature Branches: List of feature branches (from config)
- Current Branch: Currently checked-out branch
- Is Clean: Whether working tree has uncommitted changes

**Example:**
```bash
git stack status
```

---

## Usage Examples

### Example 1: Complete Workflow

```bash
# Initialize stack
git stack init w main b1 b2 b3

# Work on merged branch (already checked out)
# ... make changes to parser.py ...

# Commit to b2
git stack commit b2 "fix memory leak in parser"

# ... make more changes ...

# Commit to b1
git stack commit b1 "add error handling"

# Add a new branch to stack
git stack add b4

# Work continues on w with all changes visible
```

### Example 2: Adding Branch Mid-Workflow

```bash
# Working on existing stack
git stack status
# Shows: b1, b2, b3

# Need to work on a new feature
git checkout -b b4 main
# ... make changes ...
git commit -m "new feature"

# Add to stack
git stack add b4
# Now w includes b4 automatically
```

### Example 3: Removing a Branch

```bash
# b3 was merged to main, no longer needed
git stack remove b3
# w rebuilt with only b1, b2, b4
```

### Example 4: Manual Merge Recovery

```bash
# Something went wrong, w has conflicts
git stack rebuild
# Clean rebuild from b1, b2, b3, b4
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

The colon-separated list in `stack.branches` preserves order:
- Earlier branches are merged first
- Later branches depend on earlier ones (if applicable)
- Order matters for `gs stack restack`

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
- Confirm stack is initialized

**Before Commit Routing:**
- Verify target branch is in stack (prevent routing to unrelated branch)
- Verify working branch is checked out (prevent routing from wrong place)

### Working Directory Cleanliness

When switching branches during operations:
- Use `git checkout --quiet` to reduce noise
- Always return to working branch at end of command
- Fail early if uncommitted changes detected

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (stack not initialized, branch not found, etc.) |
| 2 | Uncommitted changes (operation not safe) |
| 3 | Conflict during cherry-pick or merge (user intervention needed) |

---

## Edge Cases

### Case 1: Empty Stack

**Scenario:** User runs `git stack init w main` with no feature branches.

**Behavior:**
- Valid initialization (stack is empty)
- `w` is just a clone of `main`
- Subsequent `git stack add` operations work normally

### Case 2: Feature Branch Updated Externally

**Scenario:** `b1` is updated by another process (e.g., `git pull`).

**Behavior:**
- `w` becomes stale (doesn't include new `b1` commits)
- User can run `git stack rebuild` to refresh
- Or, next `git stack commit` will rebuild `w` as part of operation

### Case 3: Dependency Chain

**Scenario:** `b3` depends on `b2`, which depends on `b1`.

**Behavior:**
- Stored as `stack.branches=b1:b2:b3`
- `gs stack restack` (if available) handles dependencies
- Without git-spice, user must manually rebase `b3` after `b2` changes

### Case 4: Working Branch Name Conflict

**Scenario:** User already has a branch named `w`.

**Behavior:**
- `git stack init` detects existing branch
- Asks user: "Branch 'w' already exists. Use existing branch as working branch? [y/N]"
- If yes: Use existing branch (must have correct base)
- If no: Abort with error

### Case 5: Commit Routing to Wrong Branch

**Scenario:** User accidentally runs `git stack commit b1` when they meant `b2`.

**Behavior:**
- Tool performs the operation (can't detect intent)
- User can fix by:
  - `git reset --hard HEAD~1` on `b1` (undo cherry-pick)
  - Run `git stack commit b2` (correct branch)
  - Tool will rebuild `w` automatically

### Case 6: git-spice Partial Installation

**Scenario:** `gs` exists but is GhostScript, not git-spice.

**Behavior:**
- Detection logic correctly identifies GhostScript
- Skips restack with warning
- Rest of workflow proceeds normally

### Case 7: Branch Deletion During Operation

**Scenario:** User deletes `b2` (feature branch) while it's in the stack.

**Behavior:**
- `git stack commit b2` fails (branch not found)
- User must run `git stack remove b2` to update stack metadata
- Or restore `b2` from backup/remote

### Case 8: Large Number of Feature Branches

**Scenario:** User has 10+ branches in stack.

**Behavior:**
- Rebuilding `w` takes longer (10 merges)
- Still works, but user may want to split stacks
- Consider performance optimization: batch merges if slow

### Case 9: Merge Commit on Working Branch

**Scenario:** User manually merges another branch into `w`.

**Behavior:**
- Tool detects that `w` has unexpected commits
- `git stack commit` still works (cherry-picks from HEAD)
- But merge commit may confuse dependency tracking
- Warning: "Working branch has merge commits. Consider running 'git stack rebuild'."

### Case 10: Repository with Submodules

**Scenario:** Repository uses Git submodules.

**Behavior:**
- Standard Git operations work with submodules
- No special handling needed in tool
- User may need to run `git submodule update` after `git stack rebuild`

---

## Appendix: Configuration File Example

```ini
# .git/config
[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true

[stack]
    workingBranch = w
    baseBranch = main
    branches = b1:b2:b3:b4

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
