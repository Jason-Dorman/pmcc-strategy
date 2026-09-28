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
| DEC-06 | Bar timestamps, decision time, session bars | VERIFY: probed, report at P1-05 | P1-04 |
| DEC-07 | Backtest window | VERIFY: probed → PO confirms | P1-04, P1-05 |
| DEC-08 | Long-dated coverage | VERIFY: probed; full measure at P1-09 | P1-04, P1-09 |
| DEC-09 | Live-contract RIC form | VERIFY: probed, report at P1-05 | P1-04 |
| DEC-10 | Reg T and FINRA 4210 citations | VERIFY | by P7-04 |
| DEC-11 | Risk-free rate | VERIFY → PO picks | P1-05 |
| DEC-12 | Per-symbol identifiers, splits, max strike | VERIFY: probed, report at P1-05 | P1-04 |
| DEC-13 | Hourly field availability | VERIFY: probed, report at P1-05 | P1-04 |
| DEC-14 | Strike increments | ENG method · VERIFY values: probed | P1-04 |
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
| DEC-33 | Expiry calendar | SETTLED (PO) | — |
| DEC-34 | Rule stamping for multi-rule events | ASK | P3-07 |
| DEC-40 | Source of truth | SETTLED (PO) | — |
| DEC-41 | Frontend stack follows the spec | SETTLED (spec) | — |
| DEC-42 | Python environment | ENG | — |
| DEC-43 | Packages added to the spec layout | ENG | — |
| DEC-44 | Money as integer units | ENG | — |
| DEC-45 | RIC form policy | SETTLED (PO) | — |
| DEC-46 | Cache layout | ASK | P1-07 |
| DEC-47 | Fetch dates are inclusive | ENG · probed (LSEG's date edges) | — |
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
| DEC-83 | History port, LSEG adapter and batched requests | ENG · error codes verified | — |
| DEC-84 | Calendar, chain discovery and the fetch plan | ENG | — |
| DEC-85 | Probe design | ENG | — |

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
- **Outcome:** 2026-09-27 — probed on all 12 symbols over the last 5 sessions, Sep 21–25 2026. Daily bars came back for Sep 22–25 only (DEC-47), so 48 sessions were compared. Reports are in `data_cache/probes/` (DEC-85).
  1. **Bars are stamped at their start.** Every option's hourly bars start 09:00–16:00 ET, and every Nasdaq stock's (`.O`) start 04:00–19:00. That is the 09:30–16:00 option session plus a stub, and the 04:00–20:00 extended stock session. End stamps would read 10:00–17:00 and 05:00–20:00.
  2. **Quotes are end-of-bar values.** The daily closing BID/ASK equals the final quote of the bar starting 16:00 in 48 of 48 sessions, because the day's last quote comes at or after 16:00. For single-stock options it also equals the final quote of the bar starting 15:00 in 16 of 28 sessions (AMD 4/4, NVDA 3, TSLA 3, JPM 3, AAPL 2, COIN 1, META 0), which a start-of-bar value couldn't. ETF options (SPY, QQQ, IWM, TLT, XLE) trade until 16:15, so their closing quote always falls in the stub (0 of 20 in the 15:00 bar).
  3. **Check 1 fails as written: the official close is not the close bar's last trade.** The daily TRDPRC_1, the closing auction, equals the last trade of the bar starting 15:00 in only 9 of 48 sessions. The two differ by up to 0.09% (JPM), most by under 0.03%. Points 1 and 2 still prove start stamps and end-of-bar quotes.
- **For the PO at P1-05:** the recommendation stands: `bar_end = bar_start + 1h`, decisions at `bar_end`, session bars ending 10:00–16:00 (13:00 on a half-day), and the 16:00 stub kept for provenance only. Point 3 also goes to DEC-23 (closing spot, ITM at expiry): the close bar's last trade sat up to $0.40 from the official close (META; AMD $0.33, JPM $0.31, TSLA $0.27), and that close decides exercise.
- The probe used the first stock suffix that answered (DEC-85). For SPY, IWM and XLE that was the NYSE venue (`.N`, bars 07:00–16:00), not their Arca primary (`.P`), so their stock-side spans are that venue's.

### DEC-07 — Backtest window
**Status:** VERIFY → PO confirms · **Verify at:** P1-04 · **Confirm at:** P1-05 · **Affects:** `configs/universe.yaml`, fetch plan

- **Spec:** one window for all symbols, as long as hourly option history allows and at least 10 weeks.
- **Recommendation:**
  - Probe how far back hourly BID/ASK goes, per symbol, for expired near-the-money weeklies and for live long-dated calls.
  - **Start:** the first week-open session by which all 12 symbols have data.
  - **End:** the final session of the last complete week before the universe fetch begins.
  - Fix both in `universe.yaml` before the first published run.
- **Outcome:** start —, end —, weeks —. (The PO sets these at P1-05.)
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

### DEC-08 — Long-dated coverage
**Status:** VERIFY · **Verify at:** P1-04, P1-09 · **Affects:** E-L3 candidate sets, Methodology

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

### DEC-09 — Live-contract RICs
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** P1-02, P1-03

- Long legs still listed at fetch time must resolve in the live form (no caret). LDG §4.13 and §6.3 say they do. Confirm on 3 symbols.
- **Outcome:** 2026-09-27 — confirmed on all 12 symbols:
  - Every live monthly the coverage check asked (75 contracts) answered in the live form, the only form asked.
  - A live contract asked in the caret form never answered: `TS.Intraday.UserRequestError.90001`, 12 of 12.
  - Weeklies expired 9 days earlier answered in the caret form, 12 of 12 (DEC-14's check).

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

### DEC-13 — Hourly field availability
**Status:** VERIFY · **Verify at:** P1-04 · **Affects:** fetch field lists

- A field the RIC doesn't carry raises `LDError` for the whole request (LDG §4.6).
- **Probe:** each field from Spec › Fields and bars, paired with TRDPRC_1, on hourly option and stock RICs.
- **Fetch and records:**
  - The fetch requests only the fields that exist.
  - Dropped fields are recorded in each unit's sidecar and on the Methodology page.
  - The stock also needs BID/ASK, for the stock fills after X-S5.
- **Outcome:** 2026-09-27 — for all 12 symbols, hourly bars carry all 8 fields, on the options and on the stock (for SPY, IWM and XLE, on the NYSE venue's `.N`, not the Arca primary DEC-12 recommends, which wasn't field-probed), each asked paired with TRDPRC_1: BID, ASK, TRDPRC_1, OPEN_PRC, HIGH_1, LOW_1, ACVOL_UNS, NUM_MOVES. The fetch can ask for all of them; no field is dropped. LSEG doesn't refuse a field a RIC lacks, it leaves it out of the answer (DEC-83). So a unit's sidecar should record the fields asked and the fields that came back (P1-07).

### DEC-14 — Strike increments
**Status:** ENG (method) · VERIFY (values) · **Verify at:** P1-04 · **Affects:** P1-06

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
