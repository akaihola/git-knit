# Agent Instructions

## Code Quality Checks

Run linting with `just lint`, trying in order: global → `uvx` → `nix run`:

```bash
just lint || uvx --from just-bin just lint || nix run 'nixpkgs#just' -- lint
```

Configuration: `pyproject.toml` (ruff: ~40 rule categories strict, pyright: strict mode)

Always run before submitting code.
