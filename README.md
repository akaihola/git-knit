# git-knit

> Work on multiple Open Source contributions simultaneously in a unified view, then route each change to its own PR-ready branch.

---

## ⚠️ EXPERIMENTAL PROTOTYPE - USE WITH CAUTION

![Status: Prototype](https://img.shields.io/badge/Status-Experimental%20Prototype-red?style=for-the-badge)

**git-knit is currently a rough, vibe-coded prototype and should be treated as UNTRUSTED SOFTWARE.**

### What This Means:

- **No Guarantee of Correctness:** Code has not been thoroughly reviewed or tested in production
- **Experimental Status:** Core features may change, break, or work unexpectedly
- **Risk of Data Loss:** Always back up your repository before using git-knit
- **Use Locally Only:** Do not use on branches you care deeply about without comprehensive testing first

### Before Using:

1. ✅ Back up your repository
2. ✅ Test on a small, non-critical project first
3. ✅ Review the source code to understand what commands do
4. ✅ Report issues and unexpected behavior

### Planned:

A thorough human code review is planned to validate design and implementation. Until then, **assume this is experimental and untrusted software**.

---

**Problem:** Contributing to Open Source often means juggling multiple branches. You want to fix three bugs and add a feature, but need to see and test all changes together. You want to submit separate PRs (because maintainers love focused changes), but you also need to iterate on those PRs after submission. Some work isn't ready to push yet, but you still need it in your local testing environment.

**Solution:** `git-knit` lets you create a merged "working branch" that combines all your feature branches. Make changes in one place, test the complete system, then route each commit to its intended branch. Refine your PRs with force pushes, keep private work local, all while maintaining clean, focused PRs ready for maintainers.

---

## Quick Start

```bash
# Install
pip install git-knit

# You're working on an OSS project with 3 issues to fix
# Create separate branches for each fix
git checkout -b fix-authentication main
git checkout -b fix-memory-leak main
git checkout -b add-user-profile main

# Create a working branch that merges all of them
git knit init dev main fix-authentication fix-memory-leak add-user-profile
# Now on 'dev' branch with all fixes merged

# Make changes, test everything together...
# Oops, forgot to handle edge case in auth module
# Edit auth.py...

# Route this fix to the correct PR branch
git knit commit fix-authentication "handle edge case in auth validation"
# Changes are now on fix-authentication, dev is rebuilt

# Submit your PRs
git push origin fix-authentication
git push origin fix-memory-leak

# Later: fix-reviewer-comment on fix-authentication
git knit commit fix-authentication "address reviewer feedback"
git push origin fix-authentication --force
# PR updated, dev still has all your work
```

---

## Why git-knit?

You're a responsible Open Source contributor. You know maintainers prefer focused, non-stacked PRs. But your workflow needs more flexibility:

| Your Need                                   | Traditional Git                          | git-knit                                       |
| ------------------------------------------- | ---------------------------------------- | ---------------------------------------------- |
| **Work on multiple contributions together** | Switch branches constantly, lose context | One working branch, all changes visible        |
| **Submit separate PRs**                     | Cherry-pick commits manually             | `git knit commit` routes automatically         |
| **Iterate on submitted PRs**                | Messy rebasing, lost work                | Edit in working branch, route back, force push |
| **Keep work private**                       | Can't test with private work             | Include private branches, don't push them      |
| **Quick local testing**                     | Merge test branches, then unmerge        | Working branch always reflects all work        |
| **Maintainer responsiveness**               | Wait for feedback between PRs            | Iterate independently, submit when ready       |

**Perfect for:**

- 🐛 Fixing multiple related bugs
- ✨ Adding features that depend on each other
- 📚 Refactoring that touches multiple areas
- 🧪 Testing contributions together before submitting
- 🔄 Iterating on PRs based on reviewer feedback

---

## How It Works

### The Problem

```bash
# You want to fix 3 bugs and add a feature
# You create 4 branches
git checkout -b fix-auth main
git checkout -b fix-ui main
git checkout -b fix-api main
git checkout -b add-feature main

# But you can only work on one branch at a time
# Switching between branches = losing context
# Testing all fixes together = manual merges each time
# Refine a fix = switch, commit, switch back, rebase...
```

### The git-knit Solution

```
main (upstream)
  ├─ fix-auth           (PR-ready)
  ├─ fix-ui             (PR-ready)
  ├─ fix-api            (PR-ready)
  └─ add-feature        (private, not pushed)

dev (working branch)
  = main + merge(fix-auth) + merge(fix-ui) + merge(fix-api) + merge(add-feature)
  ↑
  Work here! All changes visible together
```

```bash
# Initialize the merged view
git knit init dev main fix-auth fix-ui fix-api add-feature
# Switched to branch 'dev'

# Make changes, test everything together
# Edit files, run tests, see all 4 contributions working

# Made a fix for auth module
git knit commit fix-auth "handle edge case"
# Changes now on fix-auth, dev rebuilt

# Made a fix for UI (not ready for PR yet)
git knit commit fix-ui "improve responsiveness"
# Changes now on fix-ui, dev rebuilt (but you haven't pushed fix-ui)

# Time to submit some PRs
git push origin fix-auth
git push origin fix-api

# Reviewer asks for change on fix-auth
git knit commit fix-auth "address reviewer feedback"
git push origin fix-auth --force
# PR updated, dev still has all your work
```

---

## Installation

```bash
# pip (recommended)
pip install git-knit

# uv (faster)
uv tool install git-knit

# From source
git clone https://github.com/user/git-knit
cd git-knit
pip install -e .
```

### Verify Installation

```bash
git-knit --version
# git-knit 0.1.0

git knit --help
# Shows all available commands
```

### Optional: Git-spice for Stacked PRs

If you occasionally need stacked PRs (PR B depends on PR A):

```bash
# Install git-spice
pip install git-spice

# git-knit automatically uses it when available
# Makes restacking dependent PRs effortless
```

---

## Core Concepts

### Working Branch

A special branch that merges all your feature branches:

```bash
git knit init dev main fix-a fix-b fix-c
# Creates 'dev' branch = main + fix-a + fix-b + fix-c
```

**Why use it:**

- See all changes together
- Test complete system
- Work in one place
- Easy to context-switch between contributions

### Commit Routing

Move changes from working branch to their target branch:

```bash
# Make changes in dev
# Route to specific PR branch
git knit commit fix-auth "handle edge case"
```

**What happens:**

1. Changes are committed directly to `fix-auth`
2. `fix-auth` is merged back into `dev`
3. Working branch reflects all work again

### Multiple Working Branches

Different contexts for different work:

```bash
# Full stack for local development
git knit init dev main fix-a fix-b fix-c fix-d

# Partial stack for quick testing
git knit init quick main fix-a

# Keep both - switch between them as needed
git checkout dev  # All work
git checkout quick  # Quick tests
```

---

## Common Workflows

### Workflow 1: Fix Multiple Bugs

```bash
# You found 3 bugs to fix
# Create separate branches
git checkout -b fix-bug-1 main
git checkout -b fix-bug-2 main
git checkout -b fix-bug-3 main

# Initialize working branch
git knit init work main fix-bug-1 fix-bug-2 fix-bug-3

# Make changes, test all fixes together
# Edit files, run tests, see all bugs fixed

# Route each fix
git knit commit fix-bug-1 "resolve null pointer"
git knit commit fix-bug-2 "fix race condition"
git knit commit fix-bug-3 "handle edge case"

# Submit PRs
git push origin fix-bug-1
git push origin fix-bug-2
git push origin fix-bug-3
```

### Workflow 2: Stacked Features (with git-spice)

```bash
# Feature B depends on Feature A
git checkout -b feature-a main
git checkout -b feature-b feature-a

git knit init dev main feature-a feature-b

# Make changes, route appropriately
git knit commit feature-a "add base functionality"
git knit commit feature-b "extend feature"

# Push stacked PRs
git push origin feature-a
git push origin feature-b
# git-spice handles the stacking
```

### Workflow 3: Keep Work Private Until Ready

```bash
# One fix is ready, one feature needs more work
git knit init dev main fix-bug feature-wip

# Make bug fix, route it
git knit commit fix-bug "critical bug fix"

# Submit bug fix PR
git push origin fix-bug

# Keep iterating on feature-wip
# Don't push it until ready
git knit commit feature-wip "improve implementation"
git knit commit feature-wip "add tests"

# Finally ready
git push origin feature-wip
```

### Workflow 4: Iterate on Submitted PRs

```bash
# Submitted PRs for fix-a and fix-b
git knit init dev main fix-a fix-b

# Reviewer asks for change on fix-a
git knit commit fix-a "address reviewer feedback"
git push origin fix-a --force

# Another review on fix-b
git knit commit fix-b "optimize per reviewer"
git push origin fix-b --force

# Your working branch always reflects the latest state
# No rebase hell, no lost work
```

### Workflow 5: Move Misrouted Commit

```bash
# Oops, committed to wrong branch
git knit commit fix-a "this should be in fix-b"

# Move it to correct branch
git knit move fix-b "this should be in fix-b"
# Searches commit by message, moves it
```

---

## Command Reference

### `git knit init <working-branch> <base-branch> [branch...]`

Initialize a new merged working branch.

```bash
git knit init dev main fix-a fix-b fix-c
```

**Parameters:**

- `working-branch`: Name for your merged view (e.g., `dev`, `work`)
- `base-branch`: Base branch to start from (usually `main` or `master`)
- `branch...`: Feature branches to include (can be empty)

**What it does:**

1. Creates working branch from base branch
2. Stores configuration in Git config
3. Merges all feature branches into working branch
4. Checks out working branch

---

### `git knit commit <target-branch> [message]`

Route uncommitted changes to a target branch.

```bash
# Made changes in dev
git knit commit fix-a "fix critical bug"
```

**Parameters:**

- `target-branch`: Which branch gets this commit
- `message`: Commit message (prompts if omitted)

**What it does:**

1. Commits changes to target branch
2. Merges target branch back into working branch
3. Working branch reflects all work again

**When to use:** You made changes that belong to a specific PR branch.

---

### `git knit add <branch> [--working-branch <name>]`

Add a branch to the knit.

```bash
git knit add fix-d
# Adds fix-d to current working branch's knit
```

**What it does:**

1. Adds branch to knit configuration
2. Merges it into working branch

**When to use:** Created a new feature branch and want to include it.

---

### `git knit remove <branch> [--working-branch <name>]`

Remove a branch from the knit.

```bash
git knit remove fix-b
# Removes fix-b, rebuilds working branch without it
```

**What it does:**

1. Removes branch from knit configuration
2. Rebuilds working branch with remaining branches

**When to use:** Branch was merged upstream or no longer needed.

---

### `git knit move <target-branch> <commit-ref>`

Move a committed change to a different branch.

```bash
# Move by commit message
git knit move fix-b "this should be in fix-b"

# Move by commit hash prefix
git knit move fix-b a1b2c
```

**What it does:**

1. Finds the commit
2. Cherry-picks it to target branch
3. Restacks dependent branches (if git-spice available)
4. Rebuilds working branch

**When to use:** Committed to wrong branch or need to reorganize.

---

### `git knit rebuild [--working-branch <name>]`

Force rebuild working branch from scratch.

```bash
git knit rebuild
# Clean rebuild of current working branch
```

**What it does:**

1. Deletes working branch
2. Recreates from base
3. Merges all feature branches

**When to use:** Merge got corrupted or you want clean state.

---

### `git knit restack [--working-branch <name>]`

Restack dependent branches using git-spice.

```bash
git knit restack
# Runs: gs stack restack
```

**When to use:** Dependent branches need rebasing after upstream changes.

---

### `git knit status [--working-branch <name>]`

Show current knit configuration.

```bash
git knit status
# Shows all working branches

git knit status --working-branch dev
# Shows specific working branch details
```

**Output:**

```
git-knit Working Branches
========================

dev:
  Base Branch:      main
  Feature Branches: fix-a, fix-b, fix-c

quick:
  Base Branch:      main
  Feature Branches: fix-a

Current Branch:     dev
Is Clean:           yes
```

---

## Best Practices

### 1. Organize by Logical Groupings

```bash
# All UI fixes in one working branch
git knit init ui-work main fix-ui-a fix-ui-b fix-ui-c

# All API fixes in another
git knit init api-work main fix-api-a fix-api-b
```

### 2. Separate Submitted from Private Work

```bash
# Branches ready for PRs
git checkout -b pr-ready-a main
git checkout -b pr-ready-b main

# Work still in progress
git checkout -b wip-feature main

git knit init work main pr-ready-a pr-ready-b wip-feature
# Only push pr-ready branches, keep wip local
```

### 3. Use Meaningful Commit Messages

```bash
git knit commit fix-auth "resolve authentication timeout"
git knit commit add-profile "add user profile page"
# Makes move operations easier to use
```

### 4. Enable git-rerere for Conflict Resolution

```bash
git config --global rerere.enabled true
git config --global rerere.autoupdate true
# Remembers conflict resolutions, reapplies automatically
```

### 5. Keep Working Branches Small

```bash
# Good: 3-5 related branches
git knit init work main fix-a fix-b fix-c

# Avoid: 20+ branches (slow rebuilds)
# Split into multiple working branches instead
```

---

## Troubleshooting

### "Knit not initialized"

**Problem:** You haven't set up git-knit yet.

**Solution:**

```bash
git knit init <work> <base> [branches...]
```

### "Merge conflict with branch 'fix-a'"

**Problem:** Git couldn't auto-resolve conflicts.

**Solution:**

```bash
# Resolve conflicts manually
# Edit conflicted files
git add .
git merge --continue

# Or enable rerere to prevent this
git config --global rerere.enabled true
```

### "git-spice not found, skipping restack"

**Problem:** Optional dependency missing.

**Solution:** This is fine! git-knit works without git-spice. Install if you want stacked PR support:

```bash
pip install git-spice
```

### "Branch 'fix-a' does not exist"

**Problem:** Feature branch referenced in knit doesn't exist.

**Solution:**

```bash
# Remove it from knit
git knit remove fix-a

# Or create the branch
git checkout -b fix-a main
```

### "Working tree has uncommitted changes"

**Problem:** You have unsaved changes.

**Solution:**

```bash
# Commit or stash them
git knit commit fix-a "your message"
# or
git stash
```

---

## FAQ

**Q: Can I use git-knit with existing branches?**
A: Yes! Just run `git knit init` with your existing branch names. It'll merge them into a working branch.

**Q: What happens if I delete a feature branch?**
A: Run `git knit remove <branch>` first to update knit metadata, then delete the branch normally.

**Q: Can I have multiple working branches?**
A: Yes! Each `git knit init` creates an independent working branch. Great for organizing work by context.

**Q: Do I need git-spice?**
A: No. git-knit works standalone. git-spice is optional for stacked PR workflows.

**Q: What if maintainer rebases upstream?**
A: Your feature branches will be behind. Rebase them individually, then `git knit rebuild` to update working branch.

**Q: Can I use git-knit with git submodules?**
A: Yes. Git operations work normally with submodules. You may need to run `git submodule update` after rebuilds.

**Q: How is this different from git-stacked-diffs?**
A: git-stacked-diffs is for stacked PR workflows only. git-knit is broader: work on multiple independent contributions together, then route to separate PR branches. You don't need stacks unless you want them.

**Q: Can I contribute to a repo that uses conventional commits?**
A: Absolutely. git-knit doesn't change your commit messages. Just use conventional commit format in your messages:

```bash
git knit commit fix-auth "fix(auth): handle timeout edge case"
```

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/user/git-knit
cd git-knit
uv sync --all-extras

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=git_knit
```

### Project Status

**Version:** 0.1.0 (Alpha)

**Stability:** Core features are tested and working. API may change.

**Roadmap:**

- [ ] Git integration (symlink for `git knit` command)
- [ ] Interactive commit routing (fuzzy search)
- [ ] Visual branch graph display
- [ ] Integration tests with real repos

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Links

- 📖 [Full Specification](specification.md)
- 🚀 [PyPI Package](https://pypi.org/project/git-knit/)
- 🐛 [Report Issues](https://github.com/user/git-knit/issues)
- 💬 [Discussions](https://github.com/user/git-knit/discussions)
