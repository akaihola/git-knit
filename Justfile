lint:
    ruff check . || uvx ruff check . || nix run 'nixpkgs#ruff' -- check .
    ty check . || uvx ty check . || nix run 'nixpkgs#ty' -- check .
    pyright . || uvx pyright . || nix run 'nixpkgs#pyright' -- .
