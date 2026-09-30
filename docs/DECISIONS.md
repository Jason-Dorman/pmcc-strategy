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
| DEC-06 | Bar timestamps, decision time, session bars | SETTLED (PO) | — |
| DEC-07 | Backtest window | SETTLED (PO) | — |
| DEC-08 | Long-dated coverage | VERIFY: NVDA measured (P1-09); QQQ, TSLA at P1-10 | P1-10 |
| DEC-09 | Live-contract RIC form | SETTLED (spec, probed) | — |
| DEC-10 | Reg T and FINRA 4210 citations | SETTLED (PO): hedged short stock after X-S5 · citations found | quotes by P7-04 |
| DEC-11 | Risk-free rate | SETTLED (PO) | — |
| DEC-12 | Per-symbol identifiers, splits, max strike | SETTLED (PO) | — |
| DEC-13 | Hourly field availability | SETTLED (spec, probed) | — |
| DEC-14 | Strike increments | ENG method · values probed · unmeasured anchor SETTLED (PO) | — |
| DEC-15 | Universe size | SETTLED (PO) | — |
| DEC-16 | Fetch coverage summary | SETTLED (PO) | — |
| DEC-20 | Week-open session and order of operations | SETTLED (PO) | — |
| DEC-21 | Selection freeze and E-T1 | SETTLED (PO) | — |
| DEC-22 | Gates and the gate log | SETTLED (PO) | — |
| DEC-23 | Spot, close, ITM at expiry | SETTLED (PO) | — |
| DEC-24 | Time to expiry and Greek units | SETTLED (PO) | — |
| DEC-25 | ATM strike, ATM IV, expected move | SETTLED (PO) | — |
| DEC-26 | RV20 | SETTLED (PO) · a missing close: ASK | asked 2026-09-29 (P2 review) |
| DEC-27 | Greeks for held contracts; fresh quotes only | SETTLED (PO) | — |
| DEC-28 | Exits without a valid quote; when the long is checked | SETTLED (PO) | — |
| DEC-29 | Tie-breaks | SETTLED (PO) | — |
| DEC-30 | Starting capital (E-L4) | ASK | P3-09 |
| DEC-31 | Entry-timing sensitivity | ASK | P5-02 |
| DEC-32 | Point-in-time listing | SETTLED (PO) | — |
| DEC-33 | Expiry calendar | SETTLED (PO) | — |
| DEC-34 | Rule stamping for multi-rule events | SETTLED (PO) | — |
| DEC-35 | Rule write-up: names and rationales | SETTLED (PO) | — |
| DEC-40 | Source of truth | SETTLED (PO) | — |
| DEC-41 | Frontend stack follows the spec | SETTLED (spec) | — |
| DEC-42 | Python environment | ENG | — |
| DEC-43 | Packages added to the spec layout | ENG | — |
| DEC-44 | Money as integer units | ENG | — |
| DEC-45 | RIC form policy | SETTLED (PO) | — |
| DEC-46 | Cache layout | SETTLED (PO) | — |
| DEC-47 | Fetch dates are inclusive | ENG · probed (LSEG's date edges) | — |
| DEC-48 | Fetch plan and band-edge guard | ENG | — |
| DEC-49 | Failure taxonomy | ENG | — |
| DEC-50 | Canonical results and INV-13 | SETTLED (PO) | — |
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
| DEC-83 | History port, LSEG adapter and batched requests | ENG · error codes verified | — |
| DEC-84 | Calendar, chain discovery and the fetch plan | ENG | — |
| DEC-85 | Probe design | ENG | — |
| DEC-86 | Universe config and strict YAML | ENG | — |
| DEC-87 | Cache writes, sidecars and the loader | ENG | — |
| DEC-88 | The fetch command: plan, estimate, unit loop | ENG | — |
| DEC-89 | Pricing: Black-Scholes, the IV solver, measures, the chain pricer | ENG | — |
| DEC-90 | Strategy config: kinds, the loader and the config hash | ENG | — |
| DEC-91 | MarketView, synthetic market, accounting, fills, rules, engine loop | ENG · 3 edge cases put to the PO | handover 2026-09-30 |
| DEC-92 | Results: models, canonical JSON, the manifest and `pmcc run` | ENG | — |

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
**Status:** SETTLED · **Basis:** PO, 2026-09-28, on the P1-04 probes · **Affects:** loader, MarketView, every rule

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
- **Outcome:** 2026-09-27 — probed on all 12 symbols over the last 5 sessions, Sep 21–25 2026. Daily bars came back for Sep 22–25 only (DEC-47), so 48 sessions were compared. Reports are in `data_cache/probes/` (DEC-85).
  1. **Bars are stamped at their start.** Every option's hourly bars start 09:00–16:00 ET, and every Nasdaq stock's (`.O`) start 04:00–19:00. That is the 09:30–16:00 option session plus a stub, and the 04:00–20:00 extended stock session. End stamps would read 10:00–17:00 and 05:00–20:00.
  2. **Quotes are end-of-bar values.** The daily closing BID/ASK equals the final quote of the bar starting 16:00 in 48 of 48 sessions, because the day's last quote comes at or after 16:00. For single-stock options it also equals the final quote of the bar starting 15:00 in 16 of 28 sessions (AMD 4/4, NVDA 3, TSLA 3, JPM 3, AAPL 2, COIN 1, META 0), which a start-of-bar value couldn't. ETF options (SPY, QQQ, IWM, TLT, XLE) trade until 16:15, so their closing quote always falls in the stub (0 of 20 in the 15:00 bar).
  3. **Check 1 fails as written: the official close is not the close bar's last trade.** The daily TRDPRC_1, the closing auction, equals the last trade of the bar starting 15:00 in only 9 of 48 sessions. The two differ by up to 0.09% (JPM), most by under 0.03%. Points 1 and 2 still prove start stamps and end-of-bar quotes.
- **For the PO at P1-05:** the recommendation stands: `bar_end = bar_start + 1h`, decisions at `bar_end`, session bars ending 10:00–16:00 (13:00 on a half-day), and the 16:00 stub kept for provenance only. Point 3 also goes to DEC-23 (closing spot, ITM at expiry): the close bar's last trade sat up to $0.40 from the official close (META; AMD $0.33, JPM $0.31, TSLA $0.27), and that close decides exercise.
- The probe used the first stock suffix that answered (DEC-85). For SPY, IWM and XLE that was the NYSE venue (`.N`, bars 07:00–16:00), not their Arca primary (`.P`), so their stock-side spans are that venue's.
- **Outcome:** 2026-09-28 — PO, asked at P1-05, confirmed the recommendation as it stands above.
  - `bar_end = bar_start + 1h` is the only timestamp after load, and decisions happen at `bar_end`.
  - Session bars end 10:00–16:00 (13:00 on a half-day).
  - The 16:00 stub is kept for provenance only. ETF options quote until 16:15, so their closing quote falls in the stub and never drives a decision, mark or fill.
  - The domain's session model (P1-01, DEC-81) already follows this, so no code changes.

### DEC-07 — Backtest window
**Status:** SETTLED · **Basis:** PO, 2026-09-28, on the P1-04 probes · **Affects:** `configs/universe.yaml`, fetch plan, Spec › Universe

- **Spec:** one window for all symbols, as long as hourly option history allows and at least 10 weeks.
- **Recommendation:**
  - Probe how far back hourly BID/ASK goes, per symbol, for expired near-the-money weeklies and for live long-dated calls.
  - **Start:** the first week-open session by which all 12 symbols have data.
  - **End:** the final session of the last complete week before the universe fetch begins.
  - Fix both in `universe.yaml` before the first published run.
- **Outcome:** 2026-09-27 — probed on all 12 symbols, sampling weeks 1–18 months back (DEC-85):
  - **Hourly history ends somewhere between Sep 26 and Oct 27 2025, the same for every symbol.** Of the 11 symbols with 10- and 11-month samples (NVDA ran the first version, which had none), all had stock bars in the week of Oct 27 2025 (11 months back), and none had any bars in the week of Sep 22 2025, 366–370 days before the probe. The samples bound the edge but don't place it. They fit a rolling 365-day limit, under which the oldest data moves forward a day each day.
  - **Not every leg reaches that far.** The week of Oct 27 2025 had a weekly call with valid mids for 10 of those 11 (XLE's didn't), and a long call for 10 (SPY's didn't). NVDA is shown back to the week of Dec 22 2025 only. `back_to` in each report is the reach with no gap in any more recent sample: long calls reach no sample for SPY, JPM and XLE, because of the gaps below.
  - **The gaps.**
    - Long calls: SPY, JPM and XLE one month back (the Feb 19 2027 monthly, not yet listed at 179 DTE), SPY 10–11 months back, QQQ 4 months back. These look like monthlies not yet listed.
    - TLT's weekly 3 months back did answer but had no valid mid on any session bar: a quote gap, not a listing gap.
    - XLE's weekly 10–11 months back, and its long call 10 months back, didn't answer because the probe asked the wrong strikes: LSEG's daily closes are split-adjusted (DEC-12), so for weeks before XLE's 2-for-1 split on Dec 5 2025 the $10 anchor from the adjusted close ($40) was about half the traded price. These samples say nothing about XLE's history there. Any fetch reaching before the split must ask unadjusted (2x) strikes.
    - DEC-08 and DEC-32 cover how listing and quote gaps reach the rules.
- **For the PO at P1-05:** the spec asks for the longest window the history allows, and at least 10 weeks. The limits:
  - history back to somewhere between Sep 26 and Oct 27 2025 (proven only from Oct 27, and for NVDA only from Dec 22), moving forward a day each day;
  - the stock's 30-session warm-up before the start;
  - XLE's split on Dec 5 2025: a window starting after it avoids adjusted contracts;
  - fetch volume, which grows with the window. ARCHITECTURE §6.3 estimates ~700 requests (~16 min) per symbol for 11 weeks; a 40-week window is roughly 4 times that.
- **Outcome:** 2026-09-28 — PO, asked at P1-05: **Mon Mar 30 2026 to Fri Sep 25 2026, 26 weeks and 125 sessions**, in `configs/universe.yaml`.
  - **The choice.** The PO was offered three windows:
    - Dec 8 2025, 42 weeks. The longest the proven history allowed, and the recommendation.
    - Jan 12 2026, 37 weeks.
    - Mar 30 2026, 26 weeks. The question put its fetch at about two-thirds of the 42-week one, at the cost of 16 weeks of sample.

    The PO took the shortest. Spec › Universe said "as long as LSEG hourly option history allows"; it now names this window and cites this entry.
  - **End:** Fri Sep 25 2026, the final session of the last complete week before the universe fetch (P1-09 onward).
  - **What the window avoids:** the stock tape's 30-session warm-up starts Fri Feb 13 2026. That is 10 weeks after XLE's split and 3½ months inside the history's edge. So it doesn't matter exactly where the edge falls, or whether LSEG's hourly stock bars are split-adjusted like its daily ones (DEC-12).
  - **Checked** in `tests/unit/config/test_universe_file.py` (DEC-86):
    - the start is a week-open session and the end a week-final one;
    - 26 weekly expiries;
    - the real fetch planner, run over the window, asks for nothing outside `configs/calendar.yaml`: its expiries run to the Jun 17 2027 monthly, the last within 270 DTE of Sep 25.
  - r for this window: DEC-11.

### DEC-08 — Long-dated coverage
**Status:** VERIFY · **Verify at:** P1-04, P1-09, P1-10 · **Affects:** E-L3 candidate sets, Methodology

- **Measure per symbol:**
  - Share of session bars with a valid mid for 0.70–0.90 delta monthly calls at 120–270 DTE.
  - Median spread %.
  - Count of IV failures. A deep ITM mid below `S − K·e^(−rT)` has no IV (see DEC-27).
- Sparse data means fewer candidates and more E-T1 retries. That is reported on the Methodology page. The rules stay unchanged.
- **Outcome:** 2026-09-27 (P1-04's sample; the full measure is P1-09's) — calls on the Mar 19 2027 monthly (175 DTE), at strikes spanning about δ 0.90–0.70 (Black-Scholes with r = 0 and 60-session realized volatility), over the last 20 sessions. That is 75 contracts across the 12 symbols, 140 session bars each.
  - **Every contract had a valid mid on every session bar** (10,500 of 10,500). TLT got one strike ($75): the probe took the strike step measured at 0.8 × spot ($5), while the same expiry lists $1 strikes nearer the money, so this says nothing about how many TLT strikes are listed.
  - **Median spread as a % of mid:** QQQ 1.4, NVDA 1.4, TSLA 2.1, META 2.7, AAPL 2.7, AMD 3.002, IWM 3.2, SPY 3.5, JPM 4.6, COIN 6.3, XLE 7.5, TLT 9.6. E-T1 allows a long entry only at ≤ 3%, so on 7 of the 12 (AMD just over) the median long candidate fails E-T1. Expect retries and fewer E-L3 candidates there (R-03, R-14). The rules stay unchanged, as above.
  - **Below intrinsic** (mid < S − K, a lower bound on IV failures): 1 bar (TLT).
  - Not every monthly that is 120–270 DTE is listed at every date: SPY's Feb 2027 monthly had no bars in the week of Aug 24 2026 (179 DTE); the probe asked Jan 2027 only in the week of Jul 27 2026, where it answered (DEC-07's gaps).
- **Outcome:** 2026-09-28 — reported to the PO at P1-05, with no question, since the spec fixes the rules.
  - On the 7 symbols whose median long spread exceeds 3%, expect late long entries, and perhaps none on TLT or XLE.
  - Measured in full over the window's own monthlies (Aug 2026 – Jun 2027, DEC-07): NVDA at P1-09, the other 11 at P1-10.
- **Outcome:** 2026-09-28 — the PO cut the universe to QQQ, NVDA and TSLA (DEC-15), the three with the tightest long-leg spreads (1.4%, 1.4%, 2.1%). NVDA is measured at P1-09, QQQ and TSLA at P1-10.
- **Outcome:** 2026-09-28 — **NVDA, measured in full at P1-09**, on the cached chain (63 units, fetched Sep 29 01:54–02:34 UTC).
  - **What was measured:** every answered monthly call on every session bar of the window (875) where it is 120–270 DTE and its Black-Scholes delta is 0.70–0.90. The delta uses r = 0.0371 (DEC-11), T = DTE ÷ 365, and σ = RV20 as of the prior session. The pricer is P2's, so the band is an estimate; it doesn't depend on the contract's own quote, so a contract that didn't quote is still counted. This was a one-off script over `load_symbol`, not a command.
  - **Every session bar has at least one in-band long candidate with a valid mid** (875 of 875), across 10 monthlies from Aug 2026 to Jun 2027.
  - **Valid mid:** 90.7% of 47,787 contract-bars (DEC-16's denominator: a bar that never came back counts as no mid). Counted from each contract's first LSEG bar, **100%** (43,327 of 43,327). The whole gap is contracts not listed yet, not missing quotes:
    - **Feb 19 2027** is a candidate from May 26 and first traded Jun 30. **Apr 16 2027** is a candidate from Jul 20 and first traded Sep 11.
    - **May 21 2027** is a candidate from Aug 24 and **wasn't listed by Sep 25**. All 39 strikes and all 9 step anchors came back "not found" (codes 70005 and 90001, as for a never-listed strike). The Jun 17 2027 unit, fetched next in the same session, answered 38 of 38. The unit is cached empty and the coverage summary flags it.
    - Strikes on the near monthlies (Aug–Oct 2026) that NVDA's rise added partway through.
    - This is DEC-32's point-in-time listing, which MarketView must honour (P3-02).
  - **Median spread:** 1.52% of mid; 89.6% of valid bars are within E-T1's 3%. By expiry, the median runs from 1.10% (Jan 2027) to 3.25% (Apr 2027, in its first two weeks of listing).
  - **Below S − K·e^(−rT):** 0 bars, so no IV failures from the no-arbitrage floor. The chain pricer counts the rest (P2-04, DEC-16).
  - Expect E-L3 to find candidates on every week-open session. E-T1 retries will be rare, and most likely on a newly listed expiry.

### DEC-09 — Live-contract RICs
**Status:** SETTLED · **Basis:** Spec › RIC builder, confirmed by the P1-04 probes and reported to the PO at P1-05 (2026-09-28) · **Affects:** P1-02, P1-03

- Long legs still listed at fetch time must resolve in the live form (no caret). LDG §4.13 and §6.3 say they do. Confirm on 3 symbols.
- **Outcome:** 2026-09-27 — confirmed on all 12 symbols:
  - Every live monthly the coverage check asked (75 contracts) answered in the live form, the only form asked.
  - A live contract asked in the caret form never answered: `TS.Intraday.UserRequestError.90001`, 12 of 12.
  - Weeklies expired 9 days earlier answered in the caret form, 12 of 12 (DEC-14's check).

### DEC-10 — Reg T and FINRA 4210 citations
**Status:** SETTLED (the short stock after X-S5: PO, 2026-09-29) · citations found · **Quotes due:** P7-04 · **Affects:** P3-04, Methodology page, Spec › NAV and Reg T

- **Confirm and cite:**
  - A long listed option with 9 months or less to expiry has no loan value (paid in full).
  - A short call is covered at $0 by a long call with a lower or equal strike and a later or equal expiry.
  - Short stock needs 150% initial (proceeds plus 50%) and 30% maintenance.
- **Candidate sources:** Reg T (12 CFR §220.12), FINRA Rule 4210(c) and (f)(2), and Cboe margin rules. Quote the exact paragraphs on the Methodology page.
- **Outcome:** 2026-09-28 — researched at P1-05 in the primary sources. P7-04 re-reads the live text before quoting it.
  - **Sources:**
    - eCFR, 12 CFR 220.12, read through eCFR's API because the page sits behind a bot check. Title 12 was current to 2026-09-24, and §220.12 is unchanged since 1998.
    - FINRA Rule 4210, from the Internet Archive copy of 2026-08-30, spot-checked against the live page. Its latest amendment is SR-FINRA-2025-017, effective June 4 2026.
    - The Cboe Options rule book, updated Sep 21 2026.

  | Claim | Finding | Citation |
  | --- | --- | --- |
  | A long listed option with ≤ 9 months to expiry is paid in full | Confirmed. Reg T leaves listed options to the exchange and FINRA rules, and keeps long options out of its 50% rule. FINRA: "…expires in nine months or less, initial margin must be deposited and maintained equal to at least 100 percent of the purchase price". Cboe says 100% of current market value. Over 9 months it's 75%, a 25% loan value | 12 CFR 220.12(a), (f)(1); FINRA 4210(f)(2)(D); Cboe 10.3(c)(4)(A)–(B) |
  | E-L2's 270 DTE is always within 9 months | Confirmed. Neither rule defines "nine months" in days, and the shortest span of 9 calendar months is 273 days | FINRA 4210(f)(2)(D); Cboe 10.3(c)(4) |
  | A short call is covered at $0 by a long call with a lower or equal strike and a later or equal expiry | Confirmed, as a spread. The conditions: same underlying, all listed, all American (or all European), equal aggregate underlying value, the short expiring on or before the long. The short's margin is the lesser of its naked requirement and the spread's maximum loss, which is $0 here, and "'Long' options must be paid for in full". Spreads need a margin account | FINRA 4210(f)(2)(A)(xxxii), (f)(2)(H)(i), (f)(2)(N)(ii); Cboe 10.3(a)(5)(E), 10.3(c)(5)(C)(v)(a) |
  | Short stock: 150% initial, 30% maintenance | Confirmed for plain short stock. Initial is "150 percent of the current market value". Maintenance is the greater of $5.00 a share and 30%; 30% governs above $16.67, as it does for all 12 symbols | 12 CFR 220.12(c)(1); FINRA 4210(c)(3) |
  | …but X-S5's short stock | **Contradicts the spec's table.** X-S5 sells the stock short by assignment while the long call is held, and the long's strike is below the sale price (the short strike). Reg T then asks "100 percent of the current market value", the proceeds alone. FINRA asks 10% of the call's aggregate exercise price plus its out-of-the-money amount, capped at the (c) amount. E.g. META at $750 against a $600 long needs $6,000 of maintenance, not $22,500 | 12 CFR 220.12(c)(2); FINRA 4210(f)(2)(H)(v)a; Cboe 10.3(c)(5)(C)(iv)(a) |

  - **Also for the Methodology page:**
    - Brokers may require more than these minimums (FINRA 4210(d)(1)(B); Cboe 10.3(c)).
    - A margin account needs $2,000 of equity (4210(b)(4)).
    - FINRA's intraday margin rule, which replaced pattern day trading on June 4 2026, isn't modelled.
    - Interpretation 4210(b)(4)/051 lets an assigned short be closed the same day by exercising the long.
- **Question for the PO at P3-04** (the accounting core, which builds Reg T): after X-S5, which requirement does the short stock carry?
  - **Recommendation:** the hedged requirement the rules give while the long call is held.
    - Initial: the sale proceeds, with no additional 50% (220.12(c)(2)).
    - Maintenance: 10% of the long's strike × shares, plus the long's out-of-the-money amount, capped at the greater of $5 × shares and 30% of the short's value (4210(f)(2)(H)(v)a).
    - Plain 150%/30% would apply only if the long were gone. Under DEC-20's recommended order the cover comes before any long exit, so it never is.
  - **Alternative:** keep 150%/30% as a conservative simplification, and reword the site's negative-funds statement. Otherwise the site would say a position couldn't have been held when the rules allow it.
  - Either way, Spec › NAV and Reg T changes in the commit that answers this.
- **Outcome:** 2026-09-29 — PO, asked at P3-04: **the hedged requirement**, as recommended. Spec › NAV and Reg T now has a row for it.
  - **While long calls covering the shares are held:** no initial requirement beyond the sale proceeds. Maintenance is 10% of the long calls' aggregate exercise price plus their out-of-the-money amount at the stock's mark, capped at the greater of $5 a share and 30% of the short stock's market value.
  - **Without such a long:** the spec's 150% initial (proceeds plus 50%) and 30% maintenance.
  - Built in `pmcc/accounting/regt.py` (P3-04, DEC-91). A requirement that isn't a whole $0.0001 is rounded up, never down.

### DEC-11 — Risk-free rate
**Status:** SETTLED · **Basis:** PO, 2026-09-28 · **Affects:** pricing, eligibility, Methodology, `configs/universe.yaml`

- The spec asks for the source and value of r to be chosen.
- **Recommendation:** use the 3-month US T-bill yield on the window's start date, as one continuously compounded constant.
  - **Source:** LSEG (`US3MT=RR`, RIC to be confirmed), cross-checked against FRED DTB3.
  - **Storage:** `configs/universe.yaml` with its source and date, and shown on the site.
- r changes eligibility: a deep ITM mid below `S − K·e^(−rT)` has no IV. Fix r before any run.
- **Outcome:** 2026-09-28 — PO, asked at P1-05: the 3-month Treasury yield from FRED at the last close before the window, continuously compounded.
  - **The quote:** DGS3MO (H.15's 3-month constant maturity, investment basis) was 3.73% on Fri Mar 27 2026, the last close before the window (DEC-07).
  - **The rate:** converted over a 91-day bill, r = ln(1 + 0.0373 × 91/365) × 365/91 = 0.037128, used and stated as **0.0371** (4 decimals).
  - **Why this, not the recommendation above:** at P1-05 the recommendation became FRED, not LSEG. It is public, so any reader can check r, and it needs no extra LSEG pull. The question also offered LSEG's `US3MT=RR` and a window-average yield, which isn't point-in-time. DTB3 (discount basis) gives 0.0369 for the same day.
  - **Point in time:** the quote was known before the first decision (Mon Mar 30, 10:00). The 3-month yield then rose to 4.24% by Sep 24 2026; the spec's single constant doesn't follow it, and Methodology states r with its date.
  - **Stored** in `configs/universe.yaml` (`risk_free_rate`), with the quote, series, date and source. The loader refuses a value that isn't the quote converted (DEC-86).

### DEC-12 — Per-symbol identifiers, splits, max strike
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (stock RICs); the P1-04 probes and the P1-05 split check · **Affects:** `configs/universe.yaml`, P1-02, P1-08

- **Confirm for each universe symbol:**
  - **Stock RIC with its exchange suffix.** LDG verified only `QQQ.O` and `UUUU.K`.
  - **Option root.**
  - **No split in the window,** since a split changes the root (LDG §3).
  - **Max strike needed ≤ $999.99,** the 5-digit strike field. If any symbol needs more, that's an `ASK`.
- **Outcome:** 2026-09-27 — probed on all 12 symbols (DEC-85):
  - **Stock RICs.** Each suffix was asked alone:
    - Nasdaq listings answer `.O`, and also the venue RICs `.N`, `.P`, `.A` and `.Z`.
    - The NYSE Arca ETFs (SPY, IWM, XLE) and JPM (NYSE) have no `.O`.
    - No symbol answers `.K`.
    - The venues' last closes differ: by cents for most, and by up to $0.94 across AMD's and $0.63 across META's.
  - **Recommendation for `configs/universe.yaml` (P1-05): each primary listing:** SPY.P, QQQ.O, IWM.P, AAPL.O, NVDA.O, AMD.O, META.O, TSLA.O, COIN.O, JPM.N, TLT.O, XLE.P. The probe used the first suffix that answered, so its SPY, IWM and XLE stock bars are the NYSE venue's (`.N`), not Arca's.
  - **Option roots** are the tickers: every symbol's weeklies and monthlies answered under its ticker.
  - **Splits: LSEG's daily history is split-adjusted**, so the probe's check (the largest daily moves, none of which looked like a split) can't see a split. **XLE split 2-for-1 on Dec 5 2025** (OCC Information Memo #57734; State Street's announcement of Nov 20 2025), and its daily bars show no jump. A web search found no split announced for the other 11 in 2025–2026, but that isn't proof. Confirm them against OCC memos at P1-05, and choose the window with XLE's split in mind (DEC-07).
  - **Max strike:** the top of the weekly call band over the last year (high + 2.5 EMest, DEC-48) fits the $999.99 field for all 12. META is closest ($973.51), then AMD ($922.78).
  - **Calendar:** every symbol's daily bars match `configs/calendar.yaml` from Jan 2 2025 to Sep 25 2026, including the unscheduled closure on Jan 9 2025 (DEC-33).
- **Outcome:** 2026-09-28 — PO, asked at P1-05: each symbol at its primary listing, as recommended. In `configs/universe.yaml`:

  | RIC | Symbols |
  | --- | --- |
  | Arca, `.P` | SPY, IWM, XLE |
  | Nasdaq, `.O` | QQQ, AAPL, NVDA, AMD, META, TSLA, COIN, TLT |
  | NYSE, `.N` | JPM |

  - Option roots are the tickers.
  - SPY.P, IWM.P and XLE.P answered daily bars, but their hourly fields weren't probed (DEC-13 used `.N`). Each unit's sidecar records the fields that came back (P1-07).
- **Outcome:** 2026-09-28 — splits and contract adjustments, checked at P1-05 for Aug 1 2025 to Sep 27 2026. Sources: OCC's series search for all 12 (read 2026-09-28), OCC memos, issuer filings and news.
  - **XLE's is the only event:** 2-for-1, ex Fri Dec 5 2025 (OCC #57734). The root stayed XLE, strikes were halved, contract counts doubled, and the deliverable stayed 100 shares. It falls before the window and its warm-up (DEC-07).
  - **Halved strikes.** Contracts listed before the split carry halved strikes. DEC-14's offsets read a halved $1 or $5 grid ($0.50 or $2.50) as it is, but would read a halved $0.50 grid ($0.25) as $0.50. In this window, only XLE monthlies listed before Dec 5 2025 can carry them.
  - **Nothing for the other 11,** and no split announced before Oct 9 2026.
    - The series search lists no adjusted root (like `COIN1`) and no reduced strike for any of them, so adjusted contracts are ruled out positively.
    - A whole-number split keeps its root, so "no split" rests on issuer documents and dated news, the latest from Sep 17 and Sep 23 2026.
    - COIN's reincorporation in Texas (Dec 15 2025, 1:1) and QQQ's conversion to an open-end fund (Dec 22 2025) changed no option contract.
  - **QQQ's Dec 18 2026 monthly,** a long candidate, also lists strikes reduced by $0.21584 (e.g. $599.78), left by a Dec 2023 special dividend (OCC #53847). The fetch's integer-cent ladders never ask them, so E-L3 never sees them; the standard strikes beside them are asked.
  - **Why it matters past the window.** LSEG's daily history is split-adjusted. If its hourly history is too, a split between the window's start and the fetch would restate the tape against unadjusted strikes. None is announced before Oct 9, and the universe fetch is planned to finish by Oct 3.

### DEC-13 — Hourly field availability
**Status:** SETTLED · **Basis:** Spec › Fields and bars, confirmed by the P1-04 probes on every symbol kept (DEC-15) · **Affects:** fetch field lists

- A field the RIC doesn't carry raises `LDError` for the whole request (LDG §4.6).
- **Probe:** each field from Spec › Fields and bars, paired with TRDPRC_1, on hourly option and stock RICs.
- **Fetch and records:**
  - The fetch requests only the fields that exist.
  - Dropped fields are recorded in each unit's sidecar and on the Methodology page.
  - The stock also needs BID/ASK, for the stock fills after X-S5.
- **Outcome:** 2026-09-27 — for all 12 symbols, hourly bars carry all 8 fields, on the options and on the stock (for SPY, IWM and XLE, on the NYSE venue's `.N`, not the Arca primary DEC-12 recommends, which wasn't field-probed), each asked paired with TRDPRC_1: BID, ASK, TRDPRC_1, OPEN_PRC, HIGH_1, LOW_1, ACVOL_UNS, NUM_MOVES. The fetch can ask for all of them; no field is dropped. LSEG doesn't refuse a field a RIC lacks, it leaves it out of the answer (DEC-83). So a unit's sidecar should record the fields asked and the fields that came back (P1-07).
- **Outcome:** 2026-09-28 — reported to the PO at P1-05. The PO then chose the Arca primaries for SPY, IWM and XLE (DEC-12), whose hourly fields weren't probed, so the entry stays VERIFY: it settles when the fetches of those three (P1-10; NVDA's at P1-09 is on the probed `.O`) show all 8 fields in their sidecars, stock BID/ASK included (the X-S5 stock fills need them). The adversarial review of P1-05 caught this entry first marked SETTLED on a probe basis, which the legend doesn't allow.
- **Outcome:** 2026-09-28 — the PO then cut the universe to QQQ, NVDA and TSLA (DEC-15). All three use `.O`, whose hourly fields the probes checked (all 8, options and stock), so nothing is left to verify: settled on the spec, as the probes confirmed it.

### DEC-14 — Strike increments
**Status:** ENG (method) · values probed at P1-04, reported to the PO at P1-05 · an unmeasured anchor SETTLED (PO, 2026-09-28) · **Affects:** P1-06, P1-08

- **Method:** per expiry and per region (near the money for weeklies, deep ITM for monthlies), probe one session with 5 strikes in a single batch.
  - The strikes are an anchor `A` (a multiple of $10 near the region's centre) plus `A+0.50`, `A+1`, `A+2.50` and `A+5`.
  - The smallest offset that answers is the increment. If none answers, the increment is $10.
- **Recording:** increments are recorded per expiry in the sidecar. They can differ by region, e.g. $1 near spot and $5 deep ITM on the same monthly (LDG §6.2).
- **Outcome:** 2026-09-27 — measured with the method above, on daily bars for one session per region (DEC-85). In cents:

  | Symbol | Next weekly, near money | Expired weekly, near money | Monthly (Mar 2027), near money | Monthly, deep ITM (0.8 × spot) |
  | --- | --- | --- | --- | --- |
  | SPY, QQQ, IWM | 100 | 100 | 500 | 500 |
  | AAPL | 250 | 250 | 1,000 | 1,000 |
  | NVDA, META, TSLA, JPM | 250 | 250 | 500 | 500 |
  | AMD | 250 | 250 | none answered | 1,000 |
  | COIN | 250 | 250 | 1,000 | 500 |
  | TLT | 50 | 50 | 100 | 500 |
  | XLE | 50 | 100 | 100 | 100 |

  - The increment differs by region and by expiry, as LDG §6.2 said, so the fetch measures it per unit and per band (DEC-84).
  - 1,000 means no offset answered but the anchor did: a $10 grid, or wider.
  - **AMD's near-money monthly answered no strike at all** around its $630 anchor, so its $10 is DEC-14's default, not a measurement. The fetch (P1-08) should treat an unanswered anchor as no measurement, record it in the sidecar, and not trust the default.
- **Outcome:** 2026-09-28 — PO, asked at P1-08: what the fetch does when a band's anchor doesn't answer. Offered: try the neighbouring anchors (recommended); take the probe report's step at once; stop the unit. The PO chose the neighbours:
  - Ask the anchors $10 below and $10 above, each with its four offsets, in one request. If either answers, take the finer step they show.
  - If none answers, the band takes the probe report's step for its symbol and region, and is flagged: `probe_report` in the unit's sidecar, a `fetch.increment.unmeasured` log event, and a line in the coverage summary (DEC-16).
  - Built in `pmcc/data/pull.py` (`measure_step`, DEC-88).
- **Outcome:** 2026-09-28 — NVDA's fetch (P1-09) measured 83 of its 86 bands. Near the money every band was $2.50 (53). Deep in the money the bands were $5 (24), $2.50 (3) and $1 (3). The 3 unmeasured bands are all on May 21 2027, which wasn't listed in the window (DEC-08), so they took the probe report's $5 as designed. The daily step asks' date edges (DEC-47) held on LSEG.

### DEC-15 — Universe size
**Status:** SETTLED · **Basis:** PO, 2026-09-28 · **Affects:** Spec › Universe, `configs/universe.yaml`, P1-10, P3-09, P5, P6 (pooled statistics), P7-05; the cut list

- **Question (raised by the PO after P1-05):** is the 12-symbol universe too big, for GitHub Pages or for the timeline?
- **The assessment given:**
  - **Pages:** not a limit. The site holds results JSON only, about 1 MB per symbol by estimate (~875 hourly ledger rows per full run); Pages allows 1 GB. The raw cache never leaves the machine (DEC-56).
  - **Timeline:** the code is the same for 1 symbol or 12, so each symbol costs fetch time (roughly 40 min, with Workspace signed in), a coverage review, and its own data quirks. The probes put 7 of the 12 long legs over E-T1's 3% spread (DEC-08), so several could come back with few or no trades. The build is also about a day behind.
  - Options offered: all 12; 3 (QQQ, NVDA, TSLA, recommended: the tightest long-leg spreads, and realized volatility of about 20%, 40% and 55%); 5 (adding META, AAPL); 1–2 (NVDA, perhaps QQQ).
- **Outcome:** 2026-09-28 — PO: "ok lets do qqq, nvda, tsla".
  - `configs/universe.yaml` lists QQQ.O, NVDA.O and TSLA.O (DEC-12's primary listings); Spec › Universe, its build order and its cut list are amended to cite this entry.
  - **What goes:** the diversifying drivers (financials, Treasuries, energy). SPY, IWM and XLE's unprobed `.P` RICs (DEC-13), XLE's halved strikes (DEC-12) and QQQ's dividend-reduced strikes remain facts about the probes; only QQQ's still reaches the fetch.
  - **What stays:** pooled statistics across three symbols (DEC-61), the Universe page and the suitability screen, now over three. The cut list's universe cut (#4) is taken early.
  - **Fetch:** roughly 2–2.5 h for the three over the 26-week window (ARCHITECTURE §6.3), before DEC-48's wider long bands.

### DEC-16 — Fetch coverage summary
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P1-08, and after its review; IV failures built at P2-04) · **Affects:** P1-08, P1-09, P1-10, P2-04, ARCHITECTURE §6.1

- **The gap:** ARCHITECTURE §6.1 step 5 asked the fetch to print "% session bars with a valid mid, unanswered counts, IV-failure counts". Two points were open:
  - **IV failures** need the IV solver (P2-02), which isn't built. Offered: count bars whose mid is below S − K·e^(−rT), the no-IV condition of DEC-08 and DEC-27, as a lower bound (recommended); leave them out until P2-02; build P2-02 first.
  - **The valid-mid denominator.** Offered: every session bar the calendar has over each answered contract's unit dates, so a bar that never came back counts as no mid (recommended); only the bars LSEG returned.
- **Outcome:** 2026-09-28 — PO:
  - **IV failures: left out for now.** The summary says so. HR-8's disclosure of IV failures on the Methodology page is unaffected, since it comes from the runs. They join the fetch summary with the chain pricer, whose done-when already asks for them (P2-04), not with the solver alone (P2-02), as this entry first said.
  - **Denominator: calendar session bars,** as recommended. A valid mid is BID > 0, ASK > 0 and ASK ≥ BID (ARCHITECTURE §6.5).
  - **Reported:** per kind (stock, weekly calls, monthly calls, weekly + monthly calls, puts) on screen, and per unit in the log (`fetch.coverage.unit`), with contracts requested, answered and unanswered. **Near-the-money weekly calls** get their own line: calls whose strike lies inside the unit's stock range, the near-money band before padding. That is P1-09's ≥ 90% measure.
  - **Flags:** bands whose step wasn't measured (DEC-14), units that answered nothing (DEC-83's residual risk), and fields that never came back (DEC-13).
  - Built in `pmcc/data/coverage.py`. It reads the cache through `load_symbol`, after the LSEG session has closed (DEC-88).
- **Outcome:** 2026-09-28 — PO, asked after P1-08's review: which dates the near-the-money line counts for a **merged unit**, a monthly Friday that is also a weekly expiry. In the PO's window the Aug 21 and Sep 18 2026 units run from Mar 30, their first long-candidate session, so their near-money strikes were counted over about five months, not the weekly's two weeks. Offered: the weekly part only (recommended); the whole unit, as built. The PO chose the **weekly part only**: from the prior week's first session to the expiry (or the window's end), the dates a weekly unit covers. The per-kind table still counts the whole unit. `weekly_dates` in `pmcc/data/discovery.py` gives those dates to both the planner and the summary.
- **Outcome:** 2026-09-28 — **IV failures joined the summary at P2-04**, as settled above. `coverage()` prices the cache with the chain pricer at the universe's r (DEC-11) and prints one line: the share of session contract-bars with a valid quote, before the expiry close, whose IV failed, with the count by reason (below the floor, above the cap, no convergence, no spot). Each unit's log line carries `iv_priced` and `iv_failed`. A bar with no valid quote is the valid-mid line's, not an IV failure, and the expiry session's close bar isn't priced (DEC-89). NVDA: 8.3%, 32,403 of 390,652 (31,966 below the floor, 437 no convergence).

## C. Rule interpretations

Each of these decides trading behaviour the spec leaves open, so each goes to the PO.

### DEC-20 — Week-open session and order of operations
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-07, with P3-02 to P3-06) · **Affects:** P3-07, every rule

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
- **Outcome:** 2026-09-29 — PO: as recommended, both parts. Built in `pmcc/engine/loop.py` (P3-07, DEC-91). The spec is unchanged: this settles what it leaves open. When the long is checked within the week-open session is DEC-28's.

### DEC-21 — Selection freeze and E-T1
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-07) · **Affects:** G-1, P3-07

- **Recommendation (short):** on the week-open session, the first bar where the short selector returns a contract freezes that contract for the rest of the session.
  - E-T1 is checked on that bar and on each later bar; the first pass is the **decision bar**.
  - If no bar passes, G-1 fires.
  - The engine never re-selects or substitutes a strike (Spec › Trade rules: entry).
- **Recommendation (long):** the same freeze applies within a session. If E-T1 never passes, E-L1 retries the next session with a fresh selection.
- **Eligibility:** selectors consider only contracts that are eligible on that bar (valid quote and a successful IV solve).
- **Outcome:** 2026-09-29 — PO: as recommended. Built in `pmcc/engine/legs.py` (P3-07, DEC-91). The spec is unchanged: this settles what it leaves open.

### DEC-22 — Gates and the gate log
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-07) · **Affects:** P4-02, INV-09

- **Recommendation (evaluation):**
  - G-2–G-5 are evaluated at the decision bar. Every gate the strategy has is evaluated and recorded (pass or fire, with values).
  - The outcome is the first gate, in spec order, that fired.
  - If G-1 fires, the other gates are `not_evaluated`.
- **Recommendation (missing inputs):** a gate whose inputs are unavailable (e.g. the next-week ATM call has no quote) records `n/a`. It does not fire, and its reason is logged.
- **Recommendation (rows):** one gate-log row per strategy per week-open session.
  - A week with no long held logs outcome `E-S1`.
  - A week blocked by an unfinished long reset logs `X-L1` or `X-L2`.
- **Outcome:** 2026-09-29 — PO: as recommended. Built in `pmcc/engine/legs.py` and `pmcc/strategy/gates.py` (P3-06, P3-07, DEC-91). A week whose long couldn't be checked logs `E-S1` too (DEC-28's outcome). The spec is unchanged: this settles what it leaves open.

### DEC-23 — Spot, close, ITM at expiry
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P2-03) · **Affects:** P2-03, P3-02, P3-06, X-S4, X-S5

- **Recommendation:**
  - **Spot** at a decision bar is the underlying's TRDPRC_1 (last trade) in that bar.
  - **Closing spot** is the spot of the session's close bar (16:00 ET, or 13:00 on a half-day).
  - **ITM at expiry (X-S4/X-S5):** the short is ITM if and only if closing spot > strike. OCC auto-exercises at $0.01 ITM, so equal counts as OTM.
- **Outcome:** 2026-09-28 — PO: as recommended. The P1-04 evidence went with the question: the close bar's last trade matched the official closing auction in 9 of 48 sessions and sat up to 0.09% from it (JPM), with the largest dollar gaps on META ($0.40) and TSLA ($0.27) (DEC-06, R-21). The close bar's last trade is kept, since the cache holds only the hourly tape; the gap is for the Methodology page.
  - Built in `pmcc/pricing/measures.py`: `session_close` (the close bar's TRDPRC_1, keyed by `bar_end`) and `itm_at_expiry` (DEC-89). Spot itself is MarketView's accessor (P3-02), and the chain pricer reads it the same way. The spec is unchanged: this settles what it leaves open.
- **Outcome:** 2026-09-29 — PO, asked while building P3-07, two inputs the spec leaves open. Both taken as recommended:
  - **The stock's mark** (StockMV, only after X-S5) is its BID/ASK mid, like an option's. Without a valid quote, the last valid mid is carried and flagged stale (`stale_stock`).
  - **The closing spot when the close bar has no trade** (X-S4/X-S5) is the last TRDPRC_1 on a session bar at or before the close bar in that session. With no trade in the whole session, the run stops with an `EngineError` rather than guess. NVDA trades on every session bar (P2-04), so it doesn't arise there.
  - Built in `pmcc/engine/legs.py` (the stock's first mark), `pmcc/accounting/marks.py` (carrying it stale) and `pmcc/engine/loop.py` (`closing_spot`) (P3-07, DEC-91). The spec is unchanged: this settles what it leaves open.

### DEC-24 — Time to expiry and Greek units
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P2-01) · **Affects:** P2-01, P2-04, E-L2, X-L2, P6-04

- **Recommendation:**
  - **T:** calendar time from the decision time to the expiry session's close (16:00 ET, or 13:00 on a half-day), in years, ACT/365 (seconds ÷ 31,536,000).
  - **Units:** δ per $1; Γ per $1²; θ per year (Δt in years); ν per 1.00 of volatility (Δσ in vol units). Attribution uses the same units.
  - **DTE (E-L2, X-L2):** calendar days from the decision date to the expiry date.
- **Outcome:** 2026-09-28 — PO: as recommended. Built in `pmcc/pricing/expiry.py` (`years_to_expiry`, `days_to_expiry`) and `pmcc/pricing/black_scholes.py` (DEC-89). T is elapsed time, measured in UTC, so a clock change between the decision and the expiry counts its hour; the first version subtracted two ET times, which Python does by wall clock, and a test across the Nov 1 2026 change caught it. The decision date for DTE is the ET date. The spec is unchanged: this settles what it leaves open.

### DEC-25 — ATM strike, ATM IV, expected move
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P2-03) · **Affects:** P2-03, E-S3 (quant), G-3, G-4, X-S3

- **Recommendation:**
  - **ATM strike:** the listed strike nearest spot (tie → the lower strike).
  - **ATM IV (G-3, G-4):** the IV of the ATM **call**. Under the spec's q = 0 assumption, an American call is priced exactly by Black-Scholes, so calls avoid the early-exercise bias that puts carry.
  - **EM:** ATM call mid + ATM put mid for the front week, at the decision bar. Both quotes must be valid. Otherwise EM is unavailable, and quant E-S3 can't select on that bar.
- **Outcome:** 2026-09-28 — PO: as recommended. Built in `pmcc/pricing/measures.py` (`atm_strike`, `atm_iv`, `expected_move`; DEC-89).
  - Distances to spot are compared in $0.0001 units, so a tie is exact.
  - Each mid is `Quote.mid`, rounded half-even to $0.0001 as a fill at mid would be (DEC-44), so EM is a `Price`.
  - ATM IV is unavailable when the ATM call has no row on the bar or its IV fails. Which strikes are listed is MarketView's (DEC-32, P3-02). The spec is unchanged: this settles what it leaves open.

### DEC-26 — RV20
**Status:** SETTLED, except a missing close (ASK, 2026-09-29) · **Basis:** PO, 2026-09-28 (asked at P2-03) · **Affects:** P2-03, G-4

- **Recommendation:** RV20 at a decision bar is the sample standard deviation of the last 20 daily log returns × √252. The returns come from the 21 most recent completed session closes before the current session. A session close is the TRDPRC_1 of the close bar.
- **Fetch:** the fetch already pulls 30 warm-up sessions (DEC-48), which covers any reasonable answer.
- **Outcome:** 2026-09-28 — PO: as recommended. Built in `pmcc/pricing/measures.py` (`rv20`, `realized_vol`; DEC-89). The 21 sessions come from the calendar (`sessions_before`), so the current session's bars never count, even at its close; a half-day's close is its 13:00 bar. The spec is unchanged: this settles what it leaves open.
- **Not asked, so not settled:** what RV20 is when one of the 21 closes is missing (the close bar has no trade). The code makes RV20 unavailable rather than compute it from fewer closes, so G-4 can't evaluate for the next 21 sessions. That changes when a gate evaluates, so it goes to the PO; the P2 review found it recorded above as the PO's answer. **Asked 2026-09-29, answer pending.** NVDA's stock has a trade on every session bar (P2-04), so it doesn't arise there.

### DEC-27 — Greeks for held contracts; fresh quotes only
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P2-04) · **Affects:** P2-04, P3-02, P3-07, X-S2, X-L1

- **Selection:** an IV failure makes a contract ineligible (spec).
- **Recommendation (held contracts):** if the mid is below the no-arbitrage floor, `mid < max(0, S − K·e^(−rT))`, the contract gets δ := 1.0 (the σ → 0 limit for an ITM call), Γ = ν := 0, θ := −r·K·e^(−rT). X-S2 and X-L1 therefore still see a deep ITM leg.
- **Recommendation (fresh quotes only):** rules evaluate only on bars where the contract has a fresh valid quote. Stale carried marks value the book, but they never trigger a rule or a fill.
- **Outcome:** 2026-09-28 — PO: as recommended.
  - **Built** in `pmcc/pricing/chain.py` (DEC-89): a call below its floor gets the limit Greeks and stays ineligible. The limit is a call's, and only calls are ever held, so a put below its floor gets no Greeks. Every other failure (above the cap, no convergence, no spot) leaves the Greeks unknown.
  - **Fresh quotes only** is MarketView's and the engine's (P3-02, P3-07). The pricer prices only the rows a bar has, and a bar without a valid quote is `NO_QUOTE`, so it never supplies Greeks from a stale mark.
  - **Measured on NVDA (P2-04):** 31,966 of 390,652 quoted session contract-bars before expiry are below the floor, 8.2%. They are very deep in the money: 83% have K/S ≤ 0.6, and at 120–270 DTE all but 16 of 13,084 do (the 16, on 11 contracts, reach K/S 0.66), far below the 0.70–0.90 delta band, where 51,889 contract-bars are eligible. Nearer the money they come from contracts close to their own expiry. A long held while NVDA rallies can reach them, which is the case this rule covers.
  - **Open for P3:** a held call whose IV fails another way has no delta on that bar, and P3-06/P3-07 must say what X-S2 and X-L1 do then:
    - **no convergence:** on NVDA, 437 contract-bars, all deep ITM calls within a week of their expiry (297 on expiry day, 140 one to seven days before);
    - **no spot:** never on NVDA;
    - **the expiry session's close bar:** T = 0, so every contract there is `EXPIRED` and a held short has no delta on the bar where DEC-20 still runs short exits before X-S4/X-S5. This happens to every short, every week (found by the P2 review).
  - The spec is unchanged: this settles what it leaves open.
- **Outcome:** 2026-09-29 — PO, asked at P3-06/P3-07, the open item above: **a rule that needs a delta the bar doesn't have doesn't fire, and it is logged** (`engine.exit.unevaluated`, with the rule, the contract and the IV code). So X-S2 doesn't fire on a short with no delta; X-S3 still checks it at the Friday check, and on the expiry close bar X-S4/X-S5 decide. X-L1 doesn't fire on a long with no delta; X-L2 still checks its DTE. The alternative, reading a missing delta as 1 when the contract is in the money, was declined. Built in `pmcc/strategy/exits.py` (DEC-91).

### DEC-28 — Exits without a valid quote
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-07) · **Affects:** X-S3, X-S5, X-L1, X-L2, P3-07

- **X-S1, X-S2:** their conditions need a fresh quote, so a trigger can always fill.
- **Recommendation (X-S3):** if it triggers on the check bar with no valid quote, the close fills at the first later bar of that session that has one. The row is still ruled `X-S3`, noted "delayed fill". If there is none before the close, X-S4/X-S5 resolve the short at the close.
- **Recommendation (X-L1/X-L2):** the sale fills at the first bar of the week-open session with a valid long quote. Short entry waits for the reset and re-entry to complete.
  - If the reset doesn't complete in session, there is no short that week (gate log `X-L1`/`X-L2`).
  - The pending reset carries to the next session.
- **Recommendation (X-S5 cover):** fills at the first bar of the next session with a valid stock BID/ASK.
- **Outcome:** 2026-09-29 — PO: as recommended.
- **Outcome:** 2026-09-29 — PO, asked while building P3-07: **when the long is checked.** DEC-27 lets a rule run only on a fresh quote, so X-L1 and X-L2 can't be checked on a bar where the long has none. Recommended and taken:
  - X-L1 and X-L2 are checked once a week, at the first bar of the week-open session where the long has a fresh quote, and a sale fills on that bar. So the sale never waits for a quote; "a reset that doesn't complete" is a re-entry that doesn't pass E-T1 in the session, which E-L1 retries next session.
  - Short entry waits until that check has passed, since a reset later in the session would leave the short uncovered.
  - If the long has no fresh quote on any bar of the week-open session, it isn't checked that week and no short is sold. The gate log's outcome is `E-S1`, noted "long not checked: no fresh long quote".
  - Built in `pmcc/engine/legs.py` (DEC-91). The spec is unchanged: this settles what it leaves open.

### DEC-29 — Tie-breaks
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-06) · **Affects:** P3-06, P4-01

| Rule | Recommended tie-break order |
| --- | --- |
| E-L2 baseline (nearest 180 DTE) | later expiry |
| E-L3 baseline (delta nearest 0.80) | lower spread %, then lower strike |
| E-L3 quant (lowest extrinsic ÷ delta) | lower spread % (spec), then earlier expiry, then lower strike |
| E-S3 baseline (delta nearest 0.30) | lower spread %, then higher strike |
| ATM strike | lower strike |

Distances are compared in integer price units, so float noise can't create or break a tie.

**Outcome:** 2026-09-29 — PO: as recommended, the quant row included (built at P4-01). Built in `pmcc/strategy/selectors.py` (P3-06, DEC-91): DTE is whole days and strikes are integer units, so those ties are exact; spread % is compared as an exact fraction of the integer BID and ASK. A delta is a float from the IV solve, so its distance to the target is rounded to 9 decimal places before comparing: without that, 0.85 and 0.75 aren't equally far from 0.80 in binary floating point, and float noise would break the tie the PO settled (a unit test caught it). The spec is unchanged: this settles what it leaves open.

### DEC-30 — Starting capital (E-L4)
**Status:** ASK · **Ask at:** P3-09 · **Affects:** P5-01

- **Recommendation:**
  - `pmcc calibrate` runs every universe symbol under `baseline_pmcc` and `quant_pmcc` at `spread_capture` 0, with provisional cash.
  - It records each run's first long-leg entry cost: fill × 100 × qty + fees.
  - It sets `starting_cash = ceil(2 × max ÷ 5,000) × 5,000`.
  - The value is written to `configs/universe.yaml` with its basis (symbol, strategy, cost) and committed before the first published run. Every strategy, ablation and sensitivity run uses it unchanged.
  - P3 uses a provisional value from the symbols cached so far, labelled provisional.
- **Outcome:** 2026-09-30 — partly answered, at P3-08 (the calibration itself is still asked at P3-09). PO: `pmcc run` reads the starting cash only from `configs/universe.yaml`, with no CLI override, so no published run can use another figure. Until P3-09 writes the value, `pmcc run` stops with a message naming P3-09. `Universe.starting_cash` is optional until then (DEC-92).

### DEC-31 — Entry-timing sensitivity
**Status:** ASK · **Ask at:** P5-02

- **Recommendation for variant `t{k}`, k = 1…7 (the session bars of the week-open session):**
  - The short's decision bar is fixed at bar k.
  - At bar k the selector runs, and the selected contract must have a valid quote and pass the E-T1 spread threshold. Otherwise G-1 fires.
  - Other bars are never scanned.
- **Everything else is unchanged,** including long entry. The fixed-bar trigger replaces E-T1 under the same rule ID.
- **Ready for it (P3-07, DEC-91):** E-T1 is a port, `EntryTrigger`, with `can_decide(view, leg)` and `check(view, option, leg)`. The loop selects and freezes a contract only on a bar the trigger `can_decide`, so a fixed-bar trigger selects at bar k, as recommended, with no change to the loop.
- **Outcome:** —

### DEC-32 — Point-in-time listing
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-01 for P3-02) · **Affects:** E-S3 (quant), ATM strike, P3-02

- **Recommendation:**
  - A contract is "listed" at time t once it has had a valid quote at or before t.
  - Chain snapshots, "lowest listed strike" and the ATM strike use only listed contracts.
  - The fetch band can include strikes that are listed later, and MarketView hides them until their first quote.
- **Evidence (P1-09, 2026-09-28):** NVDA's cache shows listing happening inside the window. Whole long-dated expiries appear late: Feb 2027 from Jun 30, Apr 2027 from Sep 11, and May 2027 not by Sep 25, although each is 120–270 DTE earlier. New strikes also appear on the near monthlies as the stock moves. Before its first bar, a contract has no rows at all in the cache (DEC-08).
- **Outcome:** 2026-09-29 — PO, asked early while P3-01 was built: as recommended. The PO first wrote "contracts take the mid", then, asked to clarify, chose "listed once it has had a mid" over "listed only on bars with a mid". So a contract is listed at t once it has had a valid BID/ASK on any session bar at or before t, and it stays listed. Built in `pmcc/engine/market_view.py` (P3-02, DEC-91): chain snapshots and the listed expiries show only listed contracts. The spec is unchanged: this settles what it leaves open.

### DEC-33 — Expiry calendar
**Status:** SETTLED · **Basis:** PO, 2026-09-27 · **Affects:** P1-06, P1-07, P1-08, P3-02, E-L2, E-S1, E-S2

- **Weekly expiries:** the last trading session of each week, from the stock tape (spec).
- **Recommendation (monthly):** the third Friday, or the prior session if that Friday is an NYSE holiday. Holidays come from `configs/calendar.yaml` (NYSE holidays and early closes for 2026–2027, with the source cited). Holidays derived from the tape must match the table (a P1-06 check).
- **Recommendation (reference data):** the calendar is published in advance, so MarketView exposes it without the as-of restriction.
- **Known cases:**
  - Fri Jul 3 2026 is closed, so that week expires Thu Jul 2.
  - Mon Sep 7 2026 (Labor Day) moves week-open to Tue Sep 8.
  - Fri Jun 19 2026 is closed, so that week expires Thu Jun 18.
  - Juneteenth 2027 is observed Fri Jun 18, so the June 2027 monthly expires Thu Jun 17 (verify).
- **Outcome:** 2026-09-27 — PO, asked at P1-06, took every recommendation:
  1. **Monthlies** expire on the third Friday, or on the session before it when that Friday is an NYSE holiday. **Weeklies** expire on each calendar week's final session (Spec).
  2. **The table covers 2025–2027**, widened from 2026–2027 in case the probed window starts in 2025. It lists NYSE full closures and 13:00 early closes, cited to nyse.com and NYSE Group's calendar releases. It includes the unscheduled closure on Thu Jan 9 2025 (National Day of Mourning for President Carter). Checked on nyse.com on 2026-09-27: Juneteenth 2027 is observed Fri Jun 18, so the June 2027 monthly expires Thu Jun 17; Jul 3 2026 is closed, and Jul 2 2026 is a full day.
  3. **The tape must match the table.** A day with regular-hours bars that the table closes, or a table session with no bars, raises `CalendarMismatchError` naming the days. The table is then fixed, with a source, or the data gap is investigated; nothing is patched quietly.
  4. **MarketView exposes the calendar** as reference data, without the as-of gate.
- **Outcome:** 2026-09-27 — implemented in P1-06 (DEC-84). All four known cases pass (`tests/unit/config/test_calendar_file.py`). The P1-04 probes then checked the table against each symbol's LSEG daily bars, Jan 2 2025 to Sep 25 2026 (DEC-85): see DEC-12's outcome.

### DEC-34 — Rule stamping for multi-rule events
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-07) · **Affects:** INV-09, P3-07

| Event | Blotter rows | Recommended rule |
| --- | --- | --- |
| Long entry | `BUY` | `E-L1`; notes carry the E-L2/E-L3 selection values and the E-T1 spread |
| Short entry | `SELL` | `E-S1`; notes carry the E-S3 strike logic, the E-T1 spread and the E-S5 terms |
| Short exit | `BUY` | the exit rule (`X-S1`, `X-S2`, `X-S3`) |
| Long reset / roll | `SELL`, then re-entry `BUY` | `X-L1`/`X-L2`; the re-entry is `E-L1`, noted "re-entry after X-L1" |
| OTM expiry | `EXPIRE` at $0 | `X-S4` |
| Missed assignment | `ASSIGN` + stock `SELL` at the strike, then the next session's stock `BUY` | `X-S5` on all three |
| End of backtest | no rows; final ledger marks | `X-E1` |

**Outcome:** 2026-09-29 — PO: as recommended. Built in `pmcc/engine/legs.py` (P3-07, DEC-91). An entry row's notes and audit carry the selection's values from the bar it froze on (with `selected_at`), the E-T1 spread on the decision bar (`e_t1_spread`), and for the short the E-S5 terms (`strike_gap`, `net_debit`). The freeze bar's own mid and spread are left out, since the row's Limit and the E-T1 spread replace them. The adversarial review found the first version left them out (DEC-91). The spec is unchanged: this settles what it leaves open.

### DEC-35 — Rule write-up: names and rationales
**Status:** SETTLED · **Basis:** PO, 2026-09-29 (asked at P3-01) · **Affects:** P3-01, P4-03, P7-03 (Trade rules page)

Every rule in the YAML carries a `rationale` (Spec › Rule write-up source), but the spec explains only some of them: E-S5, G-1, G-3, and the three "why" paragraphs under the exits. BUILD-PLAN put those paragraphs into "the X-S3, X-S5 and no-roll rationales", and no rule is named for rolls.

- **Asked:** which rules carry the spec's "Why there are no rolls" paragraph, and what the other rules' rationales say.
- **Outcome:** 2026-09-29 — PO:
  - **Rationales come from the spec,** in the PO's plain-language summary of its entry, skip-week and exit tables. Both strategies use the same entry timing and exits and differ only in selection and skips, so any difference in results comes from selection, not trade management. No PO decision so far changes these rules.
  - **The no-roll paragraph goes on all five short exits, X-S1 to X-S5,** word for word as their first paragraph. The PO's summary heads the short-call exits with "there are no rolls, and the plan is never to get assigned", and that line opens the paragraph. X-S3 then carries the Friday-buffer paragraph and X-S5 the never-exercised one.
- **Built** in `configs/_shared.yaml` and `configs/baseline_pmcc.yaml` (P3-01):
  - Names follow the spec's tables. X-S4, unnamed there, is "Expires out of the money", as in the PO's summary.
  - Rationales state only what the spec does, in the PO's wording where the summary has it.
  - A threshold in a rationale is a placeholder, like one in a condition, so it can't drift from the param (DEC-52).
  - A test holds the five no-roll paragraphs identical.
  - The spec is unchanged: this settles what it leaves open.
- **Outcome:** 2026-09-29 — the adversarial review of P3-01 (DEC-90) found the text not yet as settled. Fixed, with tests:
  - **E-S2 was wrong:** "a holiday week expires on Thursday". Only a week whose Friday is closed does; the Memorial Day and Labor Day weeks lose their Monday and still expire on Friday. It now reads "a holiday week never gets an invented Friday expiry: when the Friday is a holiday, it expires on Thursday".
  - **Claims the spec doesn't make are gone:** E-T1 (a tight spread making mid "a realistic fill"), E-L1 ("invested from the start", "rather than paying a wide spread"), E-L3 ("a fraction of the price of 100 shares"), E-L4 ("keeps results comparable"), X-S1 ("most of the premium is already earned"), X-L1 ("no longer does that well") and X-E1 ("no trade the rules didn't call for"). Each now says what the spec or the PO's summary says.
  - **Wording follows the spec's tables exactly** where they have it: every rule's name, G-1's and G-2's conditions, and every exit's action (X-S5, X-L1 and X-L2 had been reworded). Tests read these from the spec file and compare, and another reads the spec's no-roll paragraph from it and checks all five short exits open with it word for word.

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
**Status:** SETTLED · **Basis:** PO, 2026-09-28 (asked at P1-07) · **Affects:** P1-07, P1-08, P3-08, Spec › Cache

- The spec says "parquet per instrument". The recommendation stores one parquet per underlying (`{SYM}/stock.parquet`) and one per option chain unit (`{SYM}/chains/{expiry}_{C|P}.parquet`). The chain unit is the fetch unit and is written atomically.
- A per-RIC manifest (`{SYM}/manifest.json`) keeps the spec's fields (RIC, fetch time, row count, hash) and adds the form, status, and first and last bar.
- Each unit has a sidecar per LDG §5.
- **Data-manifest hash:** the one in a run manifest is the sha256 of the symbol's manifest content, excluding fetch times. Re-fetching identical data doesn't change it, and fetching another symbol never does.
- **Outcome:** 2026-09-28 — PO, asked at P1-07 as three questions; each recommendation was taken:
  - **Layout: per fetch unit.** One parquet for the stock tape and one per expiry and right, each with its sidecar; not one per RIC. Spec › Cache now says "per fetch unit", citing this entry.
  - **The hash ignores the RIC form.** An expired contract can answer under the caret form on one pull date and the live form on another (DEC-45), with identical bars. The hash covers each contract's identity (its OCC symbol, or the stock's RIC), unit, status, row count, first and last bar, and a sha256 of its bars (the RIC left out). It leaves out the RIC spelling, the form and the fetch time, which the manifest and sidecar still record. This was the point DEC-82's review raised for this entry.
  - **Re-pull: move the unit's two files.** The parquet and sidecar are the record. `manifest.json` is rebuilt from the sidecars after every write, so moving a unit's two files aside (e.g. into `{SYM}/superseded/`) makes the next fetch pull it again. Code never edits or deletes an old file.
- **Outcome:** 2026-09-28 — built in P1-07 (`pmcc/data/cache.py`, `pmcc/data/load.py`, `pmcc/data/files.py`); the engineering choices are in DEC-87. One of them departs from the recommendation's wording:
  - **Manifest entries are per contract, not per RIC.** LDG §5 counts answered + unanswered = requested per contract, and one contract can be asked under both forms. So each entry is a contract asked, and it keeps the RIC that answered. The RICs asked for an unanswered contract, with each one's reason, are in the sidecar. It is an ENG choice, so the PO can overrule it.

### DEC-47 — Fetch dates are inclusive
**Status:** ENG

- `pmcc fetch --start/--end` take inclusive dates, as the spec's example implies.
- The fetch passes `end + 1 day`, because LSEG's end is effectively exclusive (LDG §2).
- **Outcome:** 2026-09-26 — the provider port takes an exclusive end (`end_exclusive`, DEC-83) and passes it to LSEG unchanged, so the day is added by `pmcc fetch` (P1-08), not by the adapter as this entry first said.
- **Outcome:** 2026-09-27 — how LSEG reads the dates, from the P1-04 probes on 11 symbols (DEC-85):
  - **Hourly bars behave as `[start, end)` over whole days, as assumed.** On every symbol, a one-session window returned that session and a week returned its five. In late September every bar from 04:00 to 19:00 ET falls on the same UTC date as its ET date, so this can't tell whether LSEG cuts days at ET or UTC midnight; either way no session bar is cut. The fetch is hourly, so this entry holds.
  - **Daily bars don't, and the edges depend on the request.**
    - For one RIC, a daily window behaved as `(start, end]`: [Mon Sep 21, Tue Sep 22) returned Tuesday's bar, [Fri Sep 25, Sat Sep 26) returned nothing, and the week returned Tuesday to Friday.
    - A daily batch of 5 option RICs returned both edge days: [Sep 14, Sep 15) gave Sep 14 and Sep 15.
  - Nothing in the backtest reads daily bars. Anything that does (the probes, or a daily increment check in P1-08) shouldn't rely on a daily request's first or last day: ask a day wider on each side and filter by date.

### DEC-48 — Fetch plan and band-edge guard
**Status:** ENG · **Affects:** P1-06, P5-05

- **Plan:** units and bands follow ARCHITECTURE §6.3.
  - The stock tape gets a 30-session warm-up.
  - Each weekly call band starts at the **prior** week-open session, so G-3 has next-week IV.
  - Each week gets an ATM put band on its week-open session, for EM.
  - Monthly long-candidate bands cover the whole window.
- **Bands:** built from regular-session highs and lows, padded; they err wide (LDG §4.10).
- **Band-edge guard:** if a selection lands on the top or bottom strike fetched, the run flags it and the unit is re-fetched wider.
- **Outcome:** 2026-09-27 — the plan is built in P1-06 (`plan_symbol` in `pmcc/data/discovery.py`, DEC-84). Two changes to ARCHITECTURE §6.3, both of which only widen what is fetched:
  - A monthly is a long candidate on **any** session of the window, not only on week-open sessions, since E-L1 retries daily and X-L1/X-L2 re-enter. Its unit runs from the first session it is a candidate on to its expiry or the window's end, whichever comes first. §6.3 said window start to window end, which can't hold for a monthly expiring inside a long window.
  - The weekly after the window (G-3's next week) is fetched only up to the window's end.
- **Outcome:** 2026-09-27 — after the adversarial review of P1-04 and P1-06 (DEC-84):
  - **The long band's top is now the week's high, at the money.** The old top, weekHigh·e^(−0.3σ̂√T), sat near δ 0.72–0.77 on the probed volatilities, not the ≈0.65 claimed, because a bigger σ̂ moves a delta-based edge deeper, and the e^(σ²T/2) term was left out. So strikes near δ 0.70, quant E-L3's edge, weren't fetched. A strike at δ 0.70 is below spot for any σ and T, so an at-the-money top always holds it.
  - **The long band is split into 3 bands of equal price ratio,** each with its own increment probe (DEC-14). One increment at the band's centre took the deep grid ($5) and would miss finer strikes near the money.
  - **Every week with a session in the window gets its weekly calls and its week-open put,** even when the window ends mid-week; the next weekly follows the last one. Before, a window ending before its last week's final session got no put for that week-open and no next weekly.
  - The band-edge guard stays with P5-05.

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
- **Outcome:** 2026-09-27 — the P1-04 probes found that LSEG doesn't refuse a field a RIC doesn't carry: it leaves the field out of the answer (DEC-83). So the "Unanswered contract" row's "a field it doesn't carry" never produces a no-data code. Such a field comes back with no values; the RIC answers with its other fields.

### DEC-50 — Canonical results and INV-13
**Status:** SETTLED · **Basis:** PO, 2026-09-30 (asked at P3-08) · **Affects:** P3-08, P4-05, P8-01, Spec › Run manifest, INV-13

- **Conflict inside the spec:** INV-13 demands byte-identical results on re-run, but the run manifest also carries a run timestamp.
- **Recommendation:**
  - Results are written as canonical JSON: sorted keys, fixed rounding per value type, UTF-8, `\n` line endings.
  - INV-13 compares whole files after removing `manifest.run_timestamp`, the only volatile field.
  - Each run records `git_sha` and `git_dirty` (the dirty check ignores `results/`). `pmcc verify` rejects committed results with `git_dirty: true`, so every published number traces to a commit. Consequence: commit the code before a publishable run.
- **Outcome:** 2026-09-30 — PO, asked at P3-08: as recommended, with two follow-ups also as recommended:
  - **A dirty tree runs.** `pmcc run` doesn't refuse a dirty tree: it records `git_dirty: true` and says to commit before a publishable run. `pmcc verify` rejects dirty results (P4-05).
  - **What counts as dirty:** a tracked file modified, staged or deleted, or an untracked file git doesn't ignore, anywhere but `results/`. An untracked config or module can change a run, so it counts; a run's own results don't.
  - **Starting cash** (asked with it, recorded under DEC-30): `pmcc run` reads it only from `configs/universe.yaml`, with no CLI override.
  - The spec's Run manifest paragraph and invariant 13 now say this. Built in P3-08 (DEC-92): `pmcc/export/canonical.py`, `manifest.py`, and INV-13's test, which runs the same config twice in two fresh processes with different hash seeds and compares the files once the timestamp is dropped.

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
- **Outcome:** 2026-09-29 — built in P3-01 (`pmcc/config/rule_text.py`, DEC-90). The loader enforces both checks, and the tests run them on the shipped files. `rationale` is a template too, so a threshold it quotes can't drift either (DEC-35).

### DEC-53 — Composition over flags
**Status:** ENG

- A strategy is a set of ordered rule lists, built from YAML by `kind` through a registry.
- "Off" means absent from the list, never a boolean passed into rule logic (EP › Low coupling).
- Variants use `extends` plus `overrides` keyed by rule ID (`params` patch, `replace`, or `remove`).
- Rules shared by both strategies live once, in `configs/_shared.yaml`.
- **Outcome:** 2026-09-29 — built in P3-01 (`pmcc/config/kinds.py`, `extends.py`, `strategy.py`; DEC-90). A kind names the one rule ID it implements, and the rules a variant may remove are G-3, G-4, G-5 and X-S1; every other spec rule is required.

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
- **Outcome:** 2026-09-28 — PO: all of P2 (P2-01 to P2-04) is built in one pass and goes in as **one commit**, not one per item as CLAUDE.md's backlog rule says. The PO will give the reason later. The four items are still ticked separately in BUILD-PLAN. This applies to P2 only.

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
- **Outcome:** 2026-09-27 (P1-06) — both hypothesis profiles now run with `deadline=None`. Under a full-suite run on Windows, one example of a P1-03 property test (a whole fetch through pandas frames) took 404 ms, against hypothesis's 200 ms default, so the test failed at random. A wall-clock limit makes a pass depend on machine load, which TEST-STRATEGY §1 rules out.

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
**Status:** ENG · error codes verified at P1-04 (see the last outcome) · **Affects:** P1-03, P1-04, P1-07, P1-08, DEC-47, DEC-49

- **Where things live.** ARCHITECTURE §3.3 rule 2 lets only `fetch` and `cli` import the adapter, so the parts that don't talk to LSEG sit outside it:
  - **`pmcc/data/provider.py`:** the `HistoryProvider` port, `RawHistory`, `Interval` and the four failure classes. There is no LSEG code here, so `fetch` can catch the failures without importing the adapter.
  - **`pmcc/data/lseg/`:** `api.py` (`LsegApi`, the slice of `lseg.data` that is called), `session.py` (`lseg_session`), `shapes.py` (`to_long`) and `provider.py` (`LsegProvider`).
  - **`pmcc/data/fetch.py`:** batches, verdicts, retries, the caret→live fallback and diagnostics (`fetch_rics`, `fetch_contracts`). None of it depends on LSEG, so it goes in `fetch.py` (ARCHITECTURE §3.1) rather than under `lseg/`, where the P1-03 item first put it. P1-08 adds unit orchestration and resume to the same module. (It couldn't: `cache` imports `fetch`, so the loop is in `pull.py`; DEC-87, DEC-88.)
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
- **Outcome:** 2026-09-27 — verified by the P1-04 probes on all 12 symbols (DEC-85). Every symbol answered the same way:
  - **A never-listed RIC is no data, hourly and daily, in both forms.**
    - Hourly: `TS.Intraday.UserRequestError.90001`, with the RIC in the message up to its `.U`.
    - Daily: `TS.Interday.UserRequestError.70005`, "The universe is not found", with no RIC named. A wrong stock suffix (`NVDA.K`) gets the same daily answer.
    - Both codes match `NO_DATA_CODE`, so the no-data codes don't need widening. The fake had assumed 90001 for daily; it now uses 70005 and the real message, and the contract test still passes.
  - **A live contract asked in the caret form** is a never-listed RIC (90001).
  - **A field the RIC doesn't carry is not an error,** contrary to LDG §4.6 and the fake. `SETTLE`, and a field name no service knows (`PMCC_NO_SUCH_FIELD`), each paired with TRDPRC_1, came back answered with TRDPRC_1 only.
    - The fake now leaves such a field out of the RIC's answer (`carried`). Its `FIELD_NOT_CARRIED` code is gone, and the two tests that used it now check the real behaviour.
    - A RIC asked only for fields it doesn't carry is still an assumption: the fake answers it with no bars.
  - **Batches:**
    - An hourly batch holding a listed and a never-listed RIC can't be read (the `UniverseContainer` TypeError).
    - The daily batch answers without the never-listed RIC.
    - An hourly pair asked for BID and SETTLE comes back as flat RIC columns, which the reader refuses as `Unattributable`.

    All three are as the fake and the contract test had them, and `fetch_rics` splits the batch and settles each RIC alone.
  - **Still assumptions:** the permission code, and what a signed-out Workspace returns. No probe can safely produce either.

### DEC-84 — Calendar, chain discovery and the fetch plan
**Status:** ENG · **Affects:** P1-06, P1-07, P1-08, P3-02 (`MarketView.calendar`), P5-05

- **Where things live:**
  - **`pmcc/domain/calendar.py`:** `SessionCalendar`, which gives sessions and their closes, week-open and week-final sessions, weekly and monthly expiries, and the sessions before a day. It sits in `domain`, not in `data` where ARCHITECTURE §3.1 first put it: `MarketView` (`strategy/ports.py`) returns it, and `strategy` may not import `data` (ARCHITECTURE §3.3 rule 3). Standard library only.
  - **`pmcc/config/calendar.py`:** `configs/calendar.yaml`, validated by pydantic into a `SessionCalendar`. The file is found from the module, not the working directory. Unknown keys, unnamed or repeated days, weekend closures and days outside the span are refused.
  - **`pmcc/data/calendar.py`:** the tape check (DEC-33): `tape_days`, `check_trading_days`, `sessions_from_tape` and `CalendarMismatchError`. A trading day is an ET date with a bar starting 09:00–15:00 ET; extended-hours bars alone never make one. A tape can't show a 13:00 close (post-market trading carries on), so early closes come from the table.
  - **`pmcc/data/discovery.py`:** increments (DEC-14), `Band` and `Pad` ladders in integer cents, `session_ranges`, `band_vol`, `nearest_monthly` and `plan_symbol` (a `FetchPlan` of `Unit`s).
- **A day outside the table raises** rather than being guessed. The table covers 2025–2027, so a window or a long-leg expiry past 2027 needs it extended first.
- **How the plan reads ARCHITECTURE §6.3.** These choices size what is fetched; they never decide what a rule sees.
  - **DTE and T:** DTE is in calendar days, and a band's T is calendar days ÷ 365. These follow DEC-24's recommendation, but since they only size fetches they don't wait for DEC-24's answer. They reproduce §6.3's example: the Jul 6 – Sep 18 2026 window needs the Nov 2026 – May 2027 monthlies (a test).
  - **Band volatility:** σ̂ = 1.25 × the highest RV20 in the window. RV20 here is the sample standard deviation of 20 daily log returns of session closes × √252, taken at every close from the last one before the window to its end. Pricing's RV20 is DEC-26's.
  - **Long candidates:** a monthly is a candidate on any session of the window. Its unit runs from the first such session to its expiry or the window's end, whichever comes first. Its band is the union over those weeks, from weekLow·e^(−2σ̂√T) up to the week's high, split into 3 bands of equal price ratio, each probed for its own increment (DEC-48's outcomes).
  - **Weeks:** every calendar week with a session in the window gets its weekly calls, and a put on its week-open session if that session is in the window; the next weekly follows the last.
  - **Pads and anchors:** EMest takes the unit's high as spot, which errs wide. A monthly's outer edges are padded 2 steps, and its 3 bands overlap by 1 step at each cut. The increment anchor is the nearest multiple of $10, ties going up, and never below $10.
  - **The estimate (P1-08):** a `FetchPlan` holds bands, not strikes; a ladder needs the band's increment, which only an option request can measure. So the estimate printed before any option request has to assume increments, from the probe reports' DEC-14 values, and say so.
  - **One unit per expiry and right:** a monthly Friday in the window can be both a weekly expiry and a long candidate. The unit then spans both date ranges and keeps every band, and the increment is probed per band (DEC-14's regions). A unit's sidecar therefore records a step per band.
- **Session ranges** come from session bars only (DEC-06), so extended-hours ticks stay out (LDG §4.10). A trade print widens the range too. The close is the close bar's TRDPRC_1.
- **Outcome:** 2026-09-27 — P1-06's tests pass: `tests/unit/domain/test_calendar.py`, `tests/unit/config/test_calendar_file.py`, `tests/unit/data/test_tape_calendar.py` and `tests/unit/data/test_discovery.py`, 86 tests, including a hypothesis property that every ladder is an integer-cent grid covering its padded range. One bug was caught while writing them: a monthly expiring inside a long window was banded over weeks after its expiry (T < 0). That led to the change recorded in DEC-48's outcome.
- **Outcome:** 2026-09-27 — an adversarial review of P1-04 and P1-06 (4 reviewers, 2 skeptics per finding; 44 findings, 34 unique, the 12 most severe verified: 10 confirmed, 2 plausible, none refuted). For P1-06:
  - **Confirmed, high:** the long band's top sat near δ 0.72–0.77, so δ 0.70 strikes weren't fetched. It now reaches the money (DEC-48).
  - **Plausible, high:** one increment probed at the long band's centre took the deep grid and would miss finer strikes near the money. The band is now 3 bands, each probed (DEC-48).
  - **Confirmed, medium:** a window ending mid-week lost its last week's put and next weekly (fixed); the tests couldn't tell which RV20s `band_vol` reads (three new tests kill the "skip the last close", "skip the pre-window close" and "start one late" mutants); no test covered the put on the window's first week-open (added).
  - **Unverified, fixed anyway:** the monthly pads are now pinned by a test.
  - **Now:** 97 tests in the four P1-06 files; 527 in the suite.

### DEC-85 — Probe design
**Status:** ENG · **Affects:** P1-04, P1-05, P1-08; DEC-06–09, DEC-12–14, DEC-47, DEC-83

- **Where:** `pmcc/data/probe/`, one module per check:
  - `identifiers`: DEC-12, plus the table against LSEG's daily bars (DEC-33)
  - `errors`: DEC-83
  - `bars`: DEC-06
  - `edges`: DEC-47
  - `fields`: DEC-13
  - `increments`: DEC-14
  - `coverage`: DEC-08 and DEC-09
  - `depth`: DEC-07
  - `runner`: sequences them and writes the report

  The probes ask through the `HistoryProvider` port; `pmcc.cli` hands them an LSEG session (ARCHITECTURE §3.3 rule 2).
- **Report:** one JSON file per symbol and day, `data_cache/probes/{SYM}_{YYYYMMDD}.json`, with sorted keys, LF endings and NaN written as null. It is written whole through a temporary file and never over an existing one; to probe again, rename the old report. `requests` counts every request made.
- **Order:** stock RIC, then daily bars, then the error answers, then the checks that read quotes (increments, bars, edges, fields, coverage, depth). A never-listed RIC must come back with a no-data code. If one answers anyway (with bars, or an answer that can't be read), the report stops after the error answers and says why, and the command exits 1. If it fails any other way, that failure is asked again like any fetch and persists as an outage. An outage writes nothing.
- **Asking:** the stock-suffix candidates, the error answers, the fields and the date edges go through `ask`, which records what the service answered: bars, a no-data code, or (for a batch) an answer that can't be read. Anything else (a transient failure, or a single RIC's unreadable answer) is asked again with DEC-49's 3 attempts and then raises an outage, because a dead or signed-out Workspace shows up only as transient failures (DEC-83). The other checks ask through `fetch_rics` and `fetch_contracts`, as the fetch will.
- **Methods:**
  - Option strikes are $10 anchors near spot, or near 0.8 × spot for a long, so they are listed on any grid up to $10.
  - The δ 0.90–0.70 strikes come from Black-Scholes with r = 0 and a 60-session realized volatility, because the pricer (P2) isn't built. Below-intrinsic with r = 0 is a lower bound on DEC-08's IV failures.
- **Tests:** `tests/unit/data/test_probe.py` runs the whole probe over `FakeMarket` (`tests/fakes/market.py`). That fake is a `HistoryProvider` over a synthetic market and fails as the port does over lseg-data (DEC-83): a dying Workspace is a transient failure, never an outage raised by the port, and there are no bars on or after its `today`. The CLI tests swap it in for `lseg_session`.
- **Outcome:** 2026-09-27 — all 12 symbols probed in about 20 minutes. NVDA took 89 requests (the first version); the rest took 94–105 each, about 100 s. No symbol stopped, and no request needed a retry.
  - **Added after NVDA,** before the other 11 ran: the DEC-47 date edges, 10- and 11-month depth samples, and a field name no service knows (because `SETTLE` hadn't been refused). NVDA's report predates these.
  - **One check turned out blind:** LSEG's history is split-adjusted, so the largest daily moves can't show a split (DEC-12).
  - **Tests:** `tests/unit/data/test_probe.py` (40) and the CLI's probe tests (4) in `tests/unit/test_cli.py`.
- **Outcome:** 2026-09-27 — an adversarial review of P1-04 and P1-06 (4 reviewers, 2 skeptics per finding; see DEC-84's outcome for the totals). For P1-04:
  - **Confirmed, high:** a Workspace dying during the DEC-83 asks got a report written that blamed LSEG's codes, because `ask` recorded transient failures instead of retrying them. `ask` now retries, and a persisting failure is an outage that writes nothing. `FakeMarket` had raised `ProviderOutageError` from the port, which `LsegProvider` can't do for a desktop session, so no test took the real path; it now fails with transient errors, and the probe is tested dying at 9 points.
  - **Confirmed, medium:**
    - the date-edge check asked for sessions not yet traded when run before a week's final session; it now uses the latest complete week, and the expired weekly is the latest at least a week back;
    - the calendar check was tested only on a tape that matches; a mismatching tape is now tested;
    - DEC-07 overstated how far every leg reaches and misread XLE's pre-split samples (split-adjusted closes gave wrong strikes); DEC-07 is corrected.
  - **Plausible, medium:** the stop gate was tested only with every never-listed ask failing; each interval is now tested alone.
  - **Unverified, fixed anyway:**
    - tests for an empty field, a split-like move, a band top past $999.99, a quote matching on one side only, `last_session` at the close, on a holiday and on a half-day, and the first-suffix choice with several suffixes answering;
    - stale docstrings about a field a RIC doesn't carry;
    - the doc figures above (request counts, AMD's 3.002%, TLT's one strike, the Jan 2027 claim, the close and venue gaps, the edge's precision, DEC-13's `.N` caveat, DEC-49's row, DEC-83's status line).
  - **Now:** 63 probe tests and 5 CLI probe tests. The reports already written stand. The fixes change what a failing run writes and which week the date edges use, not what these successful runs recorded.

### DEC-86 — Universe config and strict YAML
**Status:** ENG · **Affects:** P1-05, P1-08, P3-01 (`RunConfig`), P3-09, P4-05 (`index.json`), P6-05

- **Where:** `pmcc/config/universe.py` validates `configs/universe.yaml` with pydantic.
  - `read_universe_file()` checks the file on its own.
  - `load_universe(calendar)` also checks the window's sessions.
  - The file is found from the module, like the calendar.
  - Both config files are read by `pmcc/config/yaml_file.py`'s `read_yaml`: safe YAML that refuses a mapping key given twice. `yaml.safe_load` keeps the last of two equal keys without a word, so a second `stock_ric:` in an entry, or a second `closed:` list in the calendar, would quietly replace the first.
- **What it holds now:**
  - `window` (DEC-07);
  - `risk_free_rate` (DEC-11): the value used, plus the quote, series, date and source it came from;
  - `symbols` (DEC-12): symbol, stock RIC and option root.

  `starting_cash` joins with P3-09 (DEC-30) and the bootstrap seed with P6-05 (DEC-61). Until then an unknown key is refused.
- **What it refuses:**
  - a window that doesn't run from a week-open session to a week-final session, spans fewer than 10 weekly expiries (Spec › Universe), or falls outside the calendar;
  - an r quoted on or after the window's first day, which the first decision couldn't have known;
  - an r that isn't its quote converted. `value` must equal ln(1 + y·91/365)·365/91 rounded to 4 decimals, so a typo in either number fails at load;
  - a symbol listed twice, or a stock RIC that names another symbol or has no venue suffix;
  - a root `OptionId` would refuse. The pattern is copied from `OptionId`; a test builds a RIC from every shipped root, and another feeds the same odd roots (digits first, a dot, a space, a trailing newline, non-ASCII) to both and requires the same answer;
  - an empty `series` or `source`, and a key given twice anywhere in the file.
- **Calendar coverage:** a test runs the real fetch planner (`plan_symbol`) over the window on a synthetic tape. So every calendar date the fetch will ask for, from the warm-up (Feb 13 2026) to the last long candidate (Jun 17 2027), is inside `configs/calendar.yaml`. It uses the planner's own constants rather than copies. `config` can't import `data` (ARCHITECTURE §3.3), so this check lives in the test.
- **Outcome:** 2026-09-28 — 28 tests in `tests/unit/config/test_universe_file.py`. 14 planted mutants were all killed: each refusal above, the bill's term and its year basis, the calendar check, and unknown keys.
- **Outcome:** 2026-09-28 — an adversarial review of P1-05 (4 reviewers, 2 skeptics per finding; 14 findings, 11 unique, all verified: 1 confirmed, 6 plausible, 4 refuted). No finding showed a bug in the shipped code or a misrecorded PO answer; all 7 are fixed.
  - **Confirmed, low:** the only refusal of a bad r was 2 bp off, and the quote was never wrong, so a 1 bp tolerance in the check survived. Now refused: 1 bp high and low, and a quote 0.01 off either way.
  - **Plausible, medium:** the own-RIC rule was tested only on an unrelated ticker, so a prefix check survived (`SPY` with `SPYG.P`). Now tested both ways (`SPYG.P`, and `AMDL` with `AMD.O`).
  - **Plausible, low:**
    - unknown keys were tested only at the top level; now in the window, the rate and a symbol entry too;
    - an empty `source` or `series` was never tried (the "no source" case removed the key);
    - `yaml.safe_load` let a key given twice overwrite silently, in both config files; `read_yaml` now refuses it;
    - nothing tied the root and venue patterns to `OptionId`'s rule; now a shared-inputs test and venue cases (`SPY.p`, `SPY.PQX`);
    - DEC-13 had been marked SETTLED on a probe basis, which the legend doesn't allow while the `.P` primaries are unprobed; back to VERIFY.
  - **Refuted:** the fetch's stock-RIC source isn't named in ARCHITECTURE §6.1 (P1-08 will read `Universe`); the conversion assumes investment basis whatever `series` says (documented, and DGS3MO is investment basis); the spec's "back to late Oct 2025" (DEC-07's own headline); the README's Jul 6 – Sep 18 fetch example (the spec's CLI example).
  - **Now:** 54 tests in `test_universe_file.py` and 18 in `test_calendar_file.py`. 30 mutants re-run against them, the 14 above plus the 16 the review showed or suggested would survive (tolerances, prefix checks, looser patterns, `extra="ignore"` per model, empty strings, a lax YAML reader in either loader): all killed.

### DEC-87 — Cache writes, sidecars and the loader
**Status:** ENG · **Affects:** P1-07, P1-08, P3-02, P3-08

- **Where:**
  - `pmcc/data/files.py`: `write_new` (a `.partial` file hard-linked into place, which fails if the target exists) and `replace_file` (for the manifest, a derived index). The probe report writer uses `write_new` too.
  - `pmcc/data/cache.py`: `UnitPull`, built by `chain_pull` or `stock_pull` from `fetch_contracts` or `fetch_rics` results, and `SymbolCache` (`write_unit`, `has_unit`, `units`, `orphans`, `rebuild_manifest`).
  - `pmcc/data/load.py`: `load_symbol` → `SymbolData`, plus `quantize`.
- **Dependency direction:** `cache` imports `fetch`'s result types. So P1-08's unit loop, which fetches and then writes, sits above both, not inside `fetch.py` as ARCHITECTURE §3.1 first said; P1-08 names its module.
- **A unit exists once its sidecar does.** The parquet is written first and the sidecar last.
  - A write that fails before the sidecar is written removes the parquet it just wrote.
  - A process killed between the two leaves a parquet with no sidecar (an orphan). `write_unit` refuses to replace it, and `load_symbol` refuses to load until it is moved aside.
  - Temp files are named `{file}.{random}.partial`, so one a killed write left never blocks a later write, and nothing reads it.
  - `write_unit` reads every sidecar before writing anything, so an unreadable one stops it first. Once the sidecar is written the unit is cached; if rebuilding `manifest.json` then fails, the index stays stale until the next write.
  - A sidecar must record the unit its path names. A unit's pair renamed in place inside `chains/` is refused (`CacheError`), not read as the unit it records: moving aside means into `superseded/`.
- **One manifest entry per contract asked,** not per RIC asked, so answered + unanswered = requested counts contracts (LDG §5). `chain_pull` refuses a result that doesn't cover exactly the contracts requested, or a contract outside the unit's expiry and right.
- **Parquet:** `bar_start_utc`, `ric`, `expiry`, `strike_cents`, `right`, then one float64 column per field requested, in request order. A field no RIC returned is an all-null column, and the sidecar's `fields_returned` says so. Rows are one per RIC and bar, sorted.
- **The bars hash** is over each bar's start and its fields' values (sorted by field name; `float.__repr__`; empty cells as empty), in time order.
- **Loader:**
  - It reads the sidecars, never `manifest.json`. It checks every parquet's sha256 against its sidecar, and refuses a missing or changed file, an orphan, or a symbol with no stock unit.
  - It checks the stock tape's trading days against the calendar over the stock unit's dates (DEC-33).
  - Prices (`BID`, `ASK`, `TRDPRC_1`, `OPEN_PRC`, `HIGH_1`, `LOW_1`) become Int64 $0.0001 units, exactly as `Price.from_dollars` would give them (DEC-44). The scaling is vectorized, and a value within 1e-6 of a half unit, or of $100,000 or more, goes through `Price.from_dollars` itself. Hypothesis tests compare the two on floats within ±$1M and on five-decimal half-unit values within ±$100M (sampled, not exhaustive), plus fixed cases above $1M where plain float scaling rounds wrongly. Volumes (`ACVOL_UNS`, `NUM_MOVES`) stay float64.
  - It adds `bar_end` (Datetime, America/New_York), `session_bar` (the bar ends on one of its session's bar ends, 10:00 to the close) and `valid_quote` (BID > 0, ASK > 0, ASK ≥ BID; a missing side is invalid).
  - `SymbolData.chains` is keyed by (expiry, right).
- **Outcome:** 2026-09-28 — 60 tests (`test_cache.py` 34, `test_load.py` 21, `test_files.py` 5). The P1-07 done-when cases are all among them. 19 planted mutants were all killed. The one that survived the first run (a bars hash reading only the first bar) led to three direct hash tests.
- **Outcome:** 2026-09-28 — an adversarial review of P1-07 (4 reviewers, 2 skeptics per finding): 29 findings, 21 unique; the 12 most severe verified as 10 confirmed, 1 plausible and 1 refuted; 9 low ones unverified. All 11 confirmed or plausible are fixed, and so are the 9 unverified ones:
  - **Confirmed, medium:**
    - a unit's pair renamed in place inside `chains/` was still read as the unit its sidecar records; it double-counted in the manifest and changed the hash of identical data. A sidecar must now record the unit its path names, or it is refused.
    - test gaps: `OPEN_PRC`, `HIGH_1` and `LOW_1` quantizing and float volumes; session bars over more than one day (now across the Nov 1 clock change); the bars hash on `BID`, `TRDPRC_1` and sub-cent digits; per-contract entries with two contracts answered.
    - stale docs: ARCHITECTURE §6.1 step 4 still skipped units "already in the manifest", and TEST-STRATEGY §5 described the synthetic cache as "parquet schema and manifest".
  - **Confirmed, low:**
    - `write_unit` could raise after the unit was cached (a failed manifest rebuild), against "a write that raises leaves no file". Every sidecar is now read before anything is written, and the docs say what a failed rebuild leaves.
    - a `.partial` left by a killed write made the next write fail once. Temp files now have unique names. Writing the new tests also found that a failed temp write couldn't remove its file on Windows (an open handle); it is now closed first.
    - DEC-46 said "per-RIC manifest" though entries are per contract; now noted in DEC-46.
  - **Plausible, medium:** no put unit or two units of one expiry was cached or loaded; now tested, with a contract of another expiry refused.
  - **Unverified, low, fixed:** the stock unit's sha and missing-file checks; a tape missing its first session; quantizing above $1M; the hash's independence from entry order; the `UnitPull` guards and the `empty` miss reason; ARCHITECTURE §4.2's `bar_start` row and §6.1's resume note on orphans; `fetch.py`'s docstring; this entry's wording on the quantize tests.
  - **Refuted:** the sidecar can't record an increment anchor that didn't answer (DEC-14). That is P1-08's to add, when it probes increments.
  - **Now:** 90 tests (`test_cache.py` 51, `test_load.py` 32, `test_files.py` 7). The review's 25 surviving mutants, plus the 19 above, re-run against them: all 44 killed (one more, `%g` formatting in the bars hash, needed a seventh-digit case).

### DEC-88 — The fetch command: plan, estimate, unit loop
**Status:** ENG · **Affects:** P1-08, P1-09, P1-10; DEC-14, DEC-16, DEC-46, DEC-47, DEC-83, DEC-87

- **Where:**
  - `pmcc/data/pull.py`: `prepare` (the stock tape and the plan) and `pull_units` (the unit loop), with `pull_unit` and `measure_step`. It sits above `fetch` and `cache`, as DEC-87 said it must.
  - `pmcc/data/estimate.py`: the steps taken from the probe report, and the estimate.
  - `pmcc/data/coverage.py`: the summary (DEC-16).
  - `pmcc fetch` in `pmcc/cli.py`.

  ARCHITECTURE §3.2's `fetch_symbol()` became `prepare` and `pull_units`, so the command can print the estimate between them.
- **Target:** the symbol must be in `configs/universe.yaml`, which gives its stock RIC and option root (DEC-12). `--start` and `--end` are the window's first and last sessions, inclusive (DEC-47). They don't have to be the universe's window, but both must be sessions and the start no later than the end, or the command stops before asking anything: a band's step is measured on its unit's last session, often the window's end, and a weekend or holiday there left every such band unmeasured (the review, below).
- **The plan comes from the stock tape.**
  - If the stock unit is cached, the plan is built from it (its sha256 checked) with no request, and its dates must be the ones this window needs. Otherwise the tape is one hourly request.
  - So a resumed run plans exactly what the first run planned.
  - The tape's trading days must match the calendar (DEC-33).
- **The cache must match the plan.** Every cached chain unit must be one the plan would write, with the same dates and bands (region, low, high). If one isn't, the command stops before any option request and names the units to move into `superseded/` (DEC-46). This catches a fetch of another window, or a planner change, over an old cache.
- **`--plan-only` writes nothing.** It asks for the stock tape (1 request) if it isn't cached, prints the estimate, and stops. A full run prints the same estimate, then writes the stock unit and the chain units in plan order.
- **The estimate:**
  - It takes its steps from the symbol's newest probe report (`data_cache/probes/{SYM}_{YYYYMMDD}.json`): the finest step measured per region, from records whose anchor answered. Near the money comes from the two weekly records, deep ITM from the two monthly ones. The long bands are deep ITM by region, but the top one reaches the money, so both monthly records count for them; that is how DEC-14's "the probe report's step for its region" is read for the long bands.
  - With no probe report, or with a newest one that stopped early or can't be read, the command stops before asking anything. It doesn't fall back to an older report: a stopped probe says something about LSEG changed.
  - Requests: the low figure is the strikes (the union of each pending unit's band ladders) + 5 per band, for the step asks. An hourly batch holding one unlisted strike is asked again one RIC at a time (DEC-83), and a recently expired contract can be asked in both forms (DEC-45), so the high figure is three times the low one. The review measured fetches on the fake market at 2.3 to 2.5 times the low figure, and an NVDA-sized plan at 1.9 times; the first version printed the low figure alone. Minutes assume 44 RIC requests a minute (LDG §4.15). Cached units are left out.
  - The printed text is ASCII only: Git Bash on Windows prints it in cp1252 (DEC-58).
- **Strike steps (DEC-14):**
  - Each band's step is measured on its unit's last session, by which every strike the unit lists is listed. A monthly still live at the window's end is asked on the window's last session.
  - It asks the unit's own right, for daily BID and ASK, a day wider on each side, and counts only bars dated that session (DEC-47).
  - The PO's neighbour anchors are asked together in one request.
  - The sidecar records, per band, the session, the anchors asked, the strikes that answered, and the source: `measured`, `neighbour` or `probe_report`. This closes DEC-87's note that an unanswered anchor couldn't be recorded. `CachedUnit` reads the bands back, with the fields asked and returned.
- **A unit's fetch:** the union of its bands' ladders (the overlapping cuts ask a strike once), hourly, all 8 fields (DEC-13), through `fetch_contracts`. The fetch date for DEC-45 is the run's date in ET.
- **Resume:** units are written one at a time. An outage raises and loses only the unit in flight; the command exits 1 and says to run it again. `fetch.unit.start|done`, `fetch.ric.unanswered`, `fetch.retry` and `fetch.batch.rejected` carry `symbol` and `unit` (`stock` for the tape), bound through structlog's contextvars (DEC-83). New events: `fetch.plan`, `fetch.increment.unmeasured`, `fetch.coverage`, `fetch.coverage.unit`.
- **The strike field:** once planned, a band whose ladder on a $10 step (the widest DEC-14 can find) would pass $999.99 stops the command before any option request, as a question for the PO (DEC-12). It errs on the side of stopping; DEC-12 found every symbol fits. The first version left this to `build_ric`, which raises only after the unit's step asks.
- **Tests:** the unit loop runs over `FakeMarket` (DEC-85), which answers a whole symbol's dated requests at the port as FakeProvider does. It gains two hooks: `unlisted` (strikes no expiry lists) and `listed_days`.
- **Outcome:** 2026-09-28 — 55 new tests: `test_pull.py` 24, `test_estimate.py` 8, `test_coverage.py` 5, the CLI's fetch tests 7, and 11 across `test_discovery.py`, `test_load.py` and `test_cache.py`. 726 in the suite.
  - **P1-08's done-when:** after an outage at any of five points (the first step ask, the second, and three points mid-run), a resume asks only for the missing units and leaves the cached files byte-identical. The estimate prints before the first option request, and `--plan-only` asks only for the stock tape.
  - **Mutants:** 25 planted in the new guards: the pending filter, the cached tape, the plan checks, the neighbour anchors and the finer step, the day filter and the widening, the estimate's steps and requests, the report choice, the coverage denominator, near the money, quote validity, missing fields, the estimate's place in the command, the sidecar record, and `unit_kind`. The first run left 3 alive: no bar with an invalid quote, a missing-fields check that matched only a prefix, and no test of a unit that is both a weekly and a monthly. With tests added for each, all 25 are killed.
  - **Found while building:** once `fetch` was built, the CLI's stub test for it opened a real LSEG session. The suite's network guard blocked it, so nothing was asked. That stub case is gone, and the fetch tests swap in `FakeMarket`.
- **Outcome:** 2026-09-28 — an adversarial review of P1-08 (4 reviewers, 2 skeptics per finding): 34 findings, 28 unique. The 12 most severe were verified: 10 confirmed, 1 plausible, 1 refuted; 16 low ones went unverified. All 10 confirmed, the plausible one and all 16 low ones are fixed, most with regression tests:
  - **Confirmed, medium:**
    - **A window ending on a weekend or holiday** left every unit ending there (the next weekly and every monthly) measured on a day with no bars, so their bands took the probe report's step and were cached that way. The window's ends must now be sessions, checked before any request.
    - **A probe report that stopped early**, which `pmcc probe` writes on purpose, or one that can't be read, ended the command with a traceback. It now stops with a message, before asking anything.
    - **The README** still said only `pmcc probe` works.
    - **Test gaps** that let plausible bugs through: the region of an unmeasured band's fallback; near-the-money on a merged unit, on deep bands and at the band's top; the fetch date that picks the RIC form (DEC-45); the 8 fields asked; which neighbour's step is taken (the finer one, never the unanswered anchor's offsets); coverage counting a bar outside the session or a day early; the estimate's per-kind rows and its "to write" count.
  - **Plausible, medium:** the near-the-money line counted a merged unit's near strikes over its whole span. Put to the PO, who chose the weekly part only (DEC-16).
  - **Refuted:** that DEC-16 recorded ENG choices as the PO's answer. Per-unit coverage does reach the screen, through the log.
  - **Unverified, low, fixed:**
    - a reversed window asked for the stock tape first; now refused before any request;
    - this entry's $999.99 claim was wrong (the step asks came first); the plan is now checked (above);
    - the estimate understated the re-asks, so it now prints a low and a high figure (above); its docstring's "errs high" was false;
    - the stock tape's log events had no `symbol` or `unit`;
    - the printed estimate held `§`, which Git Bash on Windows shows garbled (DEC-58); the estimate and the summary are now ASCII, and tested so;
    - the CLI tests left structlog configured for later tests; it is reset after each;
    - tests for: the sidecar's anchors and answers on a neighbour or fallback band, both neighbours asked in one request, a neighbour band not flagged, the kind table's unit counts, a cached unit with the same bands but other dates, and the command handing the probe report's steps over as the fallback;
    - docs: `--plan-only` does ask LSEG for the tape (README); FakeMarket serves puts and the daily step asks, and stands in for FakeProvider in P1-08's done-when (TEST-STRATEGY); DEC-83's note on where the loop lives; IV failures join at P2-04, not P2-02 (DEC-16).
    - The deep-ITM fallback drawing on both monthly records is kept, and its reading of DEC-14 is written down above.
  - **Now:** 77 new tests in P1-08 (`test_pull.py` 37, `test_estimate.py` 13, `test_coverage.py` 6, the CLI's fetch tests 10, and 11 across `test_discovery.py`, `test_load.py` and `test_cache.py`), 748 in the suite. **Mutants:** 51 re-run on the reviewed code (round 1's 23 whose code is unchanged, and 28 for the review's findings and fixes, the reviewers' surviving mutants included). One survived, a strike check on too fine a step, and was killed by a new test: all 51 are killed.

### DEC-89 — Pricing: Black-Scholes, the IV solver, measures, the chain pricer
**Status:** ENG · **Affects:** P2-01 to P2-04, P3-02, P3-06, P3-07; DEC-16, DEC-23 to DEC-27, DEC-44

- **Where:** `pmcc/pricing/`, one module per job:
  - `black_scholes.py`: `price`, `greeks` (both check their inputs) and `price_vega` (the solver's unchecked inner loop).
  - `expiry.py`: T and DTE (DEC-24).
  - `iv.py`: `implied_vol` and the `IvCode`s.
  - `measures.py`: spot and close, ATM, EM, RV20 (DEC-23, DEC-25, DEC-26).
  - `chain.py`: `price_quotes` (one bar) and `price_symbol` → `PricedSymbol` (a whole symbol, memoized).
  - `pmcc/domain/quotes.py`: `Quote`, a valid BID/ASK and its mid, which MarketView's `quote()` will return (P3-02).
- **Dependencies:** `pricing` still imports only `pmcc.domain` from the package (ARCHITECTURE §3.3 rule 4). Outside it, it uses numpy, scipy (`scipy.special.ndtr` for N) and polars: `chain.py` reads the loader's frames by their columns (`bar_end`, `strike_cents`, `BID`, `ASK`, `valid_quote`, `session_bar`, `TRDPRC_1`) without importing `pmcc.data`. `pmcc.data.coverage` now imports `pricing` for the IV-failure line (DEC-16). pyright gets minimal scipy stubs in `typings/scipy/` (`ndtr`; `brentq` for the tests), like the lseg ones (DEC-42).
- **Black-Scholes:** ARCHITECTURE §7's formulas with q = 0, vectorized; every argument broadcasts. A put uses N(−d) directly rather than parity, which would lose precision to cancellation on a tiny, far out-of-the-money put.
- **The IV solver:**
  - **Codes, in the order they're checked:** `EXPIRED` (T ≤ 0), `NO_QUOTE`, `NO_SPOT`, `BELOW_FLOOR`, `ABOVE_CAP`, `NO_CONVERGENCE`.
    - `NO_SPOT` is new to ARCHITECTURE §7's list: a bar where the underlying didn't trade has no spot (DEC-23), so nothing on it can be priced.
    - `NO_QUOTE` outranks `NO_SPOT`, so an IV failure always means the contract itself had a valid quote. The coverage line counts it that way.
  - **A put's bounds** are European: floor max(0, K·e^(−rT) − S), cap K·e^(−rT). Puts feed only EM, which uses their mids; no rule reads a put's IV.
  - **Tolerance:** ARCHITECTURE §7 said stop at |model − mid| < 1e-6·max(1, mid). P2-02's done-when asks for |Δσ| < 1e-6, and a price tolerance of 1e-6 gives that only when vega exceeds max(1, mid), which a deep ITM long-dated call often doesn't. The solver stops at 1e-9·max(1, mid), or when its bracket is narrower than 1e-12. That pins σ to 1e-6 wherever vega ≥ 1e-3·max(1, mid). Where the price barely moves with vol the solved vol is looser, though it still reprices the mid: 719 of NVDA's solved lanes, off `brentq` by up to 3e-5 of vol, with a delta difference under 1e-8.
  - **Method:** Newton, safeguarded. Each lane keeps a bracket known to hold its root, starting at [1e-4, 5.0]. A step that would leave the bracket, or a vega under 1e-8, bisects instead. The start is Manaster and Koehler's vol, where vega peaks.
  - **`NO_CONVERGENCE`** means no vol in [1e-4, 5.0] prices the mid (checked before iterating), or 100 iterations ran out. On NVDA all 437 are the first kind: deep ITM calls within a week of their expiry (297 on expiry day, 140 one to seven days before), whose extrinsic no vol up to 500% explains.
  - **A mid exactly on the floor** solves at a vol near zero; only a mid under it is `BELOW_FLOOR`.
- **The chain pricer:**
  - **Mid:** a contract's IV comes from (BID + ASK) / 2 exactly, not the $0.0001-rounded `Quote.mid` that fills and EM use (DEC-44). The difference is at most $0.00005.
  - **Eligible** means the IV solved (Spec › Greeks and pricing). DEC-27's limit Greeks go on calls below their floor, which stay ineligible.
  - **Columns per contract:** mid, spread % of mid, IV, code, δ, Γ, θ, ν, and extrinsic: mid − max(0, S − K) for a call (Spec › E-L3), mid − max(0, K − S) for a put.
  - **A whole symbol:** `price_symbol` prices each unit's session bars in one vectorized pass. It joins the stock's TRDPRC_1 on the same `bar_end` and takes T from `years_to_expiry` per bar, so it has one source for T. `PricedSymbol.snapshot(bar_end, expiry, right)` slices a bar and keeps it, and `codes(expiry, right)` counts the unit's outcomes.
  - ARCHITECTURE's `price_chain(snapshot, spot, now, r)` became `price_quotes` (one bar's arrays) plus `price_symbol` and `PricedSymbol.snapshot` (the memo), so a batch prices a symbol once and every run shares it.
- **Measures:** `atm_strike` takes the strikes it's given; which are listed is MarketView's (DEC-32). `atm_iv` takes that strike and a priced call chain. `expected_move` takes two `Quote`s or None and returns a `Price`. `rv20` takes the calendar, the decision time and the close-bar trades by `bar_end`.
- **Tests:** 110 new, 858 in the suite (`tests/unit/pricing/`, `tests/unit/domain/test_quotes.py`, two in `test_coverage.py`, one in `test_cli.py`), after the review below.
  - The Black-Scholes reference values were computed once with mpmath at 50 digits (run in a throwaway environment, not a dependency) and agree with Hull's worked example (15.6) to its four decimals.
  - Hypothesis checks put–call parity, each Greek against a central difference, the solver against scalar `brentq` where the mid pins the vol down, and a solved vol repricing its mid everywhere else. Its spot step scales with S·σ·√T, since a fixed step blurred short, calm options.
- **Outcome:** 2026-09-28 — P2's done-when lines hold.
  - **P2-01:** the reference values match to 1e-8, and parity and the finite-difference Greeks hold (300 derandomized examples, plus 8 random seeds).
  - **P2-02:** |Δσ| < 1e-6 against `brentq` where solvable, and each code has a test.
  - **P2-03:** a missing put quote leaves EM unavailable, and RV20 ignores the current session's bars, even at its close.
  - **P2-04:** NVDA's full window (400,784 session contract-bars) prices in 1.4 s, after a 0.6 s load (limit 10 s). The coverage summary shows IV failures: 8.3%, 32,403 of 390,652 (DEC-16, DEC-27).
  - **Found while building:**
    - T across a clock change was an hour short, because Python subtracts two times in the same zone by wall clock; now in UTC (DEC-24).
    - NVDA's empty May 2027 unit (DEC-08) crashed the pricer; an empty unit now prices to nothing, with a test.
- **Outcome:** 2026-09-29 — an adversarial review of P2 (4 reviewers, 2 skeptics per finding): 28 findings, 18 unique. The 12 most severe were verified: 10 confirmed, 1 plausible, 1 refuted; 6 low ones went unverified. All the confirmed and plausible ones and all 6 low ones are fixed or put to the PO:
  - **Confirmed, medium:**
    - **Test gaps** that let plausible bugs through: the coverage line's denominator (an expiry-close bar counted, or a no-spot bar dropped); DEC-27's limit Greeks spread to no convergence, no spot or the expiry close; `pmcc fetch` pricing the summary at the wrong r; the snapshot memo keyed without right or expiry. Each now has a test.
    - **Wrong NVDA figures in the docs:** the 437 no-convergence bars aren't all on expiry day (297 are; 140 fall one to seven days before), and 16 below-floor bars at 120–270 DTE, not one, exceed K/S 0.6. Corrected in DEC-27, here and in BUILD-PLAN.
    - **ARCHITECTURE §5.2's MarketView** didn't match the measures: `spot()` couldn't say there was no trade, and `session_closes(n)` can't feed `rv20`. §5.2 now sketches `spot() -> Price | None` and `close_trades()`, still indicative until P3-02.
    - **A held short has no delta on its expiry close bar,** where DEC-20 still runs short exits. Added to DEC-27's open items for P3.
  - **Confirmed, low:** the 1e-6 vol guarantee holds only where vega ≥ 1e-3·max(1, mid) (qualified above, in ARCHITECTURE §7 and in `iv.py`); the EM rounding test couldn't tell each mid rounded from the straddle rounded (a test now can).
  - **Plausible, medium:** `snapshot()` read a naive time in the machine's zone, so Windows and Ubuntu CI would pick different bars (DEC-58). It now refuses a naive time, as `to_et` does.
  - **Refuted:** that the float spread % misjudges E-T1's 3% and 10% limits at the boundary. No rule compares it yet; E-T1 and DEC-29 are P3-06's.
  - **Unverified, low, fixed:** tests for the IV coming from the exact mid, an option bar the stock tape lacks (a left join, so it is `NO_SPOT`), and the solver's bisection fallback (from three starts where Newton alone fails); DEC-23 now credits the 0.09% gap to JPM (DEC-06); this entry's reason for pricing puts directly. And DEC-26's missing-close rule, recorded as the PO's answer though it was never asked, is now put to the PO (DEC-26).
  - **Mutants:** the 14 the reviewers left alive, re-run on the fixed code, are all killed.

### DEC-90 — Strategy config: kinds, the loader and the config hash
**Status:** ENG · **Affects:** P3-01, P3-05, P3-06, P3-08, P4-03, P4-05, P5-02; DEC-44, DEC-52, DEC-53

- **Where:** `pmcc/config/`, one module per job:
  - `kinds.py`: the kind registry, `SPEC_RULE_IDS` (the spec tables' order) and `OPTIONAL_RULE_IDS`.
  - `extends.py`: the `extends` chain and `overrides`, over raw rules.
  - `rule_text.py`: placeholders and rendering (DEC-52).
  - `strategy.py`: `Rule`, `FillModel`, `StrategyConfig`, `RunConfig`, `load_strategy()`, `load_run_config()`.
  - `fields.py`: pydantic field types for dollars (`Price`, `Money`), an ET clock time and a rule ID.
- **Kinds:**
  - A kind implements exactly one spec rule ID. `nearest_delta_short` and `expected_move_strike` are both E-S3, so A2 swaps the kind under the same ID. A rule whose kind implements another ID is refused, and so is any ID outside the spec, since no kind implements one.
  - Each kind has a params model: strict (the string "0.3" and `true` aren't numbers), closed to unknown keys, and range-checked (deltas and spread limits in (0, 1), DTE ≥ 1, min ≤ max).
  - Money thresholds (G-5's $0.10, the fee) are held as `Price` and `Money` (DEC-44), written in YAML as a dollar number. They're strict like the rest: a string is refused unless it is the `"0.1000"` form they serialize to, and an amount not exact to $0.0001 is refused rather than rounded (a $0.00005 G-5 would round to $0 and never fire). A clock time (X-S3's 15:00) must be a quoted `"HH:MM"`: unquoted, YAML 1.1 reads `15:00` as the integer 900.
  - A params error names the rule and the param: `X-S2 params: max_delt: Extra inputs are not permitted`.
  - The params models live in `config`, because `config` can't import `strategy` (ARCHITECTURE §3.2). `strategy/registry.py` (P3-06) maps each kind to its code, and a test will hold the two key sets equal.
  - All 26 kinds are registered now, the quant ones included, since each is a params model and the spec fixes its rule. `quant_pmcc.yaml` uses them at P4-03; the fixed-bar trigger (DEC-31) joins at P5-02.
- **Required rules:** every spec rule except G-3, G-4, G-5 and X-S1, the layers the spec's strategies and ablations switch off. A strategy without any other rule fails at load. "Off" is absence (DEC-53).
- **The loader:**
  - A file extends at most one parent, by a relative path with forward slashes to a `.yaml` file, so a config means the same on every machine (DEC-58). An absolute path, a drive, a backslash or another suffix is refused; a missing file or a directory raises `FileNotFoundError` on both OSs. A cycle is refused.
  - A child adds rules the parent doesn't define. Redefining one is refused: it must use `overrides`, keyed by rule ID, with exactly one of `params` (a non-empty patch), `replace` (a whole rule, same ID; nothing is filled in from the old one) or `remove: true`. An override of a rule no parent defines, including one the same file defines, is refused.
  - `fill_model` is patched field by field. `id` and `name` are never inherited, so the file loaded names the strategy, and `_shared.yaml` alone isn't one.
  - Rules come out in the spec's order, whatever the files' order. A strategy's `rule_ids` are the valid stamps for its blotter and gate log (INV-09).
- **The fill model** (`spread_capture`, `fee_per_contract`) is in the strategy config, beside the rules, since the friction runs vary it (Spec › Sensitivity checks). It is not a rule, so it has no rule ID: a fill carries the ID of the decision that made it.
- **Rule text:**
  - A placeholder is a bare param name with an optional format spec. An attribute or index lookup, a conversion or a positional field is refused.
  - `rationale` is rendered like `condition` and `action`, so a threshold quoted in it (X-S3's 0.25 × EM) can't drift.
  - Every param must appear in the condition or the action; the rationale alone doesn't count.
- **The config hash:**
  - It covers `RunConfig`: the resolved strategy (id, name, fill model, each rule's kind, params and templates) plus the universe's window and r. It is the sha256 of `canonical_json()`: `model_dump(mode="json")` as JSON with sorted keys, no whitespace, non-ASCII kept, in UTF-8.
  - Only resolved content counts, so the same rules spread across `extends` or flattened into one file hash the same.
  - The symbol list is left out: the symbol is a run's input, recorded in its manifest, so every symbol run on one config shares a hash.
  - `starting_cash` joins at P3-09 (DEC-30). Report sections (DEC-54) join at P4-05.
- **JSON Schema:** each kind has its own params model, so `Rule.params` is described as what every dump holds, a map of names to numbers or strings, rather than as the empty base model pydantic would emit. P4-05 exports the schema.
- **Lint:** ruff's `allowed-confusables` adds `×` and `−` to `›`: the spec writes rule text with them (`spot ≥ short strike − 0.25 × EM`), and the YAML and its tests quote it.
- **For P5-02:** `configs/sensitivity.yaml` lists many variants in one file (ARCHITECTURE §10), and `load_strategy` resolves one strategy per file. P5-02 adds the entry point that folds each listed variant onto its parent.
- **Tests:** 286 new, 1144 in the suite: `tests/unit/config/test_baseline_config.py` (the shipped files, read against the spec's tables), `test_strategy_loader.py`, `test_rule_text.py` and `test_kinds.py`.
- **Outcome:** 2026-09-29 — P3-01's done-when holds: the config tests pass for unique IDs, resolving placeholders, referenced params, and every spec rule the baseline runs (all but G-3 to G-5).
  - 28 planted mutants were run: each refusal above, the spec order, the hash's coverage, strictness and ranges, and three changes to the shipped YAML. Three survived at first:
    - a check that a rule ID is in the spec, redundant with the kind check, so it was removed;
    - the model's duplicate-ID check, which the loader can't reach, now tested on the model itself, as a config read back from JSON would reach it;
    - cycle detection, which a depth limit also passed, now pinned to the chain it names.
  - All are now killed.
- **Outcome:** 2026-09-29 — an adversarial review of P3-01 (4 reviewers, 2 skeptics per finding): 40 findings, 27 unique. The 12 most severe were verified: 8 confirmed, 3 plausible, 1 refuted; 15 low ones went unverified. Every confirmed and plausible finding, and the unverified ones, is fixed:
  - **Confirmed, high:** the new files failed ruff with 16 errors: E501, RUF001/RUF002 (`×`, `−`), RUF043 and SIM905. `just check` stayed green because `pre-commit run --all-files` lints only tracked files, and these were untracked. Fixed, and the confusables allowed as above. Ruff and pyright now run clean over `pmcc` and `tests` directly.
  - **Confirmed, medium:** the E-S2 rationale was wrong about holiday weeks (DEC-35). Six test gaps, each now tested:
    - the hash's coverage of the fill model, window, id and name;
    - the fill model's strictness, extra keys and [0, 1] range;
    - `match="id"`, which matches any pydantic "valid"/"validation" message;
    - `match="X-S2|remove"`, which a both-operations override removing X-S1 would pass;
    - `replace` as a whole rule;
    - a dollar param rendered through `Rule.text()`.
  - **Plausible, medium:**
    - the JSON Schema typed params as an empty object (fixed as above);
    - names, conditions and actions weren't pinned to the spec, and the no-roll paragraph wasn't checked against the spec's words. Both are now read from the spec file (DEC-35).
  - **Refuted:** E-L4 lacks the starting-cash multiplier and rounding. That is DEC-30's, asked at P3-09.
  - **Unverified, low, fixed:**
    - `extends` took an absolute path, any suffix, or a directory, which raised a different error on each OS;
    - an empty `params` patch was accepted;
    - dollar params took any numeric string and rounded below $0.0001;
    - the canonical hash form, a parent-only override, override extra keys, min = max bands, frozen params and `ConfigError`'s file name weren't pinned;
    - rationale claims beyond the spec (DEC-35);
    - BUILD-PLAN §2 had no DEC-35 row;
    - ARCHITECTURE §16's new-kind steps and §10's "unreferenced placeholder" were stale;
    - the BUILD-PLAN tick miscounted the mutation fixes;
    - `sensitivity.yaml` needs a P5-02 entry point (noted above).
  - **Mutants:** 41 are killed: every survivor the reviewers reported, and 7 against the new checks. The first 28 still are, except the 2 whose code is gone.

### DEC-91 — MarketView, the synthetic market, accounting, fills, rules and the engine loop
**Status:** ENG, with three edge cases put to the PO (below) · **Affects:** P3-02 to P3-07, P3-08, P4-01, P4-02, P4-05; DEC-10, DEC-20 to DEC-23, DEC-27 to DEC-29, DEC-32, DEC-34, DEC-44, DEC-49

- **Where (ARCHITECTURE §3.1):**
  - `pmcc/strategy/`: `ports.py` (the `MarketView` protocol, `LookAheadError`, and the values rules return), `selectors.py` (E-L2/E-L3, E-S2/E-S3), `trigger.py` (E-T1), `gates.py` (E-S5, G-1, G-2), `exits.py` (X-S1 to X-S3, X-L1, X-L2, the X-S4/X-S5 resolver), `registry.py` (kinds → code, `build_strategy`).
  - `pmcc/engine/`: `market_view.py` (`MarketData`, `HistoricalView`), `fills.py`, `legs.py` (`Trader`: the leg state machines and the gate log), `loop.py` (`run_backtest`), `invariants.py`.
  - `pmcc/accounting/`: `events.py`, `book.py`, `marks.py`, `valuation.py` (new beside ARCHITECTURE's list, so NAV has one home), `regt.py`, `ledger.py`.
  - `pmcc/domain/errors.py`: `EngineError`, so accounting can raise it without importing the engine (ARCHITECTURE §3.3 rule 4).
- **MarketView (P3-02):**
  - Every accessor takes an optional `at` (default `now`) and goes through one `_as_of` gate, so the done-when's "every accessor raises for t > now" is literal, and a rule can read an earlier bar. It adds `stock_quote()` (the X-S5 cover and stock marks, DEC-28, DEC-23) and `root` (to name contracts).
  - `MarketData.build` takes the loader's frames, not `SymbolData`, so `engine` doesn't import `data`. It prices the symbol once (`price_symbol`), indexes each contract's first valid session quote for DEC-32's listing, and memoizes each listed snapshot, so every run over a symbol shares it.
  - `PricedQuotes` gains the integer `bid`, `ask` and `valid` columns and `quote(row)`, so `quote()` returns the exact quote the fill uses, not a float mid. The IV is still solved from the exact float mid (DEC-89).
  - An expiry is listed once one of its calls is. `expiries(WEEKLY)` includes the third Fridays, since a monthly expiry is also its week's final session.
- **The synthetic market (P3-03, TEST-STRATEGY §5):** `tests/fixtures/synthetic/market.py` writes a symbol through `SymbolCache.write_unit`, so `load_symbol` reads it as it reads LSEG's. It uses the shipped calendar, and spot is a seeded walk or scripted knots. Quotes are Black-Scholes from an IV surface, rounded out to cents, with hooks for holes, wide spreads and missing rows. `scenarios.py` holds 19 builder functions (25 entries in `BUILDERS`, counting variants such as the delayed X-S3 fill), and the session-scoped `synthetic` fixture (`store.py`) generates each market once per test run. `extended_hours` also writes a pre-market and a post-close bar each session, so a test can check that no read comes from them.
  - **Found while tuning:** at one IV for both legs, the baseline's E-S5 fails every week. A 0.80-delta 180-DTE long carries more extrinsic than a 0.30-delta weekly's out-of-the-money distance plus its premium: at 30% IV, a $17 gap against a $17.90 debit. The scenario markets therefore price monthlies at 20% and weeklies at 40%. Real data may show many G-2 weeks; P3-10 will tell.
- **Accounting (P3-04):**
  - An `Event` checks its own Cash Δ against its fill, quantity and fee when it's made. `EXPIRE` fills at $0 and `ASSIGN` has no fill; both have no cash and no fee. The fee is per option contract, so stock rows have none.
  - `Book.apply` is the only mutator. It refuses a flip (a sale bigger than the long), an expiry or assignment off the expiry day, puts, and any book leaving a short uncovered (strike, expiry, quantity) or unequal to the long (INV-05, INV-10), raising `EngineError`.
  - Reg T follows the spec and the PO's DEC-10 answer. A requirement that isn't a whole $0.0001 is rounded up. `funds_after(book, marks, event)` values the book after an entry, with the new leg marked at its limit: it is E-L4's check, and the audit's `funds_after` (INV-08).
- **Fills (P3-05):** mid ± capture × half-spread, worked out exactly (the capture read as its decimal) and rounded half-even once. So capture 0 fills at exactly `Quote.mid`, the Limit column. The audit carries BID, ASK and the capture, so `pmcc verify` can re-derive the fill.
- **Rules (P3-06):**
  - E-T1 compares (ASK − BID) ≤ limit × mid exactly; a spread on the limit passes.
  - The DEC-29 ties are exact. A delta distance is rounded to 9 places, since 0.85 and 0.75 aren't equally far from 0.80 in binary floating point (DEC-29).
  - X-S1 runs until X-S3's check time, read from X-S3's params, so moving the check moves both. X-S3 fires on spot alone; only its fill needs a quote (DEC-28).
  - The registry maps all 26 kinds. The quant kinds raise `NotBuiltError` naming P4-01 or P4-02 until then, and E-L1, E-S1, E-S4, X-S4, X-S5 and X-E1 are markers the loop enforces.
  - E-T1 is a port, `EntryTrigger` (`can_decide`, `check`), not the concrete `SpreadTrigger`, so DEC-31's fixed-bar trigger swaps in by kind (DEC-31).
- **The engine (P3-07):**
  - `run_backtest(data, run_config, strategy, starting_cash)` walks the window's session bars in DEC-20's order and returns the blotter, the ledger (one row per bar) and the gate log. Starting cash is an argument until P3-09 settles it (DEC-30).
  - A long bought on a week-open session needs no reset check, so the short can be sold on the same bar, in DEC-20's order. At most one short is sold per week: a short closed early isn't replaced until the next week-open session (Spec › X-S1, X-S2).
  - The runtime invariants run on every event and bar (ARCHITECTURE §8.4). A failure logs `invariant.failed` and raises `InvariantViolation`, an `EngineError`.
  - A new log event, `engine.exit.unevaluated`, records a rule that couldn't evaluate, with the rule, the contract and the IV code (DEC-27).
  - Entry rows carry DEC-34's values: the selection's (with `selected_at`), the decision bar's E-T1 spread, and the short's E-S5 terms.
  - An unfinished reset's gate-log row says why: the re-entry didn't pass E-T1, E-L4 blocked it, or no long was selected.
  - A chain lists every listed contract, including one with no row on the bar (no quote, `NO_QUOTE`), so a listed ATM strike without a quote makes EM unavailable rather than silently moving to its neighbour (DEC-25, DEC-32).
- **Put to the PO at handover (2026-09-30):** three edge cases the answers so far don't settle. They're built as recommended here, and each is a one-line change if the PO decides otherwise:
  1. **X-S3 without an EM at entry** (the ATM put or call had no quote on the short's entry bar): X-S3 can't evaluate, so it doesn't fire and it's logged, as the PO's DEC-27 answer does for a missing delta. X-S4/X-S5 still resolve the short at the close.
  2. **A short entry that would leave available funds negative** (possible after an X-S5 loss): no short that week, and the gate log's outcome is `E-L4`, noted "available funds would go negative" (INV-08; Spec › E-L4 "no entry (logged)").
  3. **The stock's first mark after X-S5** when the stock has no valid quote on the assignment bar: the closing spot, flagged stale, until its next valid mid.
- **Tests:** 259 new, 1,403 in the suite, after the review below: `tests/property/test_market_view.py` (INV-04), `tests/unit/engine/` (views, fills, invariants), `tests/unit/fixtures/`, `tests/property/test_accounting_invariants.py` (INV-01, 02, 08, 10), `tests/unit/accounting/`, `tests/unit/strategy/` (every rule at its boundaries, on the stub view `tests/fakes/view.py`), and `tests/scenario/` (42 full runs).
- **Outcome:** 2026-09-30 — P3-02 to P3-07's done-when lines hold; `just check` is green, and pre-commit passes on the new files.
  - **P3-02:** every accessor raises for a time after `now`. A hypothesis test finds no answer that depends on data after `now` (a view over the whole market against one cut off at `now`). Unlisted strikes and expiries stay hidden.
  - **P3-03:** the same seed writes byte-identical files, and each builder has a smoke test.
  - **P3-04:** the property tests for INV-01, 02, 08 and 10 pass over random fills, expiries, assignments, covers and stale marks (every path is reached: 14% of examples assign). An uncovered short raises `EngineError`.
  - **P3-05:** INV-03 holds, fills at capture 0, 0.25 and 0.50 are exact in `Price` units, and the fee applies per contract.
  - **P3-06:** every rule has boundary tests.
  - **P3-07:** every baseline scenario passes, with the runtime INV-01 to INV-10 checked on every bar. G-3, G-4 and G-5 have their market builders now, but their engine scenarios wait for their code (P4-02's done-when now names them).
- **Outcome:** 2026-09-30 — an adversarial review of P3-02 to P3-07 (4 reviewers, 2 skeptics per finding): 34 findings, 19 unique. The 12 most severe were verified: 11 confirmed, 1 plausible, 0 refuted; 7 low ones went unverified. Every one is fixed, with regression tests:
  - **Confirmed, high:** entry notes broke DEC-34. They carried the freeze bar's mid and spread (40% on a short that filled at 5.4%) and no E-T1 spread or E-S5 terms, and the short's audit had no `e_t1_spread`. Fixed as above.
  - **Confirmed, medium:**
    - Nothing tested DEC-21's freezes or DEC-28's check-once: re-selecting the long or the short every bar, or checking the long on every week-open bar, passed the suite. New scenarios move spot after the freeze (`short_frozen_then_rally`, `long_frozen_then_rally`) and after the check (`long_falls_after_check`).
    - Nothing tested the short's E-L4 skip, the stale stock mark or the unfinished-reset row. Each now has a scenario (`surge_no_stock_quote`, `reset_reentry_wide`, `long_delta_drop` with little cash).
    - The G-3 to G-5 engine scenarios were deferred to P4-02, but P4-02's done-when didn't say so. It does now.
    - E-T1 was typed as the concrete `SpreadTrigger`, so DEC-31's fixed-bar trigger couldn't swap in by kind. It's a port now (above).
  - **Confirmed, low:**
    - `exit_pending` stayed on the bar where X-S4/X-S5 resolved the short. The flag now comes from the bar's end state only.
    - `engine.exit.unevaluated` lacked the contract and the IV code.
    - An unfinished reset was always noted "didn't pass E-T1", even when E-L4 blocked the re-entry.
    - DEC-23 cited `pmcc/engine/marks.py`, which doesn't exist.
    - The builder count matched neither the functions nor `BUILDERS`.
    - Two scenario assertions couldn't fail: a NAV check that reduced to nav == nav, and a date-only INV-07 check.
  - **Plausible, medium:** a listed strike with no row on a bar dropped out of the chain, which DEC-32 says can't happen, so the ATM strike and EM could shift to a neighbour (81 listed NVDA contract-bars have no row). Fixed as above.
  - **Unverified, low, fixed:**
    - nothing tested that MarketView reads session bars only (`extended_hours` markets now do);
    - the runtime INV-03 check was never failed for stock rows, zero bids or a wrong Limit;
    - `close_trades` values were never checked;
    - DEC-20's cover-before-check order and X-L1 over X-L2 on the same bar were untested;
    - TEST-STRATEGY §5 had X-L2's `min_dte` the wrong way round;
    - PRD FR-R2 still said the gates stop at the first fire.
  - **Mutants:** the reviewers' surviving mutants (both freezes, the check-once, the reset row, the session-bar filter) now fail. One survives because it's equivalent: seeding the stock's first mark as fresh instead of stale, which the same bar's carry-forward marks stale anyway.

### DEC-92 — Results: the models, canonical JSON, the manifest and `pmcc run`
**Status:** ENG · **Affects:** P3-08, P3-09, P3-10, P4-05, P4-06, P5-03; DEC-30, DEC-49, DEC-50

- **Where (ARCHITECTURE §3.1):**
  - `pmcc/export/`: `canonical.py` (canonical JSON, `drop_run_timestamp`), `models.py` (the pydantic result models), `manifest.py` (git, lockfile and version provenance), `results.py` (`write_result`).
  - `pmcc/runner.py` (new, beside `cli.py`): `run_symbol` loads a cache, runs the engine and builds the `RunResult`. It needs `data`, `engine` and `export`, and `export` must not depend on the engine or the data layer (§3.2), so it sits above them. `pmcc calibrate` and `pmcc batch` reuse its `run_loaded`.
- **The result file (provisional until P4-05):** `results/{SYM}/{run_id}.json` holds `schema_version` (1), `manifest`, `config` (the resolved `RunConfig`, dumped exactly as its hash covers it), `rule_text` (each rule's rendered condition, action and rationale), `starting_cash`, `blotter`, `ledger` and `gate_log`. The summary, cycles and attribution join at P4-05 and P6, with the JSON Schema.
  - An instrument is `{ric, occ, kind, expiry, strike}`. `ric` is the RIC the cache answered with (the expired `^` form for a contract fetched after expiry), read from the chain frames, so a blotter row leads straight to its raw quotes (TEST-STRATEGY §8). The stock is its tape's RIC, with `occ`, `expiry` and `strike` null.
  - The blotter's audit and the gate log's values pass through as the engine records them; the audit's `bid`, `ask` and `funds_after` stay in $0.0001 units (DEC-91), which `pmcc verify` reads.
  - `run_id` is the config's `id`; `strategy_id` is the part before `--` (`quant_pmcc--a3` → `quant_pmcc`).
- **Canonical JSON (DEC-50):**
  - One line, no whitespace, sorted keys, UTF-8 with non-ASCII kept, one final newline.
  - Result dollars are `Decimal` and print as 4-dp JSON numbers (`1234.5000`); the config section keeps its own dump, dollars as `"0.1000"` strings, because that is what `config_hash` covers.
  - Other floats round to 6 dp and print by shortest repr. NaN and infinities print as `null`, −0.0 as `0.0`, and a naive time is refused.
  - Arrays come only from lists and tuples, so `bytes` or a set is refused rather than printed as numbers.
  - `loads` keeps each number's text, so reading a canonical file and dumping it again gives back its bytes, and `drop_run_timestamp` is exact.
- **Provenance:** git runs read-only (`rev-parse`, `status --porcelain` with `--no-optional-locks`), with `results/` excluded by pathspec (DEC-59). `lock_hash` is the sha256 of `uv.lock`, which is LF on every OS; `pmcc_version` is the installed package's. No git, no commit, or no lockfile fails the run before anything is written.
- **`pmcc run --symbol S --config C [--universe U] [--cache data_cache] [--out results]`:**
  - `data_source` is `lseg`: the runner's caller says where the data came from, since a synthetic cache looks the same on disk. Tests and P4's sample site pass `synthetic`.
  - `run_timestamp` is the start of the run, in ET.
  - A re-run replaces its file whole (`replace_file`). A cache, calendar, provenance or engine error, a failed invariant included, exits 1 with nothing written (DEC-49), and a bad config path or YAML exits 1 naming the file.
  - It prints the trade, bar and week counts, the final NAV and the path, and says to commit first when the tree is dirty. Log events: `run.done` and `run.abort`.
- **`Universe.starting_cash`:** optional (`DollarMoney | None`) until P3-09 writes it with its basis (DEC-30). It isn't in `config_hash`, which covers the strategy, the window and r (DEC-90); the result records it as `starting_cash`.
- **The large-file hook:** a 26-week full result is about 0.5 MB (575 bytes per ledger bar on the synthetic market; NVDA's window has 875 bars), at pre-commit's default 500 KB `check-added-large-files` limit, which would stop the PO's P3-10 commit. `results/` now has its own 2 MB limit; every other path keeps 500 KB. Checked in a throwaway repository: a 1 MB result passes, a 3 MB result and a 600 KB file elsewhere fail.
- **Tests (78 new, 1,481 in the suite):**
  - `tests/unit/export/`: canonical JSON, including a hypothesis round trip, and provenance on a throwaway git repository (`tests/fakes/git_repo.py`). It lives in pytest's temporary directory, with the global and system git config shut out; the project's repository is only read.
  - `tests/scenario/test_run_result.py`: every blotter, ledger and gate-log row mirrors the engine's; RICs; the manifest; the file's config hashes to its `config_hash`; a dirty tree records `git_dirty: true`.
  - INV-13: `random_walk` cached once, then run by `tests/scenario/inv13_run.py` in two fresh processes with `PYTHONHASHSEED` 1 and 2 and different run timestamps. The files differ, and are byte-identical once `run_timestamp` is dropped, so no set or dict order leaks into a result.
  - `tests/unit/test_cli_run.py`: `pmcc run` end to end on the synthetic cache, the P3-09 stop, a dirty tree, an engine error and a bad config writing nothing.
- **Outcome:** 2026-09-30 — P3-08's done-when holds: INV-13 passes on synthetic data, and a dirty tree records `git_dirty: true`.

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
