# PMCC Backtest task runner (ARCHITECTURE §14). Recipes run under bash: Git Bash
# locally, bash on the CI runners (DEC-58). Tools run from the uv env at the
# uv.lock versions (DEC-77). A recipe whose command isn't built yet fails loudly,
# naming its backlog item.

set shell := ["bash", "-cu"]

uv := "uv run --frozen"

# List the recipes
default:
    @just --list

# Install the Python and web environments and the git hooks
setup:
    uv sync --frozen
    cd web && npm ci
    {{uv}} pre-commit install

# Lint, format check, pyright and guards on all files, then pytest, then the web checks (their types come from the JSON Schema, so no results are needed)
check:
    {{uv}} pre-commit run --all-files
    {{uv}} pytest
    {{uv}} pmcc export --schema-only --out web/public/data/
    cd web && npm run lint && npm run typecheck && npm run test

# Run pytest (dev hypothesis profile unless HYPOTHESIS_PROFILE is set)
test *ARGS:
    {{uv}} pytest {{ARGS}}

# Run the LSEG spikes for a symbol (local; Workspace signed in)
probe SYM:
    {{uv}} pmcc probe --symbol {{SYM}}

# Pull a symbol from LSEG into the cache (local; Workspace signed in). Add --plan-only for the estimate
fetch SYM START END *ARGS:
    {{uv}} pmcc fetch --symbol {{SYM}} --start {{START}} --end {{END}} {{ARGS}}

# Backtest one strategy config on one symbol, from the cache only
run SYM CONFIG:
    {{uv}} pmcc run --symbol {{SYM}} --config {{CONFIG}}

# Run every symbol, strategy and variant in the universe
batch:
    {{uv}} pmcc batch --universe configs/universe.yaml

# Calibrate the starting cash into configs/universe.yaml. Add --symbol/--config to narrow it, --check to compare
calibrate *ARGS:
    {{uv}} pmcc calibrate {{ARGS}}

# Write site data and JSON Schema from committed results
export:
    {{uv}} pmcc export --out web/public/data/

# Re-derive the invariants from committed results
verify:
    {{uv}} pmcc verify results/

# Start the Vite dev server over the exported results
web-dev: export
    cd web && npm run dev

# Build the static site into web/dist from the exported results
web-build: export
    cd web && npm run build

# Run the Playwright smoke test
e2e:
    cd web && npm run e2e

# Serve the built site and the local data endpoints on 127.0.0.1
serve:
    {{uv}} pmcc serve

# Cached data -> all runs -> verify -> export -> built site (Spec › CLI)
reproduce: batch verify export web-build
