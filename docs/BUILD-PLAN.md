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
| W1 Data | Mon Oct 26 – Tue Oct 27 | NVDA weekly puts cached; S&P closes committed | In progress: W1-01 and W1-02 done 2026-10-26 (26 weeks of puts cached, 100% quoted at the −0.30-delta strike); W1-03 waits on WD-17 |
| W2 Engine and rules | Tue Oct 27 – Thu Oct 29 | The wheel runs on NVDA: blotter, ledger, NAV, gate log; invariants hold; one cycle hand-audited | In progress: W2-01 done 2026-10-26 (WD-24); W2-02 waits on WD-14 to WD-19 |
| W3 Results and analytics | Fri Oct 30 | Wheel result and friction runs committed and verified; metrics and benchmarks | Not started |
| W4 Site | Sat Oct 31 | Wheel pages live on GitHub Pages; thesis verdict shown | Not started |
| W5 Release | Sun Nov 1 | Reproduced from a clean tree; submitted by 18:00 (deadline 23:59 ET) | Not started |

**Critical path:** the put pull (W1-02) needs Workspace signed in and the PO's approval of the estimate, and everything from W2-03 on waits for it. Weekly tenor (WD-02) must be confirmed by Tue Oct 27; a switch to monthly after that puts W3 and later at risk.

**Cut order if time runs short** (the PO confirms each cut): the bootstrap CI → Sortino and time underwater → the friction runs at 0.25 (keep 0.50) → the portfolio view as a picker (fall back to a filterable ledger, which still shows the portfolio at every bar). **Never cut:** the blotter, the ledger, the portfolio at any bar, the mid-vs-print evidence, the thesis and its verdict, the benchmark table, the invariant tests.

## Questions for the PO

| When | Asks |
| --- | --- |
| W1-03 | WD-17 (S&P source) |
| W2-02 | WD-14 (entry trigger), WD-15 (expiry and early assignment), WD-16 (r), WD-18 (dividends, interest), WD-19 (fees) |
| W3-01 | WD-20 (metrics) |
| W4-01 | WD-22 (pages) |
| any time | WD-02's confirmation (weekly, expected 2026-10-27) |

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
- [x] **W1-02 · Pull NVDA's weekly puts** **[Workspace]** **[PO]** — done 2026-10-26; 26 units in 14 min, 1.3 MB in `data_cache/NVDA/wheel/` (the PO commits it); the −0.30-delta put quoted on 100% of its session bars to expiry, spreads 0.5–2.7%, never near the band's floor (WD-11)
  - Run the pull after the PO approves the estimate. Report coverage: for each week, the share of bars with a valid quote at the strikes near −0.30 delta.
  - Done when: every weekly expiry's puts are cached, coverage is reported, and the cache is committed (by the PO).
  - Needs: W1-01
- [ ] **W1-03 · S&P 500 closes** **[PO]**
  - Ask first: WD-17.
  - Done when: the two closes are committed with their citation and loaded by a tested reader.
  - Needs: W0-01

### W2 — Engine and rules

- [x] **W2-01 · Accounting for puts and shares** — done 2026-10-26; the wheel's own book and valuation, `pmcc/wheel/book.py` (WD-24), beside the PMCC's, which is untouched; `RuleId` takes `W-` IDs (WD-12); 25 unit tests (`tests/unit/wheel/test_wheel_book.py`) and a hypothesis walk (55% of runs reach expiry, 47% a put assignment, 10% a call-away). Its questions moved to W2-02, which is the first item that needs them
  - A wheel book holds one short put (cash-secured) or 100 shares with one covered call, enforcing invariants 5–7; `ASSIGN` books shares at the strike. The PMCC's book rules still apply to PMCC runs.
  - Done when: hypothesis property tests hold invariants 1, 2, 5, 6 and 7 over random event sequences; every PMCC test still passes.
  - Needs: W0-01
- [ ] **W2-02 · Wheel config and rules**
  - Ask first: WD-14, WD-15, WD-16, WD-18, WD-19.
  - `configs/wheel.yaml`: every rule (W-T1 … W-X5) with its thresholds and write-up text; the state machine; the put and call selectors; expiry settlement; the gate log.
  - Done when: each rule has tests at its boundaries, and a synthetic market drives the wheel through every state and transition.
  - Needs: W2-01
- [ ] **W2-03 · Run the wheel on NVDA** **[PO]**
  - `pmcc run --symbol NVDA --config configs/wheel.yaml`, then check the call coverage of every strike the wheel picked, and hand-audit a full cycle against the raw quotes with the PO.
  - Done when: the result passes every invariant and the audit.
  - Needs: W1-02, W2-02

### W3 — Results and analytics

- [ ] **W3-01 · Metrics and benchmarks** **[PO]**
  - Ask first: WD-20.
  - Performance, wheel-cycle statistics and the weekly-return CI; the benchmark table against the baseline PMCC and the S&P 500; each thesis claim's verdict.
  - Done when: every number the wheel pages need is in the results JSON.
  - Needs: W2-03, W1-03
- [ ] **W3-02 · Fill justification**
  - The mid-vs-print evidence for the options the wheel traded, and the friction runs at spread capture 0.25 and 0.50.
  - Done when: both are in the results and `pmcc verify` passes them.
  - Needs: W2-03
- [ ] **W3-03 · Commit the results** **[PO]**
  - Re-run from a clean tree; `pmcc verify` passes; the PO commits.
  - Needs: W3-01, W3-02

### W4 — Site

- [ ] **W4-01 · Wheel pages** **[PO]**
  - Ask first: WD-22 (with a mockup).
  - The wheel's pages in the existing look ([UI-SPEC](UI-SPEC.md)), including the portfolio at a chosen bar; the PMCC pages unchanged.
  - Done when: the pages render the committed results, the smoke test covers them, and the PO has read them through.
  - Needs: W3-03

### W5 — Release

- [ ] **W5-01 · Reproduce and deploy** — `just reproduce` from a clean clone matches the committed results; CI deploys. Needs: W4-01
- [ ] **W5-02 · Submit** **[PO]** — Needs: W5-01

## Risks

- **Tenor changes (WD-02).** If monthly is chosen, W1-01's band and dates, the call coverage, and W-P2/W-C2 change; only about 5–6 cycles fit the window.
- **Put coverage.** Weekly puts may be sparse away from the money; W1-02 reports it before the rules depend on it.
- **Call coverage.** The cached calls were fetched for the PMCC's 0.30-delta shorts; a call at or above a cost basis well above spot may fall outside them. W2-03 checks every pick; a gap means a call pull.
- **Engine generality.** The PMCC's book refuses puts by design; W2-01 must widen it without changing any PMCC result.
