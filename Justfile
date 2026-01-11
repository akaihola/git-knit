_run tool *args:
    @echo "Running {{ tool }}..."
    @if command -v {{ tool }} > /dev/null 2>&1; then \
        {{ tool }} {{ args }}; \
    elif command -v uvx > /dev/null 2>&1; then \
        uvx {{ tool }} {{ args }}; \
    else \
        nix run 'nixpkgs#{{ tool }}' -- {{ args }}; \
    fi

lint:
    #!/usr/bin/env bash
    set -e
    exit_code=0
    just _run ruff check . || exit_code=$?
    just _run ty check . || exit_code=$?
    just _run pyright . || exit_code=$?
    exit $exit_code

lint-concise:
    #!/usr/bin/env bash
    set -e
    exit_code=0
    just _run ruff check --output-format=concise . || exit_code=$?
    just _run ty check --quiet . || exit_code=$?
    just _run pyright | sed "s|$(pwd)/||g" || exit_code=$?
    exit $exit_code
