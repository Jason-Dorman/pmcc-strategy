# PMCC Backtest — Test Strategy

Sep 25, 2026 · implements Spec › Invariant tests and EP › Testing mindset · see [ARCHITECTURE](ARCHITECTURE.md) and [DECISIONS](DECISIONS.md)

## 1. Rules

- **Tests come first.** A backlog item is done only when its tests exist and pass (EP › Testing mindset).
- **Tests are never cut** (Spec › Build order).
- **Tests never touch the network.**
  - An autouse fixture in `tests/conftest.py` blocks sockets: connect, `create_connection` and `getaddrinfo` raise, localhost included (DEC-77).
  - LSEG code is tested through `FakeProvider`.
  - CI has no cache and no credentials, and it must still prove every invariant (DEC-51).
- **Tests are deterministic.**
  - Fixed seeds everywhere.
  - Hypothesis profiles: `dev` (50 examples) and `ci` (300 examples, derandomized), chosen by `HYPOTHESIS_PROFILE` (default `dev`).
- **One behaviour per test.** Name tests `test_<rule-or-inv>_<behaviour>`, e.g. `test_x_s3_fires_within_quarter_em_of_strike`.

## 2. Layers

| Layer | Covers | Tool | Runs in |
| --- | --- | --- | --- |
| Unit | RIC grammar, calendar, bands, Black-Scholes, IV, measures, selectors, trigger, gates, exits, fills, Reg T, metrics | pytest | `just test`, CI |
| Property | Accounting invariants (INV-01, 02, 08, 10); IV vs scalar reference; MarketView as-of guard (INV-04); RIC round-trip (INV-11); integer strike ladders | hypothesis | CI |
| Scenario | Engine end to end on a synthetic market: one scenario per exit, gate and edge case (§5) | pytest | CI |
| Determinism | The same synthetic run twice gives byte-identical files (INV-13) | pytest | CI |
| Architecture | Import boundaries (ARCHITECTURE §3.3) | pytest (AST) | CI |
| Config | Rule IDs unique and complete; placeholders resolve; every param referenced; each ablation differs from quant only in its layer | pytest | CI |
| Results | Schema check plus invariants re-derived from committed results (DEC-51) | `pmcc verify` | CI |
| Runtime | Invariants checked every bar of every real run; a failure writes nothing | engine | every run |
| Frontend unit | Formatters, transforms, token-lint, contrast | Vitest | CI |
| Types | `tsc` against types generated from the current schema (INV-14) | tsc | CI |
| Smoke | Every route for one symbol; no console errors; no cross-origin requests; footer present; screenshots | Playwright (Node) | CI |
| Data acceptance | answered + unanswered = requested; mid coverage; holiday weeks; spot checks against Workspace | fetch summary + manual | local, per fetch |

## 3. Invariant matrix

Numbering follows Spec › Invariant tests.

| INV | Statement (short) | Enforced by | Where |
| --- | --- | --- | --- |
| 01 | Cash changes only on blotter rows; Σ Cash Δ = Δ cash | runtime · property · verify | `tests/property/test_accounting_invariants.py`; `pmcc verify` |
| 02 | NAV = cash + long MV − short call MV + stock MV, every bar | runtime · property · verify | same |
| 03 | No fill without a valid BID and ASK on the decision bar | runtime · unit · verify | `tests/unit/engine/test_fills.py`; `pmcc verify` (audit bid/ask, fill = mid ± capture·half) |
| 04 | No decision reads data stamped after its decision time; MarketView raises | unit · property | `tests/property/test_market_view.py` |
| 05 | Every short is covered: long strike ≤ short strike, long expiry ≥ short expiry, equal quantities | runtime · scenario · verify | `tests/scenario/`; `pmcc verify` |
| 06 | Every short entry satisfied E-S5 at its decision bar | runtime · unit · verify | `tests/unit/strategy/test_constraint.py`; `pmcc verify` (E-S5 terms in the audit) |
| 07 | No short call is open after its expiry session | runtime · scenario · verify | `tests/scenario/test_expiry.py`; `pmcc verify` |
| 08 | Available funds ≥ 0 at every entry decision | runtime · property · verify | property tests; `pmcc verify` (post-trade funds in the audit) |
| 09 | Every blotter and gate-log row carries a valid rule ID from the config | runtime · config · verify | `tests/unit/config/`; `pmcc verify` |
| 10 | Short qty = long qty whenever a short is open | runtime · property · verify | property tests; `pmcc verify` |
| 11 | The RIC builder round-trips known examples (as amended by DEC-01) and emits no caret for live contracts | unit · property | `tests/unit/data/test_ric.py` |
| 12 | Missing RICs return empty series, never exceptions | unit | `tests/unit/data/test_fetch.py` (FakeProvider) |
| 13 | Re-running a config on cached data gives byte-identical results (ignoring `run_timestamp`) | determinism test (synthetic, CI) · P8-01 (real, local) | `tests/scenario/test_determinism.py`; `just reproduce` |
| 14 | The frontend type-checks against types generated from the current schema | `gen:types` + `tsc` | CI web job |
| 15 | The Playwright smoke test loads every page for one symbol with no console errors | Playwright | `web/e2e/smoke.spec.ts` |

INV-01, 02, 08 and 10 also run as hypothesis property tests over random sequences of fills, expiries, assignments and marks (Spec › Invariant tests). The generator must include:

- stale marks
- the X-S5 path (ASSIGN, then a short-stock SELL, then the next session's BUY)
- `spread_capture` values that produce sub-cent fills (these test DEC-44's exactness)

## 4. Rule coverage

Every rule ID needs at least:

- **boundary unit tests:** just inside and just outside each threshold, plus ties (DEC-29) and missing inputs
- **one scenario test** in which it fires during a full run

| Rule | Unit focus | Scenario |
| --- | --- | --- |
| E-T1 | Spread ≤ 3% (long) and ≤ 10% (short) of mid; no quote = fail | first bar fails, a later bar passes |
| E-L1 | Retry the next session after an E-T1 failure | long enters on day 2 |
| E-L2 | Nearest 180 DTE (baseline); 120–270 DTE range (quant) | — |
| E-L3 | δ nearest 0.80; lowest extrinsic ÷ δ with tie-breaks | — |
| E-L4 | Funds check blocks the entry, and it's logged | underfunded account |
| E-S1 | Week-open only; needs a long and no short; Tuesday after a Monday holiday | Labor Day week |
| E-S2 | Expiry = the week-final session (Thursday when Friday is a holiday) | Jul 3 week |
| E-S3 | 0.30 δ OTM (baseline); lowest listed strike ≥ spot + k·EM (quant); listing is point-in-time | — |
| E-S4 | Short qty = long qty | — |
| E-S5 | Strict inequality at the boundary; uses the long's entry fill, not its mark | expensive long → G-2 |
| G-1 | Frozen contract never passes E-T1 | no valid quote all Monday |
| G-2 | E-S5 fails | as above |
| G-3 | Ratio > threshold fires; missing next-week IV = `n/a` | front-week IV bump |
| G-4 | IV ÷ RV20 < threshold fires | RV above IV |
| G-5 | Mid < $0.10 fires | tiny premium |
| X-S1 | Mid ≤ 25% of credit, before the Friday check only | premium collapse |
| X-S2 | δ > 0.60 on any bar; δ := 1 when mid is below the floor (DEC-27) | rally through the strike |
| X-S3 | Check bar is the last session bar ending ≤ 15:00 ET; buffer uses EM from entry; delayed fill (DEC-28) | Friday within the buffer |
| X-S4 | OTM at close → EXPIRE at $0 | quiet week |
| X-S5 | ITM at close → ASSIGN + short-stock SELL; cover the next session; Reg T short-stock margin | late-Friday surge |
| X-L1 | δ < 0.50 at week-open → sell, re-enter, then short entry | drop through the long's delta |
| X-L2 | DTE < 90 at week-open → roll | long crossing 90 DTE |
| X-E1 | Final marks; no liquidation | window ends mid-week |

## 5. Synthetic market (`tests/fixtures/synthetic/`)

A deterministic generator writes a dataset in the **cache format** (same parquet schema and manifest), so the loader, pricing and engine are tested exactly as they run on real data.

**Underlying**

- An hourly tape from a seeded random walk.
- A session calendar with a Monday holiday, a Friday holiday and a half-day.
- Configurable drift and volatility.

**Option chains**

- Weekly and monthly calls, plus ATM puts, priced by Black-Scholes from a configurable IV surface.
- The surface supports an event bump in the front week, for G-3.

**Market microstructure**

- Bid/ask spreads as a % of mid, with configurable widening for deep ITM and long-dated contracts.
- Missing quotes (holes).
- Trade prints on a fraction of bars (mid plus noise).

**Scenario builders**

Each builder scripts the spot path and quotes to force one behaviour:

- every exit rule
- gates G-1…G-5
- E-L4 underfunding
- stale marks
- negative available funds after X-S5
- the half-day close

**Other uses**

- The INV-13 determinism test.
- The P4 sample site, which runs on synthetic results under `data_source: synthetic` and therefore shows the banner.

## 6. FakeProvider

`FakeProvider` implements `HistoryProvider` and scripts every LSEG behaviour from LDG §4:

- per-RIC answers and never-listed RICs (`No data`)
- a whole batch rejected because of one bad RIC (including the `UniverseContainer` TypeError)
- partial answers that raise nothing
- each response shape: MultiIndex in either order, flat fields, flat RICs
- a requested field the RIC doesn't carry → `LDError` for the whole request
- a closed session, transient timeouts that recover, and a sustained outage
- a contract that answers only to the live form, or only to the caret form

It also records every request, so tests can assert batch sizes, retry order and that nothing was requested before the session opened.

## 7. Where tests run

Local commands run in Git Bash on Windows, and CI runs on Ubuntu. The same suite must pass on both (DEC-58).

| Command | Runs |
| --- | --- |
| pre-commit | ruff, ruff-format, pyright, guards (fast; on staged files) |
| `just test` | pytest (dev profile) |
| `just check` | pre-commit on all files + pytest + web lint, typecheck and Vitest |
| CI | everything above (ci profile), plus `pmcc verify`, the web build, the dist guard and the Playwright smoke test |
| `just reproduce` | local, with the cache: batch → verify → INV-13 on real data → export → web build |

## 8. Manual checks

A manual check's result is recorded in the done note of its backlog item.

| Check | When | What |
| --- | --- | --- |
| Data acceptance (LDG §7) | each fetch (P1-09, P1-10) | Spot-check 5 rows per symbol against Workspace. Near-the-money weekly mid availability ≥ 90% (or explained). Holiday weeks look right. Read the diagnostic errors. |
| Trade audit | P3-10, P4-04 | Hand-trace 3 weeks per strategy: blotter row → ledger → raw quotes in the cache, and confirm each rule's triggering values |
| Site read-through | P7-08 | Every page in both themes at 390, 1100, 1366 and 1600 px. Every number traceable. No placeholder text. No synthetic banner on real results. |
