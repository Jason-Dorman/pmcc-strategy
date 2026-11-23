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

# The live wheel's close snapshot over the headless LSEG session (LSEG_APP_KEY, LSEG_USERNAME,
# LSEG_PASSWORD in the environment; no Workspace). Prints counts; the report stays in data_cache/probes/
live-probe SYM:
    {{uv}} pmcc live-probe --symbol {{SYM}}

# One night of the live wheel: Sanji's book in, open_orders.json out (after the close; add --dry-run
# to write nothing). Asks LSEG only the night before a week's first session
live SYM *ARGS:
    {{uv}} pmcc live --symbol {{SYM}} {{ARGS}}

# NVDA's volatility for the live page's charts (L4-02): ATM IV ~30 days out and RV20 into
# live/vol.jsonl, the week's smile into live/smile.json. Add --since DAY to backfill, after
# --plan-only. Platform credentials in the environment, as `live`'s
vol SYM *ARGS:
    {{uv}} pmcc vol --symbol {{SYM}} {{ARGS}}

# The thesis's data probe (T1-01; TD-04, TD-05): the S&P 500's and VIX's closes, the high-yield
# OAS on LSEG and FRED, an SPXW chain. Platform credentials in the environment, as `live`'s.
# Prints counts; the report stays in data_cache/probes/
thesis-probe:
    {{uv}} thesis probe

thesis *ARGS:
    {{uv}} thesis run {{ARGS}}

# Pull a symbol from LSEG into the cache (local; Workspace signed in). Add --plan-only for the estimate
fetch SYM START END *ARGS:
    {{uv}} pmcc fetch --symbol {{SYM}} --start {{START}} --end {{END}} {{ARGS}}

# Backtest one strategy config on one symbol, from the cache only
run SYM CONFIG:
    {{uv}} pmcc run --symbol {{SYM}} --config {{CONFIG}}

# Backtest the wheel on one symbol (W2-03), from the cache only. Add --config for another wheel config
wheel SYM *ARGS:
    {{uv}} pmcc wheel --symbol {{SYM}} {{ARGS}}

# The wheel and its friction runs on one symbol (W3-02): configs/wheel.yaml, then each configs/wheel_friction/*.yaml
wheels SYM:
    {{uv}} pmcc wheel --symbol {{SYM}}
    for config in configs/wheel_friction/*.yaml; do {{uv}} pmcc wheel --symbol {{SYM}} --config "$config" || exit 1; done

# Run every symbol, strategy and variant in the universe
batch:
    {{uv}} pmcc batch --universe configs/universe.yaml

# Calibrate each symbol's starting cash into configs/universe.yaml (default: every symbol without a final value). Add --symbol/--config to narrow it, --check to compare
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

# Build the static site into web/dist from the exported results, then run the dist guard
web-build: export
    cd web && npm run build && npm run guard

# Build the site, then smoke-test every route in Chromium (Playwright; INV-15)
e2e: web-build
    cd web && npm run e2e

# Serve the built site and the local data endpoints on 127.0.0.1
serve:
    {{uv}} pmcc serve

# Cached data -> all runs (the PMCC's batch, then the wheel and its friction runs on NVDA) -> verify -> export -> built site (Spec › CLI)
reproduce: batch (wheels "NVDA") verify export web-build
