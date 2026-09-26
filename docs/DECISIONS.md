# Decisions and Spec Clarifications

Sep 25, 2026 · companion to the [System Spec](PMCC-Backtest-System-Spec.md), the source of truth for this build

The user is the product owner (PO). This log tracks what the spec leaves open or what conflicts with it.

Open questions are asked **just in time**, when the backlog item that needs the answer is picked up, so nothing here needs answering up front. [BUILD-PLAN §2](BUILD-PLAN.md#2-questions-for-the-po) lists when each question comes up.

| Status | Meaning |
| --- | --- |
| `ASK` | Open question, with a recommendation. Asked when the item under **Ask at** starts. Nothing that depends on it is built before the answer. |
| `VERIFY` | A fact to measure in P1. The result is reported to the PO; if it contradicts the spec, the entry becomes `ASK`. |
| `SETTLED` | Decided. **Basis** is the spec or a dated PO answer. |
| `ENG` | An engineering choice within the spec and the engineering principles: how, not what. Recorded so the PO can see it and overrule it. It becomes `ASK` if it turns out to change behaviour, results, scope or the UI. |

**Maintenance:**
- Record each PO answer or probe result under **Outcome**, with the date and evidence, and update the status.
- If an answer changes what the spec says, update the spec in the same commit, citing the entry.
- Never delete an entry. A new entry takes the next free number in its section.

Short names: **Spec** = the System Spec; **LDG** = `LSEG-DATA-GUIDE.md`; **DG** = `DESIGN-GUIDE.md`; **EP** = `docs/ENGINEERING-PRINCIPLES.md`.

## Index

| ID | Decision | Status | When |
| --- | --- | --- | --- |
| DEC-01 | RIC day field: padded or not | VERIFY → ASK | P1-04 |
| DEC-02 | Fetch environment | SETTLED (PO) | — |
| DEC-03 | Light theme | ASK | P4-06 |
| DEC-04 | Chart colour roles | ASK | P7-01 |
| DEC-05 | LSEG terms: raw cache and derived series | ASK | P3-10 |
| DEC-06 | Bar timestamps, decision time, session bars | VERIFY | P1-04 |
| DEC-07 | Backtest window | VERIFY → PO confirms | P1-04, P1-05 |
| DEC-08 | Long-dated coverage | VERIFY | P1-04, P1-09 |
| DEC-09 | Live-contract RIC form | VERIFY | P1-04 |
| DEC-10 | Reg T and FINRA 4210 citations | VERIFY | by P7-04 |
| DEC-11 | Risk-free rate | VERIFY → PO picks | P1-05 |
| DEC-12 | Per-symbol identifiers, splits, max strike | VERIFY | P1-04 |
| DEC-13 | Hourly field availability | VERIFY | P1-04 |
| DEC-14 | Strike increments | ENG method · VERIFY values | P1-04 |
| DEC-20 | Week-open session and order of operations | ASK | P3-07 |
| DEC-21 | Selection freeze and E-T1 | ASK | P3-07 |
| DEC-22 | Gates and the gate log | ASK | P3-07 |
| DEC-23 | Spot, close, ITM at expiry | ASK | P2-03 |
| DEC-24 | Time to expiry and Greek units | ASK | P2-01 |
| DEC-25 | ATM strike, ATM IV, expected move | ASK | P2-03 |
| DEC-26 | RV20 | ASK | P2-03 |
| DEC-27 | Greeks for held contracts; fresh quotes only | ASK | P2-04 |
| DEC-28 | Exits without a valid quote | ASK | P3-07 |
| DEC-29 | Tie-breaks | ASK | P3-06 |
| DEC-30 | Starting capital (E-L4) | ASK | P3-09 |
| DEC-31 | Entry-timing sensitivity | ASK | P5-02 |
| DEC-32 | Point-in-time listing | ASK | P3-02 |
| DEC-33 | Expiry calendar | ASK | P1-06 |
| DEC-34 | Rule stamping for multi-rule events | ASK | P3-07 |
| DEC-40 | Source of truth | SETTLED (PO) | — |
| DEC-41 | Frontend stack follows the spec | SETTLED (spec) | — |
| DEC-42 | Python environment | ENG | — |
| DEC-43 | Packages added to the spec layout | ENG | — |
| DEC-44 | Money as integer units | ENG | — |
| DEC-45 | RIC form policy | ENG | — |
| DEC-46 | Cache layout | ASK | P1-07 |
| DEC-47 | Fetch dates are inclusive | ENG | — |
| DEC-48 | Fetch plan and band-edge guard | ENG | — |
| DEC-49 | Failure taxonomy | ENG | — |
| DEC-50 | Canonical results and INV-13 | ASK | P3-08 |
| DEC-51 | Invariants in CI without data | ENG | — |
| DEC-52 | Rule text rendered from parameters | ENG | — |
| DEC-53 | Composition over flags | ENG | — |
| DEC-54 | Result detail levels and report sections | ASK | P4-05 |
| DEC-55 | Dividends | SETTLED (spec) | — |
| DEC-56 | Raw cache not committed | SETTLED (spec) | revisit with DEC-05 |
| DEC-57 | Reference files stay in place | ENG | — |
| DEC-58 | Windows and Ubuntu parity | ENG | — |
| DEC-59 | Git and GitHub belong to the PO | SETTLED (PO) | — |
| DEC-60 | Returns and performance definitions | ASK | P6-01 |
| DEC-61 | Bootstrap | ASK | P6-01 |
| DEC-62 | Cycle definitions | ASK | P6-01 |
| DEC-63 | Attribution conventions | ASK | P6-01 |
| DEC-64 | Fill-assumption check | ASK | P6-01 |
| DEC-70 | Design tokens | ENG | — |
| DEC-71 | shadcn/ui restyled | ENG | — |
| DEC-72 | Fonts self-hosted | ENG | — |
| DEC-73 | Routing and base path | ENG | — |
| DEC-74 | Synthetic-data banner | ENG | — |
| DEC-75 | Data page | ASK | P7-06 |
| DEC-76 | Greek attribution display | ASK | P6-01 |
| DEC-77 | Quality-gate configuration | ENG | — |
| DEC-78 | justfile conventions | ENG | — |
| DEC-79 | CI workflow conventions | ENG | — |

---

## A. Raised during planning

### DEC-01 — RIC day field: zero-padded or not
**Status:** VERIFY → ASK · **Verify and ask at:** P1-04 · **Affects:** P1-02, INV-11, Spec › RIC builder

- **Conflict:** Spec › RIC builder says "Day not zero-padded", and INV-11 cites `AAPLF52619000.U^F26`. LDG §3, measured in Aug–Sep 2026, says the opposite: the day is always two digits (`05`), and unpadded RICs didn't resolve. `lseg_client.build_option_ric` pads the day, and its parser rejects `AAPLF52619000.U^F26` (checked Sep 25).
- **Recommendation:** P1-04 probes both spellings of the same expired contract (`AAPLF52619000.U^F26` vs `AAPLF052619000.U^F26`), and the result goes to the PO.
  - The builder emits whichever spelling resolves (padded, if the guide is right). The parser accepts both.
  - If the padded form wins, amend the spec's RIC line and INV-11 to four checks:
    1. The spec's examples parse to the correct contract.
    2. The builder emits the verified spelling.
    3. Building then parsing round-trips the canonical form.
    4. Live contracts get no caret.
- **Outcome:** —

### DEC-02 — Fetch environment
**Status:** SETTLED · **Basis:** PO, 2026-09-25 · **Affects:** P0-01, DEC-58

- **Finding (Sep 25):** WSL2 was in `nat` networking mode, and `curl http://localhost:9000/api/status` from WSL got no answer. NAT-mode WSL can't reach the Workspace proxy on Windows `localhost:9000`.
- **Decision:** the project runs from **Git Bash on Windows**, on the same machine as Workspace, so the proxy is reachable directly. P0-01 confirms it:
  - `curl -s http://localhost:9000/api/status` returns `ST_PROXY_READY`
  - the one-liner in LDG §4.2 prints `Opened`
- **Consequence:** development is on Windows and CI is on Ubuntu (DEC-58).
- **Outcome:** 2026-09-25 — PO: "I'll reopen this project from git bash so we have proper access to LSEG."

### DEC-03 — Light theme
**Status:** ASK · **Ask at:** P4-06 · **Affects:** P4-06, P7-07, UI-SPEC §3

- **Conflict:** Spec › Frontend constraints requires light and dark themes, but the baseline look (DG §1, `theme.py`) is dark only. On a light ground, amber type (`#FFB000`) is about 1.9:1, and the cyan and magenta data hues fall below 3:1.
- **Recommendation:**
  - Dark stays the default, since it is the terminal identity.
  - The light theme keeps every token name and hue family and only adjusts lightness, e.g. amber type darkened to about `#8A5A00` (≈5.9:1 on white).
  - Every text pairing must reach ≥ 4.5:1 and every data mark ≥ 3:1, both in the contrast test.
  - A toggle in the command bar switches themes and is remembered per browser.
- **Note:** the palette is a baseline the PO may change.
- **Outcome:** —

### DEC-04 — Chart colour roles
**Status:** ASK · **Ask at:** P7-01 · **Affects:** P7-01, P7-02, UI-SPEC §4

The baseline palette never had two option legs in one chart or two NAV series on one page (DG §7 leaves the leg colours to the PO).

| Role | Recommendation (reuses the baseline palette) | Alternative |
| --- | --- | --- |
| Long call value | `NAV_LINE` violet (it's the asset) | `POSITIVE` |
| Short call value | `MARK` cyan (a quoted mark) | `NEGATIVE` (reuses up/down, which tables already give to BUY/SELL) |
| Quant NAV (comparison) | `NAV_LINE` violet, solid | — |
| Baseline NAV (comparison) | `MARK` cyan, solid (no mid or print series on that page) | `TEXT_MUTED` dashed (reads as a reference) |
| Available funds (NAV chart, lower pane) | `TEXT` line; the region below zero shaded `NEGATIVE` | — |

Whichever is chosen becomes named tokens (`--long-leg`, `--short-leg`, `--strategy-quant`, `--strategy-baseline`, `--available-funds`), never hex values in chart code.

**Outcome:** —

### DEC-05 — LSEG terms and what gets published
**Status:** ASK · **Ask at:** P3-10, before real results are pushed to the public repo · **Affects:** P3-10, P5-04, P6-07, `.gitignore`

- **Spec open item:** may the raw cache be committed to a public repo? The default is no: commit derived results only (DEC-56).
- **Extension:** some derived outputs embed raw values. Ledger marks and blotter limits are mids of held contracts, and the fill-assumption scatter publishes every TRDPRC_1/mid pair. Confirm these may be public.
- **Recommendation if they may not:** the scatter publishes binned points plus the fit statistics, while marks and limits stay, because they are the backtest's own valuation.
- **Outcome:** —

## B. Facts to verify in P1

The results are reported to the PO at P1-05. A result that contradicts the spec becomes an `ASK`.

### DEC-06 — Bar timestamps, decision time, session bars
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** loader, MarketView, every rule

- **Known (LDG §4.8–4.9, measured):**
  - Intraday bars arrive tz-naive UTC, stamped at the bar's start. BID/ASK are the bar's final values.
  - Tapes run past 16:00 ET, and the latest bar of a session is a post-close stub, not the close.
- **Recommendation, presented with the probe result:**
  - `bar_end = bar_start + 1h` is the only timestamp used after load, and decision time = `bar_end`.
  - Session bars are the bars whose ET start is 09:00–15:00 (ends 10:00–16:00). On a half-day they end at 13:00.
  - Extended-hours bars and the options' 16:00 stub are kept for provenance only. They never drive decisions, marks, or ledger rows.
- **Verify, on QQQ and NVDA over at least 3 sessions:**
  1. The hourly bar whose TRDPRC_1 equals that session's daily close starts at 15:00 ET, which proves start stamping.
  2. An option's BID/ASK in that 15:00 bar equals its daily closing BID/ASK, which proves end-of-bar quotes.
- **Outcome:** —

### DEC-07 — Backtest window
**Status:** VERIFY → PO confirms · **Verify at:** P1-04 · **Confirm at:** P1-05 · **Affects:** `configs/universe.yaml`, fetch plan

- **Spec:** one window for all symbols, as long as hourly option history allows and at least 10 weeks.
- **Recommendation:**
  - Probe how far back hourly BID/ASK goes, per symbol, for expired near-the-money weeklies and for live long-dated calls.
  - **Start:** the first week-open session by which all 12 symbols have data.
  - **End:** the final session of the last complete week before the universe fetch begins.
  - Fix both in `universe.yaml` before the first published run.
- **Outcome:** start —, end —, weeks —.

### DEC-08 — Long-dated coverage
**Status:** VERIFY · **Verify at:** P1-04, P1-09 · **Affects:** E-L3 candidate sets, Methodology

- **Measure per symbol:**
  - Share of session bars with a valid mid for 0.70–0.90 delta monthly calls at 120–270 DTE.
  - Median spread %.
  - Count of IV failures. A deep ITM mid below `S − K·e^(−rT)` has no IV (see DEC-27).
- Sparse data means fewer candidates and more E-T1 retries. That is reported on the Methodology page. The rules stay unchanged.
- **Outcome:** —

### DEC-09 — Live-contract RICs
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** P1-02, P1-03

- Long legs still listed at fetch time must resolve in the live form (no caret). LDG §4.13 and §6.3 say they do. Confirm on 3 symbols.
- **Outcome:** —

### DEC-10 — Reg T and FINRA 4210 citations
**Status:** VERIFY · **Verify by:** P7-04 · **Affects:** Methodology page

- **Confirm and cite:**
  - A long listed option with 9 months or less to expiry has no loan value (paid in full).
  - A short call is covered at $0 by a long call with a lower or equal strike and a later or equal expiry.
  - Short stock needs 150% initial (proceeds plus 50%) and 30% maintenance.
- **Candidate sources:** Reg T (12 CFR §220.12), FINRA Rule 4210(c) and (f)(2), and Cboe margin rules. Quote the exact paragraphs on the Methodology page.
- **Outcome:** —

### DEC-11 — Risk-free rate
**Status:** VERIFY → PO picks · **At:** P1-05 · **Affects:** pricing, eligibility, Methodology

- The spec asks for the source and value of r to be chosen.
- **Recommendation:** use the 3-month US T-bill yield on the window's start date, as one continuously compounded constant.
  - **Source:** LSEG (`US3MT=RR`, RIC to be confirmed), cross-checked against FRED DTB3.
  - **Storage:** `configs/universe.yaml` with its source and date, and shown on the site.
- r changes eligibility: a deep ITM mid below `S − K·e^(−rT)` has no IV. Fix r before any run.
- **Outcome:** —

### DEC-12 — Per-symbol identifiers, splits, max strike
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** `configs/universe.yaml`, P1-02

- **Confirm for each universe symbol:**
  - **Stock RIC with its exchange suffix.** LDG verified only `QQQ.O` and `UUUU.K`.
  - **Option root.**
  - **No split in the window,** since a split changes the root (LDG §3).
  - **Max strike needed ≤ $999.99,** the 5-digit strike field. If any symbol needs more, that's an `ASK`.
- **Outcome:** —

### DEC-13 — Hourly field availability
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** fetch field lists

- A field the RIC doesn't carry raises `LDError` for the whole request (LDG §4.6).
- **Probe:** each field from Spec › Fields and bars, paired with TRDPRC_1, on hourly option and stock RICs.
- **Fetch and records:**
  - The fetch requests only the fields that exist.
  - Dropped fields are recorded in each unit's sidecar and on the Methodology page.
  - The stock also needs BID/ASK, for the stock fills after X-S5.
- **Outcome:** —

### DEC-14 — Strike increments
**Status:** ENG (method) · VERIFY (values) · **Verify at:** P1-04 · **Affects:** P1-06

- **Method:** per expiry and per region (near the money for weeklies, deep ITM for monthlies), probe one session with 5 strikes in a single batch.
  - The strikes are an anchor `A` (a multiple of $10 near the region's centre) plus `A+0.50`, `A+1`, `A+2.50` and `A+5`.
  - The smallest offset that answers is the increment. If none answers, the increment is $10.
- **Recording:** increments are recorded per expiry in the sidecar. They can differ by region, e.g. $1 near spot and $5 deep ITM on the same monthly (LDG §6.2).
- **Outcome:** —

## C. Rule interpretations

Each of these decides trading behaviour the spec leaves open, so each goes to the PO.

### DEC-20 — Week-open session and order of operations
**Status:** ASK · **Ask at:** P3-07

- **Recommendation:** "Monday" in E-S1, X-L1, X-L2, the gates and the gate log means the **week-open session**: the first trading session of the calendar week (Tuesday after a Monday holiday).
- **Recommendation:** within each decision bar, in this order:
  0. Cover short stock left by X-S5 (at the first valid bar of the next session).
  1. Long exits X-L1/X-L2, on the week-open session only, then re-entry.
  2. Long entry if flat (E-L1–E-L4).
  3. Short exits X-S1, X-S2, X-S3.
  4. Short entry, on the week-open session only.
  5. Expiry resolution X-S4/X-S5 on the close bar of the short's expiry session.
  6. Marks, the ledger row, and runtime invariants.
- This extends the spec's order (long exits → short exits → short entry) without changing it.
- **Outcome:** —

### DEC-21 — Selection freeze and E-T1
**Status:** ASK · **Ask at:** P3-07 · **Affects:** G-1

- **Recommendation (short):** on the week-open session, the first bar where the short selector returns a contract freezes that contract for the rest of the session.
  - E-T1 is checked on that bar and on each later bar; the first pass is the **decision bar**.
  - If no bar passes, G-1 fires.
  - The engine never re-selects or substitutes a strike (Spec › Trade rules: entry).
- **Recommendation (long):** the same freeze applies within a session. If E-T1 never passes, E-L1 retries the next session with a fresh selection.
- **Eligibility:** selectors consider only contracts that are eligible on that bar (valid quote and a successful IV solve).
- **Outcome:** —

### DEC-22 — Gates and the gate log
**Status:** ASK · **Ask at:** P3-07 · **Affects:** P4-02, INV-09

- **Recommendation (evaluation):**
  - G-2–G-5 are evaluated at the decision bar. Every gate the strategy has is evaluated and recorded (pass or fire, with values).
  - The outcome is the first gate, in spec order, that fired.
  - If G-1 fires, the other gates are `not_evaluated`.
- **Recommendation (missing inputs):** a gate whose inputs are unavailable (e.g. the next-week ATM call has no quote) records `n/a`. It does not fire, and its reason is logged.
- **Recommendation (rows):** one gate-log row per strategy per week-open session.
  - A week with no long held logs outcome `E-S1`.
  - A week blocked by an unfinished long reset logs `X-L1` or `X-L2`.
- **Outcome:** —

### DEC-23 — Spot, close, ITM at expiry
**Status:** ASK · **Ask at:** P2-03 · **Affects:** P3-06

- **Recommendation:**
  - **Spot** at a decision bar is the underlying's TRDPRC_1 (last trade) in that bar.
  - **Closing spot** is the spot of the session's close bar (16:00 ET, or 13:00 on a half-day).
  - **ITM at expiry (X-S4/X-S5):** the short is ITM if and only if closing spot > strike. OCC auto-exercises at $0.01 ITM, so equal counts as OTM.
- **Outcome:** —

### DEC-24 — Time to expiry and Greek units
**Status:** ASK · **Ask at:** P2-01 · **Affects:** P6-04

- **Recommendation:**
  - **T:** calendar time from the decision time to the expiry session's close (16:00 ET, or 13:00 on a half-day), in years, ACT/365 (seconds ÷ 31,536,000).
  - **Units:** δ per $1; Γ per $1²; θ per year (Δt in years); ν per 1.00 of volatility (Δσ in vol units). Attribution uses the same units.
  - **DTE (E-L2, X-L2):** calendar days from the decision date to the expiry date.
- **Outcome:** —

### DEC-25 — ATM strike, ATM IV, expected move
**Status:** ASK · **Ask at:** P2-03 · **Affects:** E-S3 (quant), G-3, G-4, X-S3

- **Recommendation:**
  - **ATM strike:** the listed strike nearest spot (tie → the lower strike).
  - **ATM IV (G-3, G-4):** the IV of the ATM **call**. Under the spec's q = 0 assumption, an American call is priced exactly by Black-Scholes, so calls avoid the early-exercise bias that puts carry.
  - **EM:** ATM call mid + ATM put mid for the front week, at the decision bar. Both quotes must be valid. Otherwise EM is unavailable, and quant E-S3 can't select on that bar.
- **Outcome:** —

### DEC-26 — RV20
**Status:** ASK · **Ask at:** P2-03 · **Affects:** G-4

- **Recommendation:** RV20 at a decision bar is the sample standard deviation of the last 20 daily log returns × √252. The returns come from the 21 most recent completed session closes before the current session. A session close is the TRDPRC_1 of the close bar.
- **Fetch:** the fetch already pulls 30 warm-up sessions (DEC-48), which covers any reasonable answer.
- **Outcome:** —

### DEC-27 — Greeks for held contracts; fresh quotes only
**Status:** ASK · **Ask at:** P2-04 · **Affects:** X-S2, X-L1

- **Selection:** an IV failure makes a contract ineligible (spec).
- **Recommendation (held contracts):** if the mid is below the no-arbitrage floor, `mid < max(0, S − K·e^(−rT))`, the contract gets δ := 1.0 (the σ → 0 limit for an ITM call), Γ = ν := 0, θ := −r·K·e^(−rT). X-S2 and X-L1 therefore still see a deep ITM leg.
- **Recommendation (fresh quotes only):** rules evaluate only on bars where the contract has a fresh valid quote. Stale carried marks value the book, but they never trigger a rule or a fill.
- **Outcome:** —

### DEC-28 — Exits without a valid quote
**Status:** ASK · **Ask at:** P3-07

- **X-S1, X-S2:** their conditions need a fresh quote, so a trigger can always fill.
- **Recommendation (X-S3):** if it triggers on the check bar with no valid quote, the close fills at the first later bar of that session that has one. The row is still ruled `X-S3`, noted "delayed fill". If there is none before the close, X-S4/X-S5 resolve the short at the close.
- **Recommendation (X-L1/X-L2):** the sale fills at the first bar of the week-open session with a valid long quote. Short entry waits for the reset and re-entry to complete.
  - If the reset doesn't complete in session, there is no short that week (gate log `X-L1`/`X-L2`).
  - The pending reset carries to the next session.
- **Recommendation (X-S5 cover):** fills at the first bar of the next session with a valid stock BID/ASK.
- **Outcome:** —

### DEC-29 — Tie-breaks
**Status:** ASK · **Ask at:** P3-06 · **Affects:** P4-01

| Rule | Recommended tie-break order |
| --- | --- |
| E-L2 baseline (nearest 180 DTE) | later expiry |
| E-L3 baseline (delta nearest 0.80) | lower spread %, then lower strike |
| E-L3 quant (lowest extrinsic ÷ delta) | lower spread % (spec), then earlier expiry, then lower strike |
| E-S3 baseline (delta nearest 0.30) | lower spread %, then higher strike |
| ATM strike | lower strike |

Distances are compared in integer price units, so float noise can't create or break a tie.

**Outcome:** —

### DEC-30 — Starting capital (E-L4)
**Status:** ASK · **Ask at:** P3-09 · **Affects:** P5-01

- **Recommendation:**
  - `pmcc calibrate` runs every universe symbol under `baseline_pmcc` and `quant_pmcc` at `spread_capture` 0, with provisional cash.
  - It records each run's first long-leg entry cost: fill × 100 × qty + fees.
  - It sets `starting_cash = ceil(2 × max ÷ 5,000) × 5,000`.
  - The value is written to `configs/universe.yaml` with its basis (symbol, strategy, cost) and committed before the first published run. Every strategy, ablation and sensitivity run uses it unchanged.
  - P3 uses a provisional value from the symbols cached so far, labelled provisional.
- **Outcome:** —

### DEC-31 — Entry-timing sensitivity
**Status:** ASK · **Ask at:** P5-02

- **Recommendation for variant `t{k}`, k = 1…7 (the session bars of the week-open session):**
  - The short's decision bar is fixed at bar k.
  - At bar k the selector runs, and the selected contract must have a valid quote and pass the E-T1 spread threshold. Otherwise G-1 fires.
  - Other bars are never scanned.
- **Everything else is unchanged,** including long entry. The fixed-bar trigger replaces E-T1 under the same rule ID.
- **Outcome:** —

### DEC-32 — Point-in-time listing
**Status:** ASK · **Ask at:** P3-02 · **Affects:** E-S3 (quant), ATM strike

- **Recommendation:**
  - A contract is "listed" at time t once it has had a valid quote at or before t.
  - Chain snapshots, "lowest listed strike" and the ATM strike use only listed contracts.
  - The fetch band can include strikes that are listed later, and MarketView hides them until their first quote.
- **Outcome:** —

### DEC-33 — Expiry calendar
**Status:** ASK · **Ask at:** P1-06

- **Weekly expiries:** the last trading session of each week, from the stock tape (spec).
- **Recommendation (monthly):** the third Friday, or the prior session if that Friday is an NYSE holiday. Holidays come from `configs/calendar.yaml` (NYSE holidays and early closes for 2026–2027, with the source cited). Holidays derived from the tape must match the table (a P1-06 check).
- **Recommendation (reference data):** the calendar is published in advance, so MarketView exposes it without the as-of restriction.
- **Known cases:**
  - Fri Jul 3 2026 is closed, so that week expires Thu Jul 2.
  - Mon Sep 7 2026 (Labor Day) moves week-open to Tue Sep 8.
  - Fri Jun 19 2026 is closed, so that week expires Thu Jun 18.
  - Juneteenth 2027 is observed Fri Jun 18, so the June 2027 monthly expires Thu Jun 17 (verify).
- **Outcome:** —

### DEC-34 — Rule stamping for multi-rule events
**Status:** ASK · **Ask at:** P3-07 · **Affects:** INV-09

| Event | Blotter rows | Recommended rule |
| --- | --- | --- |
| Long entry | `BUY` | `E-L1`; notes carry the E-L2/E-L3 selection values and the E-T1 spread |
| Short entry | `SELL` | `E-S1`; notes carry the E-S3 strike logic, the E-T1 spread and the E-S5 terms |
| Short exit | `BUY` | the exit rule (`X-S1`, `X-S2`, `X-S3`) |
| Long reset / roll | `SELL`, then re-entry `BUY` | `X-L1`/`X-L2`; the re-entry is `E-L1`, noted "re-entry after X-L1" |
| OTM expiry | `EXPIRE` at $0 | `X-S4` |
| Missed assignment | `ASSIGN` + stock `SELL` at the strike, then the next session's stock `BUY` | `X-S5` on all three |
| End of backtest | no rows; final ledger marks | `X-E1` |

**Outcome:** —

## D. Architecture and environment

### DEC-40 — Source of truth
**Status:** SETTLED · **Basis:** PO, 2026-09-25

1. **The spec is the source of truth for this build**, as amended by the PO answers recorded here.
2. The derived docs (PRD, ARCHITECTURE, TEST-STRATEGY, UI-SPEC, BUILD-PLAN) elaborate the spec. A derived doc that disagrees with it gets fixed.
3. EP says how code is written.
4. Reference material, not authority:
   - **LDG and `lseg_client.py`:** practical know-how for getting data out of LSEG, so it isn't relearned. LSEG behaviour that contradicts the spec goes to the PO.
   - **DG and `theme.py`:** the baseline look (palette, type, terminal layout). The PO may change it.

**Outcome:** 2026-09-25 — PO: "the spec should be the source of truth for this build … the other docs … gave us a baseline."

### DEC-41 — Frontend stack follows the spec
**Status:** SETTLED · **Basis:** Spec › Stack

- DG §4 describes a Python/Plotly page builder (`page_shell.py`, which isn't in this repo).
- The spec's stack is used instead: Vite, React, TypeScript, Tailwind, shadcn/ui, TanStack Table, and ECharts via `echarts-for-react`.
- The baseline look is carried over through tokens, the terminal layout, and the panel, table and chart rules (UI-SPEC).
- `theme.py` is never imported.

### DEC-42 — Python environment
**Status:** ENG

- uv with a committed `uv.lock` (the spec's choice).
- Python 3.12.
- `lseg-data==2.1.1` (the version LDG used).
- **pandas:** pinned, and imported only in `pmcc/data/lseg/`, where lseg-data hands back pandas and it is converted to polars at once. LDG notes pandas 3.0 changed datetime and string dtypes.
- **tzdata:** a runtime dependency, because Windows has no system time-zone database for `zoneinfo` (DEC-58).
- **Playwright:** never install the Python `playwright` package in this env; it bumps `pyee` and breaks lseg-data. The e2e test uses Node Playwright in `web/`.
- **Typing:** a minimal local stub in `typings/lseg/` keeps pyright strict usable. It covers only what `pmcc/data/lseg/` calls (`open_session`, `close_session`, `get_history`, `session.get_default().open_state`, `OpenState`, `errors.LDError`) and grows with it.
- **pandas == 2.3.3:** the newest version lseg-data 2.1.1 allows (it caps pandas below 3.0), and the version the known-good conda `algo` env runs (P0-03).
- **Packaging:** the `uv_build` backend, with `pmcc/` at the repo root (`module-root = ""`), so `pmcc` is an installed console script. Other runtime deps take lower bounds; `uv.lock` pins them exactly.

### DEC-43 — Packages added to the spec layout
**Status:** ENG

- **`pmcc/domain/`:** value objects and the time model, at the bottom of the dependency graph.
- **`pmcc/config/`:** pydantic config models, the loader, hashing and rule text, also at the bottom.
- **`pmcc/strategy/ports.py`:** owns the `MarketView` protocol, so strategy code never imports the engine (EP › Dependency Inversion).
- **Enforcement:** import boundaries are checked by `tests/architecture/test_imports.py` (ARCHITECTURE §3.3).

### DEC-44 — Money as integer units
**Status:** ENG

- **Units:** accounting and fills hold prices and cash as integers in units of $0.0001 (`Price`, `Money`).
- **Quantizing:** quotes are quantized once, at load (round half-even), and `spread_capture` fills at the fill boundary.
- **Why:** invariants 1–2 then hold exactly, with no float tolerance, and results stay byte-stable.
- **Floats:** Greeks, IV and analytics stay float64.
- **JSON:** dollars are exported to 4 decimals.

### DEC-45 — RIC form policy
**Status:** ENG

- **Unexpired contracts:** an expiry on or after the fetch date uses the live form only (Spec › RIC builder).
- **Expired contracts:** ask the caret form first, then the live form for whatever didn't answer. The changeover takes days (LDG §3). Record `ric_form_used`.
- **Puts:** put carets use the **call** month letter (`^F26` for a June put).
- **Strike limit:** a strike above $999.99 raises.
- **OCC symbols:** follow `occ_symbol()`.

### DEC-46 — Cache layout
**Status:** ASK · **Ask at:** P1-07

- The spec says "parquet per instrument". The recommendation stores one parquet per underlying (`{SYM}/stock.parquet`) and one per option chain unit (`{SYM}/chains/{expiry}_{C|P}.parquet`). The chain unit is the fetch unit and is written atomically.
- A per-RIC manifest (`{SYM}/manifest.json`) keeps the spec's fields (RIC, fetch time, row count, hash) and adds the form, status, and first and last bar.
- Each unit has a sidecar per LDG §5.
- **Data-manifest hash:** the one in a run manifest is the sha256 of the symbol's manifest content, excluding fetch times. Re-fetching identical data doesn't change it, and fetching another symbol never does.
- **Outcome:** —

### DEC-47 — Fetch dates are inclusive
**Status:** ENG

- `pmcc fetch --start/--end` take inclusive dates, as the spec's example implies.
- The adapter passes `end + 1 day`, because LSEG's end is effectively exclusive (LDG §2).

### DEC-48 — Fetch plan and band-edge guard
**Status:** ENG · **Affects:** P1-06, P5-05

- **Plan:** units and bands follow ARCHITECTURE §6.3.
  - The stock tape gets a 30-session warm-up.
  - Each weekly call band starts at the **prior** week-open session, so G-3 has next-week IV.
  - Each week gets an ATM put band on its week-open session, for EM.
  - Monthly long-candidate bands cover the whole window.
- **Bands:** built from regular-session highs and lows, padded; they err wide (LDG §4.10).
- **Band-edge guard:** if a selection lands on the top or bottom strike fetched, the run flags it and the unit is re-fetched wider.

### DEC-49 — Failure taxonomy
**Status:** ENG

| Class | Example | Handling |
| --- | --- | --- |
| Unanswered contract | RIC never listed; `LDError … No data` | Soft: empty series, manifest `unanswered`, log event `fetch.ric.unanswered` |
| Transient provider error | timeout; batch rejected whole | Retry the whole batch, then each RIC alone (LDG §4.4); 3 attempts with backoff |
| Outage | session not `Opened`; repeated transport errors | Fail loud: abort the unit, write nothing, exit non-zero (LDG §4.3) |
| Engine error | look-ahead request; uncovered short; quantity mismatch | Crash the run; nothing written |
| Invariant violation | NAV doesn't reconcile | Run exits non-zero; no result file |

### DEC-50 — Canonical results and INV-13
**Status:** ASK · **Ask at:** P3-08

- **Conflict inside the spec:** INV-13 demands byte-identical results on re-run, but the run manifest also carries a run timestamp.
- **Recommendation:**
  - Results are written as canonical JSON: sorted keys, fixed rounding per value type, UTF-8, `\n` line endings.
  - INV-13 compares whole files after removing `manifest.run_timestamp`, the only volatile field.
  - Each run records `git_sha` and `git_dirty` (the dirty check ignores `results/`). `pmcc verify` rejects committed results with `git_dirty: true`, so every published number traces to a commit. Consequence: commit the code before a publishable run.
- **Outcome:** —

### DEC-51 — Invariants in CI without data
**Status:** ENG

CI has neither the cache nor credentials, so "the CI build fails if any invariant fails" (Spec › Invariant tests) is met three ways:

1. **Runtime:** checks run in every backtest, and a failure writes nothing.
2. **`pmcc verify` in CI:** re-derives INV-01, 02, 03, 05, 06, 07, 08, 09 and 10 from committed results. Blotter and gate-log rows carry the audit fields this needs.
3. **Tests:** unit, property and scenario tests on a synthetic market cover INV-04, 11, 12 and 13.

INV-14 and INV-15 run in the web job.

### DEC-52 — Rule text rendered from parameters
**Status:** ENG

- Each YAML rule carries `id, name, kind, params, condition, action, rationale`.
- `condition` and `action` are templates (`"short delta > {max_delta}"`) rendered from `params` at load.
- A config test fails if a placeholder is unresolved or a param is never referenced, so the published text can't drift from the thresholds the engine uses.

### DEC-53 — Composition over flags
**Status:** ENG

- A strategy is a set of ordered rule lists, built from YAML by `kind` through a registry.
- "Off" means absent from the list, never a boolean passed into rule logic (EP › Low coupling).
- Variants use `extends` plus `overrides` keyed by rule ID (`params` patch, `replace`, or `remove`).
- Rules shared by both strategies live once, in `configs/_shared.yaml`.

### DEC-54 — Result detail levels and report sections
**Status:** ASK · **Ask at:** P4-05 · **Affects:** P7-01

- **Recommendation (detail levels):**
  - **Full detail** (`baseline_pmcc`, `quant_pmcc`): blotter, ledger, gate log, cycles, attribution.
  - **Summary** (ablation and sensitivity runs): metrics, cycle stats, exit mix, skips by rule, session-close NAV, weekly returns, invariant results.
- **Recommendation (report sections):** each strategy YAML declares which sections its page shows (`report.sections`). Quant declares `gate_log` and `greek_attribution`; baseline doesn't. One component tree then renders both pages (Spec › Site and UI), and the difference lives in config.
- **Outcome:** —

### DEC-55 — Dividends
**Status:** SETTLED · **Basis:** Spec › Overview and scope

- Out of scope. This supersedes LDG §6's advice to pull dividend data.
- The Methodology page states q = 0, notes that early exercise ahead of ex-dividend dates isn't modelled, and names which universe symbols pay dividends (public information, no data pull).

### DEC-56 — Raw cache not committed
**Status:** SETTLED · **Basis:** Spec › Cache (the default), until DEC-05 is answered

- This is the spec's default, and it supersedes LDG §5 ("commit the data").
- LDG's other cache rules still apply unchanged: never overwrite, keep a sidecar, write only after success, and check the counts.

### DEC-57 — Reference files stay in place
**Status:** ENG

- `LSEG-DATA-GUIDE.md`, `DESIGN-GUIDE.md`, `theme.py` and `lseg_client.py` stay at the repo root as read-only references, excluded from ruff, pyright and pytest.
- `lseg_client.py` is ported into `pmcc/data/` (typed, polars-based), never imported.
- Changes to the look go into `web/src/theme/`, not `theme.py`.

### DEC-58 — Windows and Ubuntu parity
**Status:** ENG · **Affects:** P0-02, P0-03, P0-05, P3-08

Development runs in Git Bash on Windows (DEC-02) and CI runs on Ubuntu. Both must produce the same bytes and the same behaviour.

- **Line endings:** `.gitattributes` sets `* text=auto eol=lf` and `*.parquet binary`.
  - Git for Windows would otherwise check files out with CRLF.
  - Committed results must compare byte for byte (INV-13, P8-01), so LF is required on Windows too.
- **Python writers** pass `newline="\n"`. Paths go through `pathlib`, and no Python code depends on the shell.
- **Time zones:** `tzdata` is a runtime dependency, because Windows has no system time-zone database for `zoneinfo`.
- **just:** recipes run under bash (`set shell := ["bash", "-cu"]`), which is Git Bash locally and bash on the runners.
- **Node:** 22 LTS on both machines, pinned by `.nvmrc` and `engines`.
- **Location:** the project lives on a Windows path, not `\\wsl.localhost\…`, because uv, node and file watching are slow or broken over that share.

### DEC-59 — Git and GitHub belong to the PO
**Status:** SETTLED · **Basis:** PO, 2026-09-25 · **Affects:** every item that commits or pushes (P0-02 onward), CLAUDE.md, BUILD-PLAN

- **Decision:** the PO does every git and GitHub action for the whole project: creating the repo, `git init`, staging, committing, pushing, branches, tags, and GitHub settings (Pages, secret scanning, Actions).
- **The agent may** run read-only git commands (`status`, `diff`, `log`, `show`, `ls-files`, `check-ignore`) to check done-when lines and draft commit messages.
- **The agent never** runs a git or gh command that changes the repo or GitHub (`init`, `add`, `commit`, `push`, `branch`, `tag`, `stash`, `reset`, `checkout`, `gh repo`, `gh api` writes, and so on).
- **Workflow:** the agent finishes an item's work, docs and tick in the working tree, then hands the PO the list of files and a proposed commit message (`P0-03: python project`). "Commit" and "push" anywhere in the docs mean the PO's action.

### DEC-77 — Quality-gate configuration
**Status:** ENG · **Affects:** P0-04, P0-05, P0-06

- **Hook versions:** ruff and pyright run in pre-commit as local hooks through `uv run --frozen`, so the hooks, `just check` and CI all use the versions pinned in `uv.lock`. There are no separately pinned mirror repos to drift. Only `pre-commit-hooks` (check-yaml, end-of-file-fixer, check-added-large-files, detect-private-key) comes from a pinned remote repo.
- **Reference files (DEC-57):** excluded twice, by ruff's `extend-exclude` with `force-exclude = true` (pre-commit passes file names explicitly, which otherwise bypasses the exclude) and by a global `exclude` in `.pre-commit-config.yaml`, so no hook ever checks or rewrites them. pyright checks only `pmcc` and `tests`.
- **ruff rules:** `E W F I B UP SIM N PT RUF C90`, mccabe max complexity 10, line length 100. `›` is an allowed confusable, because the docs cite with it (Spec › CLI).
- **pyright:** strict, over `pmcc` and `tests`, with stubs from `typings/`.
- **pytest:** `--strict-markers --strict-config`, `xfail_strict`. The hypothesis profile comes from `HYPOTHESIS_PROFILE` (`dev` by default, `ci` in CI).
- **No network:** an autouse fixture in `tests/conftest.py` makes socket connect, `create_connection` and `getaddrinfo` raise, localhost included, since LSEG's proxy listens on `localhost:9000`.
- **Credentials hook:** a `language: fail` hook rejects any file named `lseg-data.config.json`, at any path.
- **Outcome:** 2026-09-25 — `pre-commit run --all-files` passes. A planted complexity-11 function (C901) and a fake `lseg-data.config.json` were both rejected, then removed.
- **Outcome:** 2026-09-25 — PO: "I'll handle everything with github - setting up the repo, initializing, and committing and pushing - and that will remain true for the remainder of the project." Read-only git allowed (PO, same day).

### DEC-78 — justfile conventions
**Status:** ENG · **Affects:** P0-05, P0-06, P4-06

- **Tools:** every Python tool and `pmcc` command runs through `uv run --frozen`, and `setup` uses `uv sync --frozen`, so recipes never rewrite `uv.lock` (DEC-77).
- **Stubs:** recipes call the real `pmcc` commands, whose stubs already exit 1 naming their backlog item, so no recipe needs its own stub.
- **Web before P4-06:** until `web/package.json` exists, `setup` and `check` skip their npm steps with a printed note, and `web-dev`, `web-build`, `e2e` (and so `reproduce`) fail naming P4-06. The web steps switch on by themselves when the scaffold lands.
- **Extra recipes:** `test *ARGS` (TEST-STRATEGY §7 uses it) and `fetch … *ARGS`, so `--plan-only` can be passed; `default` lists the recipes.
- **Test:** `tests/unit/test_justfile.py` checks the bash shell setting and the §14 recipe names by reading the file, so it runs in CI without `just` installed.
- **Outcome:** 2026-09-25 — `just --list` shows every recipe; `just check` green in Git Bash (pre-commit, 15 tests, web steps skipped).

### DEC-79 — CI workflow conventions
**Status:** ENG · **Affects:** P0-06, P4-05, P4-07

- **Trigger:** every push and pull request. Read-only token (`contents: read`), and a newer push to the same ref cancels the older run.
- **Steps call tools directly, not `just`:** the `python` job runs the same commands as `just check` (`uv sync --frozen`, `pre-commit run --all-files`, `pytest`) through `uv run --frozen`, so the runner needs no `just` install and uses the `uv.lock` versions (DEC-77).
- **Credentials guard:** the first step fails if `git ls-files` lists `lseg-data.config.json` at any path (ARCHITECTURE §15), before anything is installed.
- **Caches:** setup-uv's uv cache, and `~/.cache/pre-commit` keyed on `.pre-commit-config.yaml`. Python comes from `.python-version`.
- **Actions:** pinned to major tags (`actions/checkout@v5`, `astral-sh/setup-uv@v6`, `actions/cache@v4`).
- **Staging:** `pmcc verify results/` joins the `python` job with P4-05, once the command and committed results exist. The `web` and `deploy` jobs arrive with P4-07.
- **Test:** `tests/unit/test_ci_workflow.py` reads `ci.yml` and checks the triggers, the Ubuntu runner, the frozen install, pre-commit on all files, pytest under the `ci` profile, the credentials guard, and that CI never runs `pmcc fetch` or `pmcc probe`.

## E. Analytics definitions

These define the reported numbers, so each goes to the PO. They're asked as one batch when P6 starts.

### DEC-60 — Returns and performance
**Status:** ASK · **Ask at:** P6-01

- **Recommendation:**
  - **Session-close NAV:** the NAV at the session's close bar.
  - **Daily return:** close NAV ÷ previous close NAV − 1.
  - **Weekly return:** NAV at the week-final session close ÷ the previous week-final close − 1. The first week compares against starting cash.
  - **Sharpe:** mean ÷ sample standard deviation of daily returns.
  - **Sortino:** mean ÷ √mean(min(r, 0)²).
  - Both use a target of 0 and are not annualized. Any annualized figure is × √252 and labelled "annualized from N sessions".
  - **Max drawdown:** measured on per-bar NAV.
  - **Longest time underwater:** the most sessions from a peak to full recovery, or to the end.
  - **Return on starting NAV:** P&L ÷ starting cash.
  - **Return on capital deployed:** P&L ÷ the peak long-leg entry cost.
- **Outcome:** —

### DEC-61 — Bootstrap
**Status:** ASK · **Ask at:** P6-01 · **Affects:** P6-05

- **Recommendation (per symbol and strategy):** a percentile 95% CI of the mean weekly return, from 10,000 resamples.
- **Randomness:** numpy PCG64, seeded from `configs/universe.yaml` (`bootstrap.seed`); the seed is recorded in results.
- **Recommendation (pooled):**
  - Build a week × symbol matrix of weekly returns.
  - Resample whole weeks (rows) with replacement, so all symbols move together.
  - Take the mean of each resample.
- **Outcome:** —

### DEC-62 — Cycles
**Status:** ASK · **Ask at:** P6-01 · **Affects:** P6-02

- **Recommendation:**
  - **Cycle:** one calendar week of the window.
  - **Cycle P&L:** the NAV change from the previous week-final close to this one, both legs included.
  - **Win / loss statistics:** a win is P&L > 0. Win rate, average win, average loss and payoff (average win ÷ |average loss|) cover weeks with a long held.
  - **Traded vs skipped:** counted separately, with skips counted by rule ID.
  - **Premium captured:** (credit − buyback) ÷ credit, on traded weeks.
  - **Weekly credit as % of long-leg cost:** credit ÷ the current long's entry cost.
  - **Exit mix:** counts of X-S1–X-S5, X-L1 and X-L2.
- **Alternative:** base the win statistics on short-leg P&L instead of NAV.
- **Outcome:** —

### DEC-63 — Attribution
**Status:** ASK · **Ask at:** P6-01 · **Affects:** P6-03, P6-04

- **Recommendation (by leg):**
  - The short leg is credits − buybacks (the spec's net short premium). X-S5 stock losses are shown separately.
  - The long leg is realized + unrealized P&L, split into the intrinsic change (Δ of max(0, S − K) × 100 × qty) and the extrinsic change (the rest).
- **Recommendation (by Greek):**
  - Per bar and per leg, predicted = δΔS + ½Γ(ΔS)² + θΔt + νΔσ, using the previous bar's Greeks and DEC-24 units.
  - Residual = actual − predicted.
  - A bar with a stale endpoint or a failed IV counts entirely as residual, and the number of such bars is reported.
- **Outcome:** —

### DEC-64 — Fill-assumption check
**Status:** ASK · **Ask at:** P6-01 · **Affects:** P6-07

- **Recommendation:**
  - **Sample:** session bars with a TRDPRC_1 print and a valid end-of-bar BID/ASK. Weekly call bands are the "shorts" group and monthly long candidates the "longs" group. Computed per symbol and pooled.
  - **Fit:** OLS of TRDPRC_1 on mid, reporting slope, intercept, R² and N. Also report the median |print − mid| as a % of the spread.
  - **Caveat stated on the page:** a print can be up to an hour older than the end-of-bar quote.
- **Outcome:** —

## F. Frontend

### DEC-70 — Design tokens
**Status:** ENG

- **`web/src/theme/tokens.css`:** the only place colours and font stacks exist, as CSS custom properties for both themes.
  - Values start from `theme.py` (the baseline), with names that mirror it (`--nav-line`, `--margin-im`, …).
  - A palette change the PO asks for is one edit in this file.
- **`web/src/theme/tokens.ts`:** typed accessors plus the numeric layout constants.
- **ECharts:** reads colours from the CSS variables at render time, so a theme switch re-renders charts in the new colours.
- **Ported tests:**
  - Token-lint: no hex, `rgb()`, font name or `[Npx]` arbitrary value outside `web/src/theme/`.
  - AA contrast for every text pairing, in both themes.

### DEC-71 — shadcn/ui restyled
**Status:** ENG

- Radius 0, no shadows, token colours only, matching the baseline's square terminal panels.
- The components are used for behaviour and accessibility (Select, Tooltip, Toggle), not for their default look.

### DEC-72 — Fonts self-hosted
**Status:** ENG

- Space Grotesk, Inter and JetBrains Mono come from `@fontsource/*` and are bundled into `web/dist`. The site then makes no Google Fonts request.
- This follows Spec › Frontend constraints: static output, loading from its own origin only.

### DEC-73 — Routing and base path
**Status:** ENG

- HashRouter, as the spec requires, with Vite `base: './'` so the build works under any Pages repository path.
- Data is fetched relative to the document (`data/index.json`).
- Rule links are routes (`#/rules/E-S3`), because an in-page `#anchor` can't work inside a hash route.
- The route table is in UI-SPEC §7.

### DEC-74 — Synthetic-data banner
**Status:** ENG

- Every result carries `manifest.data_source` (`lseg` | `synthetic`).
- Any page showing a synthetic result shows a warning banner, so generated data can never pass for real (DG §4).
- The P4 sample deploy relies on this.

### DEC-75 — Data page
**Status:** ASK · **Ask at:** P7-06

- The spec says the Data page "only works via the local server" but doesn't say what it shows.
- **Recommendation:**
  - **On github.io:** a single panel reading "Data connection required".
  - **Locally:** `pmcc serve` serves `web/dist` plus read-only JSON endpoints over the cache (coverage per expiry, quotes per RIC) on 127.0.0.1.
  - The local mode is cuttable; the github.io behaviour is not.
- **Outcome:** —

### DEC-76 — Greek attribution display
**Status:** ASK · **Ask at:** P6-01

- **Recommendation:** a table per leg × component (δ, Γ, θ, ν, residual) shows cumulative $ and % of ΔV, plus one cumulative-residual line.
- A five-series stacked chart would need five hues the baseline palette doesn't have.
- **Outcome:** —

---

## Template

```markdown
### DEC-NN — Title
**Status:** ASK | VERIFY | SETTLED | ENG · **Ask at / Verify at / Basis:** … · **Affects:** backlog IDs, tests
- **Context:** what the spec says, what conflicts or is missing.
- **Recommendation / decision:** …
- **Outcome:** YYYY-MM-DD — evidence (probe file, commit, PO answer).
```
