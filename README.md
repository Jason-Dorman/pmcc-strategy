# PMCC Backtest

A symbol-agnostic backtester for the **Poor Man's Covered Call** (PMCC): a deep in-the-money, long-dated call held as a stock substitute, with weekly out-of-the-money calls sold against it. One engine runs two strategies, a fixed-rule baseline and a quant variant, on LSEG hourly data, and publishes the results as a static site on GitHub Pages.

> **Status:** foundations (P0) are in place: toolchain, quality gates, CI, logging and import-boundary tests. The data layer (P1) is in: the domain primitives (integer money, option IDs, rule IDs, the ET session and bar model), the option RIC builder and parser, the LSEG adapter (session check and fail-soft history, tested against a fake that a contract test keeps true to lseg-data), batched requests (single-RIC verdicts, retries and the caret→live fallback), the NYSE session calendar (2025–2027, checked against each stock's trading days), chain discovery (strike increments, integer-cent strike bands, the fetch plan), `pmcc probe`, the raw cache and its loader (one parquet and sidecar per fetch unit, never overwritten), and `pmcc fetch` (an estimate before any option request, a resumable unit loop, a coverage summary) are in. The PO has reviewed the probes' reports and set the backtest window, the risk-free rate and each symbol's RICs in `configs/universe.yaml`. NVDA's full option chain over the window is cached (P1-09) and committed (DEC-05); QQQ and TSLA are set aside for now (P1-10 paused, DEC-15). Pricing (P2) is in: Black-Scholes and Greeks, a vectorized IV solver, the measures the rules read (ATM IV, expected move, RV20) and a chain pricer that prices NVDA's whole window in about 1.4 s; `pmcc fetch`'s coverage summary now counts IV failures. The strategy config is in (P3-01): `configs/_shared.yaml` and `configs/baseline_pmcc.yaml` hold every baseline rule with its thresholds and write-up, and the loader validates each rule's params and text, resolves `extends` and `overrides`, and hashes the result. The engine is in (P3-02 to P3-07): the look-ahead-proof `MarketView`, the accounting core (blotter events, book, marks, NAV, Reg T), the fill simulator, the baseline's rules and the bar loop with its gate log and runtime invariants, tested end to end on a synthetic market. `pmcc run` (P3-08) writes one run's result, `results/{SYM}/{run_id}.json`, as canonical JSON with its run manifest (the commit and whether the tree was dirty, the config, data and lockfile hashes); it takes the starting cash from `configs/universe.yaml`. `pmcc calibrate` (P3-09) sets that value to twice the most expensive first long-leg entry, rounded up to $5,000, checks that it covers every entry, and writes it there with its basis: $15,000, final, from NVDA under both strategies (quant's first long sets it; P5-01, DEC-30). The baseline on NVDA (P3-10) is run and committed, `results/NVDA/baseline_pmcc.json` (35 trades over 26 weeks; $10,000 to $13,672.50 then, re-run at $15,000 at P4-04), hand-audited against the raw quotes (DEC-94): milestone M1. The quant layer's rules and configs are in (P4-01 to P4-03, DEC-95): the cheapest-replacement long leg, the expected-move short strike and gates G-3 to G-5, with `configs/quant_pmcc.yaml` and the five ablations in `configs/ablations/`. They're run on NVDA and reviewed (P4-04): `results/NVDA/` holds quant and A1–A5 beside the baseline, re-run at the recalibrated $15,000 ($15,000 to $18,672.50 for the baseline, $18,303.50 for quant). `pmcc verify` and `pmcc export` are in (P4-05, DEC-96): verify re-derives the runtime invariants from each committed result's rows and runs in CI, and export writes the site's data with a JSON Schema per file. Strategies' results keep every row and ablations' a summary (DEC-54); NVDA's seven results are re-run at the new schema and pass `pmcc verify`. The site's scaffold is in `web/` (P4-06, DEC-97): Vite, React and TypeScript, the baseline terminal look with its tokens (one dark theme, DEC-03), types generated from the schema, and every page's route as a placeholder until P7. `pmcc batch` is in (P5-01 to P5-03, DEC-100): the universe is NVDA alone for now, QQQ and TSLA commented out (DEC-15); `configs/sensitivity.yaml` adds the friction, entry-timing and parameter-grid variants, 24 runs per symbol; the batch runs them one process per symbol and writes each symbol's data-coverage file. The full batch is run and committed (P5-04): `results/NVDA/` holds all 24 runs and `coverage.json`, verified (milestone M3). Their data completeness is reviewed (P5-05, DEC-08): no pick sits on the edge of the strikes fetched, so nothing was refetched. The analytics are under way (P6, DEC-101): every run's summary now carries its performance metrics, cycle statistics and a seeded bootstrap CI of its mean weekly return, and the batch writes each symbol's robustness tables and the universe's headline and pooled files, as the PO defined each number (DEC-60 to DEC-65). The committed results predate them until P6-09 re-runs the batch. The build runs Sep 26 – Oct 9, 2026, tracked in [docs/BUILD-PLAN.md](docs/BUILD-PLAN.md).
> - The commands under Usage are the interface defined in the spec. `pmcc probe`, `pmcc fetch`, `pmcc run`, `pmcc batch`, `pmcc calibrate`, `pmcc export` and `pmcc verify` work; until its backlog item lands, each other command exits with code 1 and names that item.
> - The site: **<https://jason-dorman.github.io/pmcc-strategy/>**, deployed by CI from `main` once a Playwright smoke test has loaded every page (P4-07, P4-08). Until P7 its pages are placeholders over the committed NVDA results.

## What the results answer

- Does the quant PMCC beat the fixed-rule baseline, per symbol and pooled, after honest costs?
- Which quant layers earn their complexity? Five ablation runs each switch one layer off.
- Does the answer survive friction, entry timing and parameter changes?
- Which symbols suit a PMCC at all?

## The two strategies

| | Baseline PMCC | Quant PMCC |
| --- | --- | --- |
| Long leg | Monthly expiry nearest 180 DTE; strike with delta nearest 0.80 | Any monthly expiry 120–270 DTE; among 0.70–0.90 delta strikes, the least extrinsic value per unit of delta |
| Short leg | Weekly; OTM strike with delta nearest 0.30 | Weekly; lowest listed strike at or above spot + 1.0 × the expected move |
| Skip-week gates | Liquidity (G-1) and structural constraint (G-2) | G-1, G-2, plus event week (G-3), volatility risk premium (G-4), minimum premium (G-5) |
| Exits | Identical for both: take profit, defensive close, Friday check, expiry and missed assignment, long-leg reset and roll | |

- **Traceable rules.** Every rule has a stable ID (`E-S3`, `G-4`, `X-S5`, …), and its thresholds live in YAML. Every trade on the blotter names the rule that fired it.
- **Where to read them:** the full rules are in the [spec](docs/PMCC-Backtest-System-Spec.md) and on the site's Trade rules page. That page is generated from the same config the engine runs.

**Universe:** NVDA for now. QQQ and TSLA, an index ETF and a second single name that widen the volatility range, are set aside and may join it at the end (DEC-15). Every symbol is backtested on one common window of hourly bars, Mar 30 – Sep 25 2026 (26 weeks). The risk-free rate is 3.71%, continuously compounded, from the 3-month Treasury yield at the last close before the window (3.73%).

## How the results stay honest

- **No look-ahead, by construction.** Strategies never see raw data. They get a `MarketView` that raises an error on any request for data after the decision time.
- **Real quotes only.** Fills happen at the mid of an actual bid and ask on the decision bar. No quote means no fill. Stale marks are flagged and never trade.
- **Accounting that reconciles.** Every strategy has a blotter, a per-bar ledger, NAV, and Reg T margin.
  - 15 invariant tests gate CI: cash, NAV, coverage, look-ahead, margin, reproducibility and more.
  - The accounting invariants are also checked on every bar of every backtest.
- **Uncertainty is shown.** Small-sample statistics carry bootstrap confidence intervals. Sensitivity results are published in full, never as a best-case pick.
- **Every number traces back.** Each result carries a manifest (git commit, config hash, data hash, lockfile hash), shown in the footer of every page.

## Requirements

- **[uv](https://docs.astral.sh/uv/),** which installs Python 3.12 (from `.python-version`) on the first sync.
- **[just](https://just.systems):** `uv tool install rust-just` installs it.
- **git, with Git Bash on Windows.**
- **Node.js 22 LTS with npm,** for the site (`web/`; pinned by `web/.nvmrc`).
- **LSEG Workspace,** only for fetching data. It must be running and signed in on the same Windows machine, because the LSEG desktop session connects to it locally.

Development runs in Git Bash on Windows, and CI runs the same checks on Ubuntu. Keep the clone on a Windows path, not `\\wsl.localhost\…`. Backtests, tests and the site build never contact LSEG.

If uv fails with `invalid peer certificate: UnknownIssuer`, check for a stale `SSL_CERT_FILE` left by a conda activation (`echo $SSL_CERT_FILE`) and `unset SSL_CERT_FILE`, or start the terminal without conda activated.

## Setup

In Git Bash:

```bash
git clone git@github.com:Jason-Dorman/pmcc-strategy.git
cd pmcc-strategy
just setup        # uv sync, npm ci in web/, pre-commit hooks
just check        # lint, format check, pyright, pytest, then the site's lint, typecheck and tests
```

LSEG credentials go in `lseg-data.config.json` in the repo root. The file is gitignored; never commit or share it. Its shape:

```json
{ "sessions": { "default": "desktop.workspace",
                "desktop": { "workspace": { "app-key": "<your app key>" } } } }
```

## Usage

```bash
uv run pmcc probe  --symbol NVDA                                       # LSEG spikes → data_cache/probes/ (Workspace required)
uv run pmcc fetch  --symbol NVDA --start 2026-07-06 --end 2026-09-18   # LSEG → local cache (Workspace required)
uv run pmcc fetch  --symbol NVDA --start 2026-03-30 --end 2026-09-25 --plan-only   # the estimate: asks LSEG for the stock tape only, writes nothing (Workspace required)
uv run pmcc calibrate --check   # recompute the starting cash (every symbol × both strategies) and compare; writes nothing
uv run pmcc calibrate           # write it into configs/universe.yaml; refuses while a final value is there (DEC-30)
uv run pmcc run    --symbol NVDA --config configs/baseline_pmcc.yaml    # one backtest, from the cache only → results/NVDA/baseline_pmcc.json
uv run pmcc run    --symbol NVDA --config configs/ablations/a3.yaml     # a quant ablation → results/NVDA/quant_pmcc--a3.json
uv run pmcc batch  --universe configs/universe.yaml                     # every symbol × strategy × variant
uv run pmcc verify results/                                             # re-derive the invariants from the results; refuses a dirty tree's
uv run pmcc export --out web/public/data/                               # results → site data + JSON Schema (refuses results verify fails)
uv run pmcc export --schema-only --out web/public/data/                 # just the JSON Schema, which the site's types come from
just web-dev                                                            # export, then the site on Vite's dev server
just web-build                                                          # export, then the static site in web/dist and the dist guard
just e2e                                                                # build, then the Playwright smoke test over every page
just reproduce                                                          # cached data → all runs → verify → export → built site
```

`just --list` shows every recipe.

## Reproducing the published results

Results are committed in `results/`, and so is the raw LSEG cache they ran on: NVDA's, in `data_cache/NVDA/` (DEC-05). Re-running them needs no LSEG access:

- `just run NVDA configs/baseline_pmcc.yaml` re-runs one result. Re-running a configuration on the same cached data produces byte-identical results, apart from each manifest's run time and commit.
- `just verify` checks the committed results without the cache: their schema, a clean tree, and the invariants re-derived from each full result's rows.
- `just reproduce` re-runs every configuration on the cached data, verifies the results, exports them and builds the site. `pmcc batch` writes every symbol's 24 runs, `coverage.json` and `robustness.json`, then `universe/headline.json` and `universe/pooled.json`, and exits 1 if anything failed.

To add a symbol, or to build a cache from LSEG:

0. If `configs/universe.yaml` holds a final starting cash, recalibrate around the fetch, in this order: delete the final `starting_cash` block, its header comment included (the file refuses a final block that lacks a listed symbol, and `pmcc fetch` reads this file, so it would stop); uncomment the symbol; finish its fetch (P1-10: show the PO the estimate first); run `just calibrate`; then re-run every result (`just batch`), since the value may change (DEC-15). QQQ and TSLA are commented out there, ready to uncomment.
1. Fetch it into `data_cache/` with `pmcc fetch`. This needs LSEG access. Each symbol needs its probe report first (`pmcc probe`), whose strike steps feed the estimate; `--plan-only` prints the estimate after asking LSEG for the stock tape only. The window's `--start` and `--end` must both be sessions. If a fetch stops (Workspace signs out, say), run the same command again: it picks up at the first unit not yet cached.
2. Add `!data_cache/{SYM}/` to `.gitignore` and commit the cache with the symbol's results. Until it's committed, the uncommitted cache makes every run's tree dirty.

Each result's manifest records the commit, config, data manifest and lockfile that produced it, and whether the working tree had uncommitted changes (`git_dirty`, ignoring `results/`). Commit the code before a publishable run: `pmcc verify` rejects dirty results (DEC-50).

## Repository layout

```
pmcc/        Python package: data (LSEG adapter, cache), pricing, strategy, engine, accounting, analytics, export, cli
configs/     strategy, ablation, sensitivity, universe and calendar YAML
results/     committed results JSON, per symbol and per run
web/         Vite + React + TypeScript site
tests/       pytest + hypothesis
docs/        the spec and the build docs
```

## Documentation

| Doc | What it's for |
| --- | --- |
| [System spec](docs/PMCC-Backtest-System-Spec.md) | The source of truth: what gets built and how |
| [PRD](docs/PRD.md) | Purpose, users, requirements, release criteria |
| [Architecture](docs/ARCHITECTURE.md) | Packages, interfaces, data plan, results contract, CI |
| [Build plan](docs/BUILD-PLAN.md) | Phased backlog, status board, cut list, risks |
| [Decisions](docs/DECISIONS.md) | Open questions, PO answers, engineering choices |
| [Test strategy](docs/TEST-STRATEGY.md) | How the 15 invariants and every rule are tested |
| [UI spec](docs/UI-SPEC.md) | Page layouts and the visual system |
| [Engineering principles](docs/ENGINEERING-PRINCIPLES.md) | How the code is written |

**Reference material:**
- `LSEG-DATA-GUIDE.md` and `lseg_client.py`: getting data out of LSEG.
- `DESIGN-GUIDE.md` and `theme.py`: the baseline look.

## Data

Market data comes from LSEG Workspace under the author's access. The repository holds code, configuration, derived results, and the raw cache of each symbol in the published results, so anyone can re-run them: NVDA's for now (DEC-05). Other symbols' caches stay on the author's machine until they're published.
