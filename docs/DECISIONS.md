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
| DEC-01 | RIC day field: padded or not | SETTLED (PO) | — |
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
| DEC-45 | RIC form policy | SETTLED (PO) | — |
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
| DEC-80 | Logging setup and the import-boundary test | ENG | — |
| DEC-81 | Domain value types | ENG | — |
| DEC-82 | RIC module | ENG | — |
| DEC-83 | History port, LSEG adapter and batched requests | ENG · VERIFY (error codes) | P1-04 |

---

## A. Raised during planning

### DEC-01 — RIC day field: zero-padded or not
**Status:** SETTLED · **Basis:** PO, 2026-09-26, on the earlier project's measurements (LDG §3) · **Affects:** P1-02, P1-04, INV-11, Spec › RIC builder

- **Conflict:** Spec › RIC builder says "Day not zero-padded", and INV-11 cites `AAPLF52619000.U^F26`. LDG §3, measured in Aug–Sep 2026, says the opposite: the day is always two digits (`05`), and unpadded RICs didn't resolve. `lseg_client.build_option_ric` pads the day, and its parser rejects `AAPLF52619000.U^F26` (checked Sep 25).
- **Recommendation:** P1-04 probes both spellings of the same expired contract (`AAPLF52619000.U^F26` vs `AAPLF052619000.U^F26`), and the result goes to the PO.
  - The builder emits whichever spelling resolves (padded, if the guide is right). The parser accepts both.
  - If the padded form wins, amend the spec's RIC line and INV-11 to four checks:
    1. The spec's examples parse to the correct contract.
    2. The builder emits the verified spelling.
    3. Building then parsing round-trips the canonical form.
    4. Live contracts get no caret.
- **Outcome:** 2026-09-25 (interim, asked at P1-02, since the probe comes later) — PO: "Padded, provisional."
  - The builder emits the padded spelling (`AAPLF052619000.U^F26`), and the parser reads both. The spec's unpadded example is tested to parse to the right contract, not to rebuild as written (`tests/unit/data/test_ric.py`).
  - The spec's RIC line and INV-11 stay as written until the P1-04 probe settles this entry. If the probe shows the unpadded spelling resolves instead, the builder changes in one place, `_day_field` in `pmcc/data/ric.py` (DEC-82).
- **Outcome:** 2026-09-26 — PO: "yes the work from the previous project covered it and I know it works - maybe we just make a note in case something breaks."
  - Settled as zero-padded, with no probe; P1-04 no longer checks the spelling. Spec › RIC builder and INV-11 are amended to the four checks above.
  - **If it breaks:** a wrong day spelling shows up as every strike of an expiry dated the 1st–9th coming back unanswered, while expiries dated the 10th or later answer. Check the spelling first. It is set in one place, `_day_field` in `pmcc/data/ric.py`, and the parser already reads both spellings.

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
**Status:** SETTLED · **Basis:** PO, 2026-09-26 (with DEC-01), on the earlier project's measurements (LDG §3)

- **Unexpired contracts:** an expiry on or after the fetch date uses the live form only (Spec › RIC builder).
- **Expired contracts:** ask the caret form first, then the live form for whatever didn't answer. The changeover takes days (LDG §3). Record `ric_form_used`.
- **Puts:** put carets use the **call** month letter (`^F26` for a June put).
- **Strike limit:** a strike above $999.99 raises.
- **OCC symbols:** follow `occ_symbol()`.
- **Outcome:** 2026-09-26 — implemented in `pmcc/data/ric.py` (P1-02, DEC-82). `forms_to_ask()` gives the forms in asking order, `build_ric()` raises above $999.99, and `occ_symbol()` matches LDG §3.
- **Outcome:** 2026-09-26 — PO, in the DEC-01 answer: the call-letter caret for puts and the caret-then-live order for expired contracts come from the earlier project's measurements, so both are now in Spec › RIC builder. The status was ENG until then.

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
- The fetch passes `end + 1 day`, because LSEG's end is effectively exclusive (LDG §2).
- **Outcome:** 2026-09-26 — the provider port takes an exclusive end (`end_exclusive`, DEC-83) and passes it to LSEG unchanged, so the day is added by `pmcc fetch` (P1-08), not by the adapter as this entry first said.

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
| Unanswered contract | the service answers a RIC, asked alone, with a no-data code (never listed; a field it doesn't carry) or with no bars in the window | Soft: empty series, manifest `unanswered`, log event `fetch.ric.unanswered`. A RIC that doesn't come back with bars in its batch is asked again alone first, since only a single-RIC answer settles it (LDG §4.4) |
| Transient provider error | timeout; refused connection; an HTTP status or permission code; an answer that can't be read | Ask the same request again: 3 attempts, with backoff (2 s, 4 s); a failure that persists is an outage |
| Outage | session not `Opened`; a failure that persists through 3 attempts | Fail loud: abort the unit, write nothing, exit non-zero (LDG §4.3) |
| Engine error | look-ahead request; uncovered short; quantity mismatch | Crash the run; nothing written |
| Invariant violation | NAV doesn't reconcile | Run exits non-zero; no result file |

- **Outcome:** 2026-09-26 — the data-layer classes are implemented in P1-03 as `NoDataError`, `UnreadableAnswerError`, `TransientError` and `ProviderOutageError` (`pmcc/data/provider.py`). DEC-83 records exactly which errors fall in each class and how each is retried. Two rows changed from the first version of this table:
  - "Batch rejected whole" was a transient error, retried as a batch. A batch is now split instead, and each RIC is settled on its own.
  - An HTTP status, a permission code, and a single RIC's answer that can't be read are now failures that are retried and then fail loud. They were never meant as "no data", but lseg-data reports them in the same `LDError` as a never-listed RIC, and the P1-03 review found the first version filing them as unanswered (DEC-83).

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

### DEC-80 — Logging setup and the import-boundary test
**Status:** ENG · **Affects:** P0-07, P1-03, P1-08, P3-07

- **Where:** `pmcc/log.py` holds `configure_logging(command, log_dir=Path("logs"))`. A command calls it once at startup; every other module logs through `structlog.get_logger()` and never imports `pmcc.log`, so `accounting` and `pricing` can log without breaking ARCHITECTURE §3.3 rule 4. A new rule 7 enforces this.
- **Sinks:** each event is one JSON line (`sort_keys`), printed to stderr and appended to `logs/{command}_{UTC yyyymmddThhmmssZ}.jsonl`. The file is opened per event with `newline="\n"` (DEC-58), so a crash never loses a buffered line and Windows writes LF. No stdlib `logging` handlers: `FileHandler` can't be told to write LF on Windows.
- **Fields:** `event`, `level`, `timestamp` (ISO 8601, UTC, `Z`), `command`, plus the call's keyword fields; exceptions render as text under `exception`. Level INFO and up.
- **Wiring:** the command stubs don't configure logging yet. Each command calls `configure_logging` when its backlog item builds it (first `pmcc probe`, P1-04, and `pmcc fetch`, P1-08).
- **Import test:** `tests/architecture/test_imports.py` parses every module under `pmcc/` with `ast`, resolves relative imports, and treats `from a import b` as importing `a.b`, so `from pmcc import data` counts as `pmcc.data`. Imports inside functions and `TYPE_CHECKING` blocks count. Dynamic imports (`importlib`) are not scanned.
- **Outcome:** 2026-09-25 — logging tests pass (stderr and file carry the same events, LF only). A `pandas` import planted in `pmcc/engine/` failed the import test with `rule 1: pmcc.engine.planted imports pandas`, then was removed.

### DEC-81 — Domain value types
**Status:** ENG · **Affects:** P1-01, and every package that uses `pmcc.domain`

- **Modules:** `money` (`Price`, `Money`), `instruments` (`OptionId`, `Right`, `Side`), `rules` (`RuleId`), `clock` (ET, `bar_end`), `sessions` (`Session`, `session_of`). `pmcc.domain` re-exports them.
- **`Price` and `Money`** are frozen dataclasses around one `int` of $0.0001 units (DEC-44), not bare ints, so they can't be mixed by accident: `Price + Money` and `Money * 1.5` raise `TypeError`, and a float for units is refused. `Price.notional(multiplier, qty)` is the only way from a price to cash, and it's exact.
- **Quantizing:** `from_dollars` rounds half-even, in exact arithmetic (a `Fraction`), so no decimal context can round twice.
  - A float (numpy's `float64` included) is read by its shortest repr. So `1.23445` is quantized as the printed quote, a tie, to `1.2344`. Its binary value, `1.23445000000000004…`, sits just above the tie and would round up to `1.2345`.
  - The P1-07 loader's vectorized quantizing must agree with this function, and is to be tested against it.
- **Dollars out:** `to_dollars()` is exact and always has 4 decimal places, whatever the decimal context.
- **`OptionId`:** root, expiry, right, strike. The strike is a `Price` in whole cents (the RIC encodes cents); the $999.99 RIC limit is the RIC builder's check (DEC-45), not this type's.
- **`RuleId`:** a `str` subclass that accepts only the spec's shape (`E-T1`, `G-3`, `X-S5`, …: one digit 1–9). Whether the config defines the ID is checked there (INV-09).
- **Sessions (DEC-06):** a `Session` is a day and its close (16:00, or 13:00 on a half-day). Its session bars end on the hour from 10:00 through the close. `session_of(bar_end, sessions)` returns `None` for extended-hours bars, the post-close stub and non-trading days. This follows DEC-06's recommendation; the P1-04 probe verifies it. Which days trade and which are half-days comes from the calendar (P1-06).
- **`bar_end`:** a naive start is LSEG's UTC stamp. The hour is added in UTC, then converted to ET, so it is elapsed time even across a DST change.
- **Outcome:** 2026-09-25 — domain tests pass, including half-even ties, money arithmetic, `bar_end` under EDT, EST and the fall-back hour, and session-bar classification on a regular day and a half-day.
- **Outcome:** 2026-09-25 — an adversarial review (4 reviewers, 2 skeptics per finding) confirmed 4 defects, all fixed with regression tests: `np.float64` was rejected by `from_dollars`; ruff failed on the new files; the §4.1 table in ARCHITECTURE was broken; and this entry described the float's binary value the wrong way round. Also fixed from its plausible findings: double rounding past 28 significant digits, `to_dollars` losing its 4 decimal places on huge amounts, and a missing test for a non-UTC aware `bar_end` start.
  - Process gap: `pre-commit run --all-files` skips files git doesn't track, so `just check` passed before the new files were staged. Until that's closed, run `uv run --frozen ruff check pmcc tests` and `uv run --frozen ruff format --check pmcc tests` before handover.

### DEC-82 — RIC module
**Status:** ENG · **Affects:** P1-02, and the code that builds or reads RICs (P1-03, P1-04, P1-07, P1-08, the blotter's instrument column)

- **API (`pmcc/data/ric.py`):**
  - `build_ric(option, form)`, and `parse_ric(ric)` → `ParsedRic(option, form)`.
  - `forms_to_ask(expiry, fetch_date)` is the DEC-45 policy, returned as the forms to ask in order: `(live,)` when the expiry is on or after the fetch date, otherwise `(expired, live)`.
  - `occ_symbol(option)`, and `MAX_STRIKE` ($999.99).
  - `RicForm` is `live` or `expired`, the values recorded as `ric_form_used`. `build_ric` also takes the value as text, as a manifest stores it, and raises on anything else rather than quietly building the live form.
- **Day spelling:** the builder zero-pads the day (DEC-01). The parser reads both spellings: 8 digits after the month letter are an unpadded one-digit day, 9 are a two-digit day.
- **The parser is strict.** Anything else raises `ValueError`, so a malformed RIC can't pass for a contract:
  - upper case and ASCII digits only, `.U` required, no surrounding whitespace
  - the date must exist, and the strike must be at least $0.01
  - a caret must be the expiry's call letter and year, so a put-letter caret (`^R26`, which returned no puts in LDG §3) is refused
- **Roots:** whatever `OptionId` allows (upper-case letters and digits, starting with a letter). The month letter is always the last letter before the RIC's digits, so digits in a root can't make a parse ambiguous.
- **Two-digit years:** both builders raise for an expiry outside 2000–2099 rather than wrap the year.
- **OCC symbol:** the root is at most 6 characters and the strike at most 8 digits of $0.001 ($99,999.99); anything wider raises.
- **Outcome:** 2026-09-26 — the INV-11 tests pass (`tests/unit/data/test_ric.py`, 92 tests, including hypothesis round-trips over random contracts under the `dev` and `ci` profiles). Two one-off checks outside the suite:
  - a sweep of 609,000 build-then-parse round-trips: every calendar day of 2000–2099 × both rights × both forms, with digit roots and more strikes on the 1st–3rd of each month, and every day under 10 also parsed unpadded
  - every one of the 2,399 wrong caret suffixes the grammar allows, refused for both a call and a put
- **Outcome:** 2026-09-26 — an adversarial review (4 reviewers, 2 skeptics per finding; 12 unique findings) confirmed 2 defects and rated 7 plausible. All 9 are fixed, with regression tests:
  - **Confirmed:** the tests pinned only 6 of the 24 month letters. Build and parse share one table, so a round-trip couldn't see a transposed letter, and January and December (the LEAPS months) were unpinned. Every letter and caret is now checked against the grammar spelled out independently in the test. Also, this entry and a code comment said the month letter is the RIC's last letter; it is the last letter before the digits.
  - **Plausible:** `build_ric` quietly built the live form for a form passed as text (`"expired"` read back from a manifest). It now reads the text value and raises on anything else. New tests cover trailing whitespace, a separator other than a dot, non-ASCII digits in every field, float-truncated strikes, and every field of the OCC symbol. PRD FR-D3 now names the tests behind the caret-then-live order. This entry's caret figure covered only 71 suffixes and is now exhaustive.
  - The review's surviving mutants, plus a few more (17 in all), were re-run against the new tests. All are killed except one equivalent mutant: `\d` in the caret group still refuses non-ASCII digits, because the caret must equal the ASCII suffix exactly.
  - 3 findings were refused by both skeptics and left as they are. One of them, about how RIC forms interact with the DEC-46 hash, is worth raising when DEC-46 is asked at P1-07.

### DEC-83 — History port, LSEG adapter and batched requests
**Status:** ENG · VERIFY (the service's error codes) · **Verify at:** P1-04 · **Affects:** P1-03, P1-04, P1-07, P1-08, DEC-47, DEC-49

- **Where things live.** ARCHITECTURE §3.3 rule 2 lets only `fetch` and `cli` import the adapter, so the parts that don't talk to LSEG sit outside it:
  - **`pmcc/data/provider.py`:** the `HistoryProvider` port, `RawHistory`, `Interval` and the four failure classes. There is no LSEG code here, so `fetch` can catch the failures without importing the adapter.
  - **`pmcc/data/lseg/`:** `api.py` (`LsegApi`, the slice of `lseg.data` that is called), `session.py` (`lseg_session`), `shapes.py` (`to_long`) and `provider.py` (`LsegProvider`).
  - **`pmcc/data/fetch.py`:** batches, verdicts, retries, the caret→live fallback and diagnostics (`fetch_rics`, `fetch_contracts`). None of it depends on LSEG, so it goes in `fetch.py` (ARCHITECTURE §3.1) rather than under `lseg/`, where the P1-03 item first put it. P1-08 adds unit orchestration and resume to the same module.
- **Rows:** long `(bar_start, ric, field, value)`, one row per non-empty cell, sorted by RIC, field and time. `bar_start` is LSEG's own stamp, unshifted: a UTC datetime for hourly bars and a date for daily ones. `bar_end` is added at load (P1-07).
- **What lseg-data 2.1.1 does.** Read in its source, and pinned by `tests/unit/data/test_lseg_contract.py`, which runs the library's own code offline:
  - `get_history` asks the historical-pricing service once per RIC, in parallel, and hourly requests page.
  - A transport failure in any RIC's request fails the whole call. lseg-data keeps only the exception's text and raises a new `LDError(message=…)`: no class, no cause, no code.
  - If no RIC answered, it raises an `LDError` whose text starts "No data to return" and lists each distinct failure once: a service code such as `TS.Intraday.UserRequestError.90001` (a never-listed RIC), or an HTTP status (a failing or signed-out Workspace). Each message is cut at its first dot, so a RIC loses its `.U`.
  - A desktop session never leaves Opened on its own. A dead Workspace shows up only as failing requests.
  - **Frames:**
    - One RIC gives flat field columns.
    - Several RICs give a `(RIC, field)` MultiIndex when the first RIC to answer carries two or more fields. When it carries one, they give flat RIC columns named after the last RIC's field. A RIC whose answer carries more fields then spills into its neighbour's column, or the build raises (`IndexError`, `ValueError`).
    - An hourly batch holding a RIC that failed can't be built: a failed page leaves a raw with no headers, which raises the `UniverseContainer` TypeError of LDG §4.4. A daily batch answers without the failed RIC and raises nothing.
- **Failure classes (how DEC-49 is applied).** They share no base class, so nothing can catch an outage by accident.
  - **`NoDataError` (soft):** an `LDError` whose every code is a no-data code, `TS.*.UserRequestError.*`. It carries the codes.
  - **`UnreadableAnswerError`:** any other class of error from `get_history` (raised while lseg-data builds its frame), or a frame whose columns can't be attributed. A batch is split. A single RIC can't be, so its unreadable answer is asked again like a transient failure and ends as an outage.
  - **`TransientError`:** any other `LDError` (a flattened transport failure, an HTTP status, a permission code, a failure with no code), or an unwrapped `TimeoutError`, `ConnectionError` or httpx `TransportError`. It gets 3 attempts in all, 2 s and then 4 s apart, and then counts as an outage.
  - **`ProviderOutageError` (loud):** the config is missing, opening raises, or the session isn't Opened before a request (Pending counts as not open); any error raised once the session is no longer open; any failure that persists through 3 attempts.
- **A RIC is unanswered only on the service's word, given to that RIC alone.**
  - `fetch_rics` asks in batches of 25, and every RIC that doesn't come back with bars is asked again on its own.
  - A RIC's verdict is its bars, a no-data code (`MissReason.NO_DATA`, with the codes), or no bars in the window (`MissReason.EMPTY`).
  - A rejected batch's codes don't say which RIC got which, so a batch never settles a RIC.
  - **Cost:** one extra request for each RIC that doesn't answer in its batch. An hourly batch holding a missing RIC costs 1 + 25 requests, as it did in the earlier project.
- **Answers that can't be attributed are rejected, not guessed.** How the port departs from LDG's `to_long`:
  - Flat RIC columns are trusted only when a single field was asked, and only under that field's name. LDG's filed unnamed ones under the first field asked, and trusted the name, which lseg-data takes from the last RIC.
  - Field columns for several RICs, columns that match no RIC or field asked, and a MultiIndex with no level holding an asked RIC are rejected. LDG's dropped the first and guessed the other two.
  - Columns for RICs nobody asked for are dropped. LDG's kept them under LSEG's spelling.
  - An answer that isn't a DataFrame is rejected. LDG's treated it as empty.
- **Session:**
  - `lseg_session()` yields an `LsegProvider`, not the module.
  - The config is found at the repo root and passed to `open_session(config_name=…)`. lseg-data reads it; pmcc only checks that it exists.
  - `lseg.data` is imported only when a session opens, so importing pmcc stays offline. A test checks this in a fresh interpreter.
- **Counting and logs:**
  - A `RicsResult` refuses to exist unless every RIC asked is answered or missed, never both (LDG §5). `fetch_contracts` counts per contract. A hypothesis test covers both forms and live-only contracts.
  - `fetch_rics` logs each unanswered RIC once as `fetch.ric.unanswered`, with `ric`, `form` (for an option RIC), `reason`, `codes` and `message`. A caret miss is logged even when the live form then answers: it is a fact about that RIC.
  - `fetch.batch.rejected` and `fetch.retry` are logged as they happen. `symbol` and `unit` join the events when P1-08 binds them.
- **Test double and contract test:**
  - `FakeLseg` (`tests/fakes/lseg.py`) ports what lseg-data does with the service's answers: per-RIC answers, the flattening of transport failures, the `validate_responses` message, and `HistoricalBuilder` with its quirks. `fake_provider(fake)`, the real `LsegProvider` over it, is the FakeProvider of TEST-STRATEGY §6.
  - `tests/unit/data/test_lseg_contract.py` feeds the fake's answers to lseg-data's own code: its builder, `validate_responses`, paging and `get_hp_data`. The library runs in a separate interpreter with sockets blocked and its config lookup pointed at an empty folder, and it must give the same frames, messages and raws. An lseg-data upgrade that changes any of it fails there.
  - Tests import pandas to build frames, and import lseg.data only in that separate interpreter. The import rules of ARCHITECTURE §3.3 cover `pmcc/` (DEC-80). Tests import the fake as `tests.fakes`, so pytest gets `pythonpath = ["."]`.
- **pandas typing:**
  - pandas has no type stubs, and pyright strict can't see through its return types. The four files that handle pandas frames (`pmcc/data/lseg/shapes.py`, `tests/fakes/lseg.py`, `tests/unit/data/test_lseg_provider.py`, `tests/unit/data/test_lseg_contract.py`) turn off pyright's unknown-type and missing-stub reports at file level. Everything else stays strict.
  - In `shapes.py`, `to_long` checks the frame and reads its column labels, and `_wide` and `_stamps` convert it. The alternative, `pandas-stubs`, would be a new dependency and needs the PO.
- **Verify at P1-04:**
  - lseg-data itself names 90001 as "universe is not found". The daily never-listed code, the missing-field code and what a signed-out Workspace returns are assumptions in the fake.
  - The probes record the real `LDError` text for a never-listed RIC (hourly and daily, both forms), a field the RIC doesn't carry, and an hourly batch holding one of each.
  - If a guessed RIC comes back with a code that isn't a `UserRequestError` code, the fetch stops as an outage rather than record the RIC as unanswered. Widening the no-data codes is then a decision recorded here.
- **Residual risks,** which `get_history` doesn't let the adapter see:
  - A transport error whose text is empty makes lseg-data return an empty frame, which reads as `EMPTY`. httpx's transport errors carry text, and P1-08's coverage summary flags a unit with no answers.
  - An hourly RIC whose later page fails over HTTP comes back truncated but answered. The window's ~800 hourly bars per contract are expected to fit one page.
- **Outcome:** 2026-09-26 — first version: 63 tests, INV-12 included; 15 planted mutants killed.
- **Outcome:** 2026-09-26 — an adversarial review (4 reviewers, then 2 skeptics per finding) found 38 findings, 24 of them unique. The 12 most severe were verified: 9 confirmed, 2 plausible, 1 refuted. All 11, and the 12 unverified low findings, are fixed with regression tests; the design above is the result.
  - **Confirmed, high:** real lseg-data flattens transport failures into bare `LDError` text and never moves a desktop session out of Opened. So a dead or signed-out Workspace was filed as "no data", against LDG §4.3 and the CLAUDE.md hard rule. The first version classified by exception class and by `open_state`, and the fake raised shapes lseg-data never produces.
  - **Confirmed, high:** lseg-data names flat RIC columns after the last RIC's field and spills values across RICs, so the port could file one field's values under another.
  - **Confirmed, medium:**
    - a flat-RIC test couldn't tell the columns' name from the first field asked;
    - `fetch_rics` logged nothing for an unanswered RIC;
    - outages during the one-at-a-time asks and between form rounds were untested;
    - this entry handed the real-error check to P1-04 with no step there;
    - the fake's outages were ones lseg-data can't produce.
  - **Confirmed, low:** the log's `forms` key against ARCHITECTURE §15's `form`, and this entry undercounting how the port departs from LDG's `to_long`.
  - **Plausible:** Pending was untested; the "raises only `ProviderOutageError`" docstrings were false; `Retry(attempts=0)` faked an outage.
  - **Refuted:** pandas in tests. The import rules cover `pmcc/`.
  - **Now:** 110 tests in the four P1-03 files (362 in the suite). Another 16 mutants planted in the new guards were all killed: the no-data code rule twice, the `LDError` match, closed-during-a-call, Pending, settling left-out RICs, splitting and retrying unreadable answers, filtering unasked RICs, single-RIC batches, zero attempts, the log event and its form, the sort, and both flat-RIC checks.

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
