# Wheel Backtest — Build Plan and Backlog

Oct 26, 2026 · from the [Wheel spec](WHEEL-SPEC.md) · **due Sun Nov 1 2026, 11:59 pm ET** (WD-13; submit target 18:00) · the PMCC's finished plan is archived in [archive/pmcc/BUILD-PLAN.md](archive/pmcc/BUILD-PLAN.md)

## How to use this plan

- **Order:** take the first unchecked item whose **Needs** are all checked, unless the PO says otherwise.
- **Ask first:** when picking up an item, put its **Ask first** questions to the PO in one message, each with the recommendation from [DECISIONS](DECISIONS.md), and ask the next item's while finishing the current one. Record every answer in DECISIONS.
- **Done means:** the **Done when** line holds, `just check` is green, every doc the work touched is updated, and the work is handed to the PO with its file list and a proposed commit message (`W1-01: …`). The PO commits.
- **Ticking:** `- [x] **W1-01 · …** — done YYYY-MM-DD; notes`, in the same commit as the work.
- **Tags:** **[PO]** needs a PO answer or review; **[Workspace]** needs LSEG Workspace signed in on the PO's machine.
- **Not overdoing it (WD-01, WD-05):** each item builds what the spec asks for and no more. The PMCC's code is reused where it fits; it's generalized only as far as the wheel needs, and the PMCC's results must not change.

## Status board

| Phase | Dates | Exit criteria | Status |
| --- | --- | --- | --- |
| W0 Docs and thesis | Mon Oct 26 | Wheel spec, decisions and backlog live; PMCC docs archived; thesis fixed | Done 2026-10-26: thesis fixed (WD-21), due date (WD-13), fills at mid (WD-23) |
| W1 Data | Mon Oct 26 – Tue Oct 27 | NVDA weekly puts cached; S&P closes committed | Done 2026-10-26: 26 weeks of puts cached, the −0.30-delta strike validly quoted on 93.6% of bars to expiry (W1-02); S&P closes committed (W1-03) |
| W2 Engine and rules | Tue Oct 27 – Thu Oct 29 | The wheel runs on NVDA: blotter, ledger, NAV, gate log; invariants hold; one cycle hand-audited | Done 2026-10-27: W2-01 and W2-02 (WD-24, WD-25); W2-03, `pmcc wheel` and its verified result file, the Jun 1 – Jul 10 cycle hand-audited with 0 discrepancies (WD-26, WD-27). Next: W3-01 |
| W3 Results and analytics | Fri Oct 30 | Wheel result and friction runs committed and verified; metrics and benchmarks | Done 2026-10-28: W3-01 to W3-03 (WD-20, WD-28 to WD-31); `results/NVDA/wheel.json` and the two friction runs run from a clean tree at `8abed76` and verified. Next: W4-01 |
| W4 Site | Sat Oct 31 | Wheel pages live on GitHub Pages; thesis verdict shown | In progress 2026-10-28: W4-01's pages built to the PO's answers (WD-22, WD-32), `just check` and the smoke test green; waiting on the PO's read-through |
| W5 Release | Sun Nov 1 | Reproduced from a clean tree; submitted by 18:00 (deadline 23:59 ET) | Not started |

**Critical path:** the data is in (W1) and weekly tenor is confirmed (WD-02, 2026-10-27), so it now runs through W4-01's pages, the last item the PO's review gates before release.

**Cut order if time runs short** (the PO confirms each cut; the bootstrap CI, Sortino and time underwater are already cut, WD-20): the friction runs at 0.25 (keep 0.50) → the portfolio view as a picker (fall back to a filterable ledger, which still shows the portfolio at every bar). **Never cut:** the blotter, the ledger, the portfolio at any bar, the mid-vs-print evidence, the thesis and its verdict, the benchmark table, the invariant tests.

## Questions for the PO

| When | Asks |
| --- | --- |
| W4-01 | WD-22 (pages) |

## Backlog

### W0 — Docs and thesis

- [x] **W0-01 · Archive the PMCC docs; write the wheel's** **[PO]** — done 2026-10-26; the PO settled WD-01 to WD-10, WD-13 (due Nov 1), WD-21 (thesis kept) and WD-23 (fills at mid); weekly tenor provisional (WD-02)
  - Move the PMCC's spec, PRD, ARCHITECTURE, TEST-STRATEGY, UI-SPEC, BUILD-PLAN and DECISIONS to `docs/archive/pmcc/`; repoint the two tests that read its spec; write WHEEL-SPEC, DECISIONS, this plan and the styling-only UI-SPEC; update CLAUDE.md and README.
  - Ask first: WD-13 (settled: Nov 1), WD-21.
  - Done when: the PO has reviewed the spec and fixed the thesis; `just check` is green.

### W1 — Data

- [x] **W1-01 · Wheel put fetch plan** — done 2026-10-26; `plan_wheel_puts`, `prepare_wheel`, `SymbolCache(part=...)` and `pmcc fetch --wheel` (WD-11); 18 tests; the real plan-only estimate shown to the PO: 26 units, 710 strikes, 970–2,910 requests, about 23–67 min
  - A fetch plan for the wheel's weekly puts (WD-11's band), written to `data_cache/NVDA/wheel/` with its own manifest, reusing the PMCC's fetch loop, RIC builder and cache format. `--plan-only` prints the estimate. The PMCC's plan and cache are untouched.
  - Done when: tests cover the band, the unit dates and the separate manifest; the estimate is shown to the PO.
  - Needs: W0-01
- [x] **W1-02 · Pull NVDA's weekly puts** **[Workspace]** **[PO]** — done 2026-10-26; 26 units in 14 min, 1.3 MB in `data_cache/NVDA/wheel/` (the PO commits it); the −0.30-delta put validly quoted on 93.6% of its session bars to expiry (the rest zero bids late in the week, marked stale), spreads 0.5–2.7% at entry, never near the band's floor (WD-11)
  - Run the pull after the PO approves the estimate. Report coverage: for each week, the share of bars with a valid quote at the strikes near −0.30 delta.
  - Done when: every weekly expiry's puts are cached, coverage is reported, and the cache is committed (by the PO).
  - Needs: W1-01
- [x] **W1-03 · S&P 500 closes** **[PO]** — done 2026-10-26; `configs/benchmarks.yaml` (FRED SP500: 6,368.85 on Mar 27, 7,743.41 on Sep 25) and its reader `pmcc/wheel/benchmarks.py`, which checks the closes bracket the window; 7 tests
  - Ask first: WD-17 (settled 2026-10-26: FRED SP500).
  - Done when: the two closes are committed with their citation and loaded by a tested reader.
  - Needs: W0-01

### W2 — Engine and rules

- [x] **W2-01 · Accounting for puts and shares** — done 2026-10-26; the wheel's own book and valuation, `pmcc/wheel/book.py` (WD-24), beside the PMCC's, which is untouched; `RuleId` takes `W-` IDs (WD-12); 23 unit tests (`tests/unit/wheel/test_wheel_book.py`) and a hypothesis walk (55% of runs reach expiry, 47% a put assignment, 10% a call-away). Its questions moved to W2-02, which is the first item that needs them
  - A wheel book holds one short put (cash-secured) or 100 shares with one covered call, enforcing invariants 5–7; `ASSIGN` books shares at the strike. The PMCC's book rules still apply to PMCC runs.
  - Done when: hypothesis property tests hold invariants 1, 2, 5, 6 and 7 over random event sequences; every PMCC test still passes.
  - Needs: W0-01
- [x] **W2-02 · Wheel config and rules** — done 2026-10-26; `configs/wheel.yaml`, `pmcc/wheel/config.py`, `rules.py`, `engine.py`, `market.py` (WD-24); 27 config and rule tests at their boundaries and 15 scenarios; on NVDA it runs in 0.2 s with every invariant held. WD-25's rule details put to the PO. Then an adversarial review of W0-01 to W2-02 (4 reviewers, 2 skeptics per finding; WD-24): 8 confirmed and 2 plausible findings, all fixed, with the unverified lows. Nothing high: the PMCC's results and the wheel's NVDA numbers stood. The fixes add the runtime checks module and the market's missing-week check, mark assigned shares at the closing trade (WD-25 #4), let a W-P4 refusal retry on later bars, and add tests for every gap the review's surviving mutants showed: 13 more scenarios (28), 7 runtime-check tests that make each invariant fire, and unit tests for the OTM call filter, the stale flags, the missing-week check, late benchmark dates and the week-open band. The wheel now has 102 tests, and the 22 mutants re-run against them (the review's survivors and their kin) are all killed
  - Ask first: WD-14, WD-15, WD-16, WD-18, WD-19 (all settled 2026-10-26, as recommended).
  - `configs/wheel.yaml`: every rule (W-T1 … W-X5) with its thresholds and write-up text; the state machine; the put and call selectors; expiry settlement; the gate log.
  - Done when: each rule has tests at its boundaries, and a synthetic market drives the wheel through every state and transition.
  - Needs: W2-01
- [x] **W2-03 · Run the wheel on NVDA** **[PO]** — done 2026-10-27; `pmcc wheel` (`just wheel NVDA`, also in `just reproduce`) writes `results/NVDA/wheel.json`, a `WheelResult` whose invariants `pmcc verify` re-derives from its rows, and which `pmcc export` holds back until W4-01 (WD-26). On NVDA: 61 rows over 26 weeks, every week sold, 4 complete cycles, $25,000 to $29,171.50; committed at W3-03 from a clean tree. Every put and call picked was covered by the cache (no week skipped under W-C3, no call pull needed). The PO picked and accepted the hand audit of May 26 and the Jun 1 – Jul 10 cycle: 3,898 checks, 0 discrepancies, after it found WD-27 (delta ±1 under the floor, PO). WD-02 confirmed: weekly. The PMCC's 31 result files are unchanged (a scratch batch)
  - A `pmcc wheel --symbol NVDA` command (the PMCC's `pmcc run` rejects the wheel's config: WD-24) that writes `results/NVDA/wheel.json` with its run manifest; then check the call coverage of every strike the wheel picked and of every week skipped under W-C3, and hand-audit a full cycle against the raw quotes with the PO.
  - Done when: the result passes every invariant and the audit.
  - Needs: W1-02, W2-02

### W3 — Results and analytics

- [x] **W3-01 · Metrics and benchmarks** **[PO]** — done 2026-10-28; the result's summary holds the metrics (trimmed, WD-20), the cycle statistics (a complete cycle runs from assignment to call-away, WD-29), the benchmark table against the baseline PMCC's committed result and the S&P 500, and each claim's verdict by the tests WD-29 fixed before any was computed; each blotter row has its Trade P&L (WD-28). `pmcc verify` re-derives each and checks the baseline's figures against its file (WD-30). On NVDA: +$4,171.50 (16.69%), Sharpe 1.574 against the PMCC's 1.242, S&P 500 21.58%: claims 1 and 2 met, 3 not
  - Ask first: WD-20; the blotter's Trade P&L; complete cycles and the verdict tests (all settled 2026-10-27: WD-20, WD-28, WD-29).
  - Performance, wheel-cycle statistics and the weekly-return CI; the benchmark table against the baseline PMCC and the S&P 500; each thesis claim's verdict.
  - Done when: every number the wheel pages need is in the results JSON.
  - Needs: W2-03, W1-03
- [x] **W3-02 · Fill justification** — done 2026-10-28; every wheel result holds its fill evidence: each sold option's prints against its mids from sale to expiry, puts and calls, fitted as the PMCC's fill check is (WD-31). The friction runs are `configs/wheel_friction/sc025.yaml` and `sc050.yaml`, variants that extend the wheel (`just wheels NVDA`, in `just reproduce`). On NVDA: 825 pairs, R² 0.9994, 89% of prints inside the quote, the median at the bid or ask; paying half the spread costs $17.25 of $4,171.50 and changes no verdict. All three wheel files pass `pmcc verify` (a dirty tree aside)
  - The mid-vs-print evidence for the options the wheel traded, and the friction runs at spread capture 0.25 and 0.50.
  - Done when: both are in the results and `pmcc verify` passes them.
  - Needs: W2-03
- [x] **W3-03 · Commit the results** **[PO]** — done 2026-10-28; `just wheels NVDA` on the clean tree at `8abed76` wrote `results/NVDA/wheel.json`, `wheel--sc025.json` and `wheel--sc050.json` (`git_dirty: false`, 420 KB each), the same figures as the working-tree runs; `just verify` passes all 34 files (27 runs), and a scratch export still publishes only the PMCC's 31. The PO commits them
  - Re-run from a clean tree; `pmcc verify` passes; the PO commits.
  - Needs: W3-01, W3-02

### W4 — Site

- [ ] **W4-01 · Wheel pages** **[PO]** — built 2026-10-28, waiting on the PO's read-through: `#/wheel/NVDA` and `#/wheel-review/NVDA` (WD-22, WD-32); export publishes the wheel's three results; 44 new web tests and the smoke test's wheel routes at four widths
  - Ask first: WD-22 (with a mockup; settled 2026-10-28, as recommended).
  - The wheel's pages in the existing look ([UI-SPEC](UI-SPEC.md)), including the portfolio at a chosen bar; the PMCC pages unchanged.
  - Done when: the pages render the committed results, the smoke test covers them, and the PO has read them through.
  - Needs: W3-03

### W5 — Release

- [ ] **W5-01 · Reproduce and deploy** — `just reproduce` from a clean clone matches the committed results; CI deploys. Needs: W4-01
- [ ] **W5-02 · Submit** **[PO]** — Needs: W5-01

## Risks

- **Tenor changes (WD-02).** Closed: weekly confirmed 2026-10-27.
- **Put coverage.** Weekly puts may be sparse away from the money; W1-02 reports it before the rules depend on it.
- **Call coverage.** Closed: W2-03 found every call and put the run picked covered on its decision bar, the basis-bound calls included; no call pull is needed (WD-26).
- **Engine generality.** The PMCC's book refuses puts by design, so the wheel has its own book, config and loop beside it (WD-24), and the PMCC's results must keep matching: after the review's fixes, a scratch batch of all 24 PMCC runs matched all 31 committed result files (WD-24).
