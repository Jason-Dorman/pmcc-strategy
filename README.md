# PMCC Backtest

A symbol-agnostic backtester for the **Poor Man's Covered Call** (PMCC): a deep in-the-money, long-dated call held as a stock substitute, with weekly out-of-the-money calls sold against it. One engine runs two strategies, a fixed-rule baseline and a quant variant, on LSEG hourly data, and publishes the results as a static site on GitHub Pages.

> **Status:** foundations (P0) are in place: toolchain, quality gates, CI, logging and import-boundary tests. The build runs Sep 26 – Oct 9, 2026, tracked in [docs/BUILD-PLAN.md](docs/BUILD-PLAN.md).
> - The commands under Usage are the interface defined in the spec. Until its backlog item lands, each one exits with code 1 and names that item.
> - The site link will be added at the first deploy.

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

**Universe:** SPY, QQQ, IWM, AAPL, NVDA, AMD, META, TSLA, COIN, JPM, TLT, XLE, backtested on one common window of at least 10 weeks of hourly bars.

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
- **Node.js 22 LTS with npm,** for the site (`web/`, from build item P4-06).
- **LSEG Workspace,** only for fetching data. It must be running and signed in on the same Windows machine, because the LSEG desktop session connects to it locally.

Development runs in Git Bash on Windows, and CI runs the same checks on Ubuntu. Keep the clone on a Windows path, not `\\wsl.localhost\…`. Backtests, tests and the site build never contact LSEG.

If uv fails with `invalid peer certificate: UnknownIssuer`, check for a stale `SSL_CERT_FILE` left by a conda activation (`echo $SSL_CERT_FILE`) and `unset SSL_CERT_FILE`, or start the terminal without conda activated.

## Setup

In Git Bash:

```bash
git clone git@github.com:Jason-Dorman/pmcc-strategy.git
cd pmcc-strategy
just setup        # uv sync, npm ci in web/ (once it exists), pre-commit hooks
just check        # lint, format check, pyright, pytest (and the web checks, once web/ exists)
```

LSEG credentials go in `lseg-data.config.json` in the repo root. The file is gitignored; never commit or share it. Its shape:

```json
{ "sessions": { "default": "desktop.workspace",
                "desktop": { "workspace": { "app-key": "<your app key>" } } } }
```

## Usage

```bash
uv run pmcc fetch  --symbol NVDA --start 2026-07-06 --end 2026-09-18   # LSEG → local cache (Workspace required)
uv run pmcc run    --symbol NVDA --config configs/quant_pmcc.yaml       # one backtest, from the cache only
uv run pmcc batch  --universe configs/universe.yaml                     # every symbol × strategy × variant
uv run pmcc export --out web/public/data/                               # results → site data + JSON Schema
just reproduce                                                          # cached data → all runs → export → built site
```

`just --list` shows every recipe.

## Reproducing the published results

Results are committed in `results/`. Raw LSEG data is not. To reproduce from scratch:

1. Fetch the universe into `data_cache/` with `pmcc fetch`. This needs LSEG access.
2. Run `just reproduce`. It re-runs every configuration on the cached data, verifies the results, exports them and builds the site. Re-running a configuration on the same cached data produces byte-identical results.

Each result's manifest records the commit, config, data manifest and lockfile that produced it.

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

Market data comes from LSEG Workspace under the author's access. Raw data isn't redistributed here; the repository holds code, configuration and derived results only.
