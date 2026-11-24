# Decisions — Live Wheel and Volatility Thesis

Nov 13, 2026 · companion to the [Live spec](LIVE-SPEC.md), the source of truth for the live assignment. Since Nov 21 also the [Thesis spec](THESIS-SPEC.md)'s log, in its own part at the end: [Volatility thesis (`TD-nn`)](#volatility-thesis-td-nn)

The user is the product owner (PO). This log tracks what the spec leaves open, the PO's answers, and engineering choices. It starts fresh for the live assignment; the PMCC's log (`DEC-nn`) and the wheel's (`WD-nn`) are archived in [archive/pmcc/DECISIONS.md](archive/pmcc/DECISIONS.md) and [archive/wheel/DECISIONS.md](archive/wheel/DECISIONS.md) and decide nothing here (LD-01). Entries are `LD-nn` for the live wheel and `TD-nn` for the thesis (TD-11), so they never collide with a citation in the older code.

| Status | Meaning |
| --- | --- |
| `ASK` | Open question, with a recommendation. Asked when the backlog item under **Ask at** starts; nothing that depends on it is built before the answer. |
| `SETTLED` | Decided. **Basis** is a dated PO answer. |
| `ENG` | An engineering choice: how, not what. Recorded so the PO can see it and overrule it. It becomes `ASK` if it turns out to change behaviour, results, scope or the UI. |

**Maintenance:** record each answer under **Outcome** with the date; if it changes the spec, update the spec in the same commit, citing the entry. Never delete an entry; a new one takes the next free number.

## Index

| ID | Decision | Status | Ask at |
| --- | --- | --- | --- |
| LD-01 | Wheel docs archived; the live assignment's docs | SETTLED (PO) | — |
| LD-02 | Due date | SETTLED (PO): Tue Nov 17 2026, 11:59 pm ET | — |
| LD-03 | The algorithm: the wheel, live, on NVDA | SETTLED (PO) | — |
| LD-04 | `open_orders.json` at the root and under `mkt/` | SETTLED (PO): both, 2026-11-14 | — |
| LD-05 | The nightly job contacts LSEG | SETTLED (PO) | — |
| LD-06 | The bot commits; the site deploys after each nightly run | SETTLED (PO) | — |
| LD-07 | Limit at mid, at the open | SETTLED (PO) | — |
| LD-08 | One order a week; an unfilled week is skipped | SETTLED (PO) | — |
| LD-09 | Starting cash: $25,000, ours to track | SETTLED (PO) | — |
| LD-10 | The page's contents | SETTLED (PO) | — |
| LD-11 | How a strike is chosen | SETTLED (PO): from LSEG's chain, by us | — |
| LD-12 | NVDA in the course's prices, and its conid | SETTLED (PO): NVDA added to `price_history.json` | — |
| LD-13 | Risk-free rate for delta | SETTLED (PO): DGS3MO, 4.32% on 2026-11-12 | — |
| LD-14 | A stale or unreadable book, or a bad order in the file | SETTLED (PO): stop and fail | — |
| LD-15 | LSEG data on the page | SETTLED (PO): not restricted; the pick's quote shown | — |
| LD-16 | The page's route and nav name | SETTLED (PO): `#/live/NVDA`, "Live" | — |
| LD-17 | Sanji's files are exempt from the formatting hooks | ENG | — |
| LD-18 | ID prefixes | ENG | — |
| LD-19 | What `open_orders.json` holds; order ids | SETTLED (PO): an order stays until its week ends | — |
| LD-20 | Code layout | ENG | — |
| LD-21 | The headless session and the close snapshot (L1-02) | ENG | — |
| LD-22 | Reading the order language strictly (L2-01) | ENG | — |
| LD-23 | Earnings weeks | SETTLED (PO): traded like any other | — |
| LD-24 | The night's run: book, rules, file and log (L2-02, L2-03) | ENG | — |
| LD-25 | Every night that plans a week's first session places its order | SETTLED (PO) | — |
| LD-26 | The live picks read the close snapshot, not a MarketView | SETTLED (PO) | — |
| LD-27 | The nightly workflow (L3-01) | ENG | — |
| LD-28 | The live page's data and layout (L4-01) | ENG | — |
| LD-29 | A put's strike goes as its percent from the close, which Sanji applies to the open | SETTLED (PO): `pct:` in whole percents for puts, a number for calls; cash covers a 10% gap | — |
| LD-30 | A blotter of Sanji's fills | SETTLED (PO): at L5-01 | — |
| LD-31 | A late nightly run still plans the next session | SETTLED (PO): a run before the open plans that day; cron `17 3 * * *` | — |
| LD-32 | A stale price file is a warning while Sanji has written no book | SETTLED (PO): warn, don't stop, until positions or fills exist | — |
| LD-33 | A volatility workflow and its charts: IV against RV20, and the smile | SETTLED (PO): its own workflow, a 3-month backfill, drawn on the site | — |
| LD-34 | The volatility workflow's files, pulls and schedule (L4-02) | ENG | — |
| LD-35 | The open orders show the strike LSEG gave the run beside the one sent | SETTLED (PO): on the page only; the order Sanji gets is unchanged (LD-29); the rule table moves to the page's end | — |
| LD-36 | The site's name, home page and menus | SETTLED (PO): "Algo Trading Strategies"; a card per strategy at `#/`, live first; a menu per strategy; no symbol picker or ident line; Universe and Data off the menus; a strategy label on each page | — |
| LD-37 | The home page's look: modern, less text, a moving background | SETTLED (PO): tiles, no charts; a big headline and big figures; a drifting background; a modern break from the terminal look, home only | — |
| LD-38 | The site calls the live wheel "Wheel forward test"; its home tile tells the week's trade | SETTLED (PO): "Wheel forward test", its page "Overview"; the tile reads "Selling a $155 put" with its delta, IV and expiry | — |
| LD-39 | The smile chart is named a skew | SETTLED (PO): "This week's skew", the data unchanged, the caption saying why | — |
| LD-40 | The algorithm's and the skew's copy, the PO's own | SETTLED (PO): the PO's text, with five accuracy fixes | — |
| LD-41 | The skew shows the market's expected move, from the ATM straddle | SETTLED (PO): the straddle's price either side of the close, a band on the skew and a line under it | — |
| LD-42 | The site doesn't name Sanji | SETTLED (PO): "the course's order system" on the page, in the rule texts and in the run's reasons | — |
| LD-43 | The skew marks the open order's strike, not tonight's pick | SETTLED (PO): the order's strike, labelled "Order", placed against the close and the expected move | — |

## Settled

### LD-01 — Wheel docs archived; the live assignment's docs
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** all docs; CLAUDE.md; README

- The wheel is finished (PO). Its spec, plan and decisions move to `docs/archive/wheel/`, with a copy of the UI spec as it stood; W4-01, W5-01 and W5-02 are closed there. Its code, configs, results and pages stay live and unchanged.
- The live assignment gets its own spec (`docs/LIVE-SPEC.md`), decisions (this file) and build plan (`docs/BUILD-PLAN.md`); `docs/UI-SPEC.md` stays the site's styling doc and takes the new page.

### LD-02 — Due date
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- Due Tue Nov 17 2026, 11:59 pm ET; submit target 18:00. The professor wants an `open_orders.json` he can see by Monday or Tuesday (class of Nov 10), so the first order is for Mon Nov 16's session.

### LD-03 — The algorithm: the wheel, live, on NVDA
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** Spec › Scope, Why the wheel, Trade rules

- The wheel as backtested (archived spec, `W-` rules), adapted to live orders: one contract, sell a 0.30-delta put at the start of a week in Cash, a 0.30-delta call at or above the cost basis in Shares, hold to expiry. Its backtest is the "why".
- Rule IDs are new (`L-…`, LD-18), because the live rules differ: a decision is made once, at the night before the session, from the close, and Sanji settles expiries and assignments.

### LD-04 — `open_orders.json` at the root and under `mkt/`
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- **Asked:** the assignment says the repo root; the order language page says `mkt/open_orders.json`.
- **Outcome:** the root. Sanji already writes `price_history.json` at our root (commits since Nov 5).
- **Amended 2026-11-14 (PO):** the professor's current order page puts `open_orders.json`, `positions.json` and `fills.json` under `mkt/`, while the assignment says the root. The run writes the same `open_orders.json` at both, and looks for Sanji's files under `mkt/` first, then at the root. (Recommended. The alternatives were the root only, or `mkt/` only.)

### LD-05 — The nightly job contacts LSEG
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** CLAUDE.md › Hard rules; Spec › Nightly job, Data

- The old rule (only `pmcc fetch` and `pmcc probe` contact LSEG; CI never does) is lifted for this assignment's new requirements (PO). The nightly job, and the PO running the same command locally, may contact LSEG. Tests, the CI checks and builds, and the site still never do.
- **Session:** a platform session (app key, username and password: the "EDP API" app key shown in class), not Workspace. The credentials are the repo's GitHub secrets `LSEG_APP_KEY`, `LSEG_USERNAME` and `LSEG_PASSWORD`, already set (PO); locally, the same names as environment variables. `lseg.data` is still imported only under `pmcc/data/lseg/`, and only that package reads the credentials.

### LD-06 — The bot commits; the site deploys after each nightly run
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** CLAUDE.md › Hard rules; Spec › Nightly job

- The PO still makes every other commit. The nightly job's Actions bot may commit only `open_orders.json` and the run log; it pulls before pushing.
- A commit made with the Actions token starts no other workflow, so CI also runs when the nightly job completes (`workflow_run`), and deploys from `main` then as on a push. Without it the site would wait for Sanji's next push.

### LD-07 — Limit at mid, at the open
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- `order_type` `lmt`, `lmt_prc` `mid`, `ref` `open`: the backtest's fill model (the mid). A market order, filled at the open, was the alternative.

### LD-08 — One order a week; an unfilled week is skipped
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- As in the backtest: an option is sold only for the week's first session. If that order doesn't fill, the week is skipped; no retry on a later session. Nights with nothing pending write `[]`.

### LD-09 — Starting cash: $25,000, ours to track
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- Sanji doesn't start our book with cash (PO) and doesn't check buying power, so the cash-secured check is ours: cash is $25,000, as in the backtest, plus the cash flows in Sanji's fills.

### LD-10 — The page's contents
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- One new page: the algorithm and why it was chosen; tonight's `open_orders.json`; Sanji's positions and fills; the nightly run log. Not an explanation of the pipeline.

### LD-11 — How a strike is chosen
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** Spec › Data, L-P3, L-C3, L-O1; L1-02, L2-03

- **Asked:** pull NVDA's chain from LSEG and compute the strike ourselves, or let Sanji pick with a token? Robin, the professor's database, isn't offered to students (class of Nov 10: he offered whitelisting, then chose each student's own headless LSEG access instead); the order page says Sanji rejects `delta:` tokens until Robin has chain snapshots; and no token says "at or above the cost basis".
- **Outcome:** the nightly job pulls NVDA's chain for the week from LSEG with the PO's headless (platform) credentials, which the PO has already used without Workspace running; it computes each strike's delta at the close with the backtests' pricer, and writes the chosen strike as a number and the expiry as a date. Sanji then only resolves a named contract. (Recommended. The alternatives were `"strike": "delta:30"` or `otm:N`.)
- **Amended for puts by LD-29** (PO, 2026-11-16): a put's strike goes as its percent from the close, which Sanji applies to the open; a call's stays a number.

### LD-12 — NVDA in the course's prices, and its conid
**Status:** SETTLED · **Basis:** PO, 2026-11-14 · **Affects:** Spec › The course's side; `price_history.json`; CLAUDE.md › Sources of truth

- **Context:** every order names its underlying by IBKR conid, "copied from `price_history.json`", and that file tracked only SPY (756733). The course's repo (read 2026-11-14) shows how instruments get there: the 16:00 ET price job reads each student's `price_history.json`, fetches every entry with `"tracked": true` (30 days back for a new one), and writes it back; a missing file is seeded with one of six (AAPL, NVDA 4815747, MSFT, GOOGL, SPY, AMZN), and ours drew SPY. Its `SETUP.md`: "the student edits price_history.json".
- **Conid:** NVDA's is **4815747** (Interactive Brokers' product list, and the price job's own seed list).
- **Outcome:** NVDA is added to our `price_history.json` as `{"tracked": true, "name": "NVIDIA CORP", "price_history": {}}`, beside SPY, in the job's own format (`json.dumps(indent=2)`, no final newline). Its bars start with the job's next run. (Recommended. The alternatives were to switch to SPY, or ask the professor first.) This is the one edit we make to a Sanji file, as the course provides for.
- **The test orders:** placed 2026-11-13 (buys at $1 and $0.01, for Nov 13 and Nov 16), then removed 2026-11-14 (PO): the order page says "Sanji does not resolve these orders yet", so they could tell us nothing. Both order files are `[]` until the nightly run's first order. (Recommended. The alternative was to keep them.)

### LD-13 — Risk-free rate for delta
**Status:** SETTLED · **Basis:** PO, 2026-11-14 · **Affects:** Spec › Data; `configs/live.yaml`

- **Context:** the backtests used 3.71%, from the 3-month Treasury yield before Mar 30. It moves the 0.30-delta pick only at the margin.
- **Outcome:** FRED DGS3MO, the latest when the rules were built: **4.32% on 2026-11-12** (the page, updated Nov 13; Nov 11 has no value). Converted as the backtests' rate was (a bill's investment yield over 91 days to a continuous rate): **4.297%**. Fixed in `configs/live.yaml` with its date and source. (Recommended. The alternative was 3.71%.)

### LD-14 — A stale or unreadable book, or a bad order in the file
**Status:** SETTLED · **Basis:** PO, 2026-11-14 · **Affects:** L-B1, L-B2; Spec › Trade rules, Nightly job

- **Outcome:** if Sanji's prices don't reach the last completed session (L-B1), its book doesn't map to one of the four states (L-B2), or an order already in `open_orders.json` (ours or placed by hand) fails the order language's checks (LD-22), the run writes no new order, logs a failed row with the rule and why, and fails so it shows red in Actions. (Recommended. The alternative was to assume the last state logged, and drop a bad hand-placed order with a warning.) Amended for L-B1 (PO, LD-32): while Sanji has written no book, stale prices are a warning, not a stop.
- **Asked 2026-11-14** (the L2-01 code review): what a bad order already in the file does to the run was first recorded under LD-22 as an engineering choice; it decides run behaviour, so it was asked here.

### LD-19 — What `open_orders.json` holds; order ids
**Status:** SETTLED · **Basis:** PO, 2026-11-14 (first recorded as ENG, 2026-11-13) · **Affects:** Spec › Orders

- **Asked:** weekly selling places one order a week, for Monday; dropping it once Monday was priced (the first rule) would leave the file `[]` on Tuesday, the due date.
- **Outcome:** each order already in the file stays until the week it's for has ended (the week's last session is before the session planned tonight), then drops; a wheel order (id `wheel-…`) for the session planned tonight is replaced by tonight's decision, so a second run the same night can't put on a second option. Orders placed by hand are kept the same way. Sanji acts on an order only on its own session and never fills an id twice, so a kept order is harmless. (Recommended. The alternative was to drop an order once its session was priced.)
- An id is `wheel-{for}-{P|C}-{strike}`, the strike as its token with any `:` dropped (`wheel-2026-11-16-P-pct-5`, LD-29).

### LD-23 — Earnings weeks
**Status:** SETTLED · **Basis:** PO, 2026-11-14 · **Affects:** Spec › Why the wheel; the live page

- **Asked:** NVDA's Nov 20 weekly priced about a 10% move at Nov 13's close (the ATM straddle about $15.75 on $162.83), likely its earnings that week (not confirmed). Sell through earnings weeks, or skip them?
- **Outcome:** sell through them, as the backtest did (it had no event filter): a richer premium, and a likelier assignment. The page says so. (Recommended. The alternative was a new rule skipping earnings weeks, which needed an earnings-date source.)

### LD-25 — Every night that plans a week's first session places its order
**Status:** SETTLED · **Basis:** PO, 2026-11-14 (the L2 code review) · **Affects:** Spec › Data; L2-03, L3-01

- **Asked:** the nightly job runs every night, and Friday, Saturday and Sunday nights all plan Monday. The spec said LSEG is asked "on the night before a week's first session only".
- **Outcome:** each of those nights pulls the snapshot and places Monday's order, replacing the last night's (LD-19), so a failed or delayed Sunday run still leaves Friday's order in the file. From Friday's close each night, so normally the same order. Two more LSEG sessions a weekend. (Recommended. The alternative was Sunday night only.)

### LD-26 — The live picks read the close snapshot, not a MarketView
**Status:** SETTLED · **Basis:** PO, 2026-11-14 (the L2 code review) · **Affects:** CLAUDE.md › Hard rules › Strategies; `pmcc/live/rules.py`

- **Asked:** CLAUDE.md's hard rule "Strategies see market data only through `MarketView`" comes from the backtests, where the view stops a bar loop reading the future. The live picks read tonight's close snapshot directly.
- **Outcome:** the rule is amended: the live wheel's picks read the close snapshot, which holds only data up to the run, so look-ahead can't happen. The backtests keep the rule. (Recommended. The alternative was a MarketView adapter over the snapshot.)

### LD-29 — A put's strike goes as its percent from the close, which Sanji applies to the open
**Status:** SETTLED · **Basis:** PO, 2026-11-16 (twice: the change, then its code review) · **Affects:** Spec › Trade rules (L-P4, L-O1), Orders, Run log, Invariants (LINV-03); amends LD-11 for puts and LD-22 for `pct:`; L2-04

- **Asked:** the order is written the night before, from the last close, and the strike was sent as a number, so a gap at the open (likelier in an earnings week) leaves it at another delta than the rule meant: a gap down puts the $155 put near the money. The class of Nov 10 and the order page have Sanji pick a strike against the open (`atm`, `otm:N`, `pct:X`); `delta:` and `premium:` are refused until Robin has chain snapshots. The options: keep the number; `pct:`; `otm:N`.
- **Outcome:** `pct:`. The night still picks the 0.30-delta put at the close from LSEG (L-P3), then sends its strike as its distance from the close in whole percents (`pct:-5` for $155 against $162.83, −4.81%). Sanji takes the open × (1 + X/100), then the nearest listed strike, a tie further out of the money, so the strike moves with a gap: at Friday's close `pct:-5` is $155, after a 6% gap down $145. (Recommended.)
- **Whole percents (the code review):** the order page shows only whole ones (`pct:-5`) and rejects a token it doesn't know, so a decimal (first sent as `pct:-4.8`) might be rejected; the order language now refuses a decimal `pct:` (LD-22's rule: nothing the page doesn't show). A whole percent moves Sanji's target at most half a percent of the close, under half a strike step while strikes are over 1% of the price apart (NVDA's $2.50 at $162.83 is 1.54%; $5 below $150), so an unchanged open still lands on the picked strike; a property test sweeps closes from $20 to $600. The rounding step is L-O1's `pct_step` (1).
- **The cash (the code review):** the strike Sanji sets is unknown until the open, so L-P4 and LINV-03 check the cash against the strike picked at the close × 100 plus L-P4's `gap_allowance`, 10% for a gap up (PO). $25,000 covers it many times over today; it matters once fills tighten the cash.
- **What follows:** a call's strike stays a number, since L-C3 must never sell below the cost basis and a strike set at the open can't promise that. The id carries the token (`wheel-2026-11-16-P-pct-5`). The run log adds the strike sent; the page shows it.
- **Monday Nov 16's order** was written on Sunday night as `155`. It was converted on 2026-11-16, before the open, by one-off scripts through the same code (`pct_token` and `order_id` on the logged pick, $155, and Friday's close, $162.83, LD-21), both files through the order language's checks: first to `pct:-4.8`, then, at the code review, to `wheel-2026-11-16-P-pct-5`, strike `pct:-5`. No run could have replaced it (a run before Monday's close is refused, LD-24). It isn't a run, so it has no run-log row: the two Nov 15 rows still name the order as first written, and the page's Open orders caption says so. A copy of Monday night's run on the converted files keeps it and asks LSEG nothing. Sanji isn't resolving orders yet, so no fill is expected either way.

### LD-30 — A blotter of Sanji's fills
**Status:** SETTLED · **Basis:** PO, 2026-11-16 · **Affects:** UI-SPEC §6 › Live (Fills); L5-01

- **Outcome:** once Sanji resolves an order, the page's fills become a blotter like the wheel page's: each fill as a row, joined to the night and order that placed it, with its time, contract, side, quantity, limit, fill, cash change, the rule that placed it and, once the option settles, its P&L. Built at L5-01, when `fills.json`'s format is known. (Recommended.) A wheel fill joins its run by the session and right its id carries (`wheel-{for}-{P|C}-`), not the whole id, since Monday Nov 16's id changed after its run (LD-29; the code review).

### LD-31 — A late nightly run still plans the next session
**Status:** SETTLED · **Basis:** PO, 2026-11-17 · **Affects:** Spec › Nightly job (Schedule, When), Trade rules (L-S1); amends LD-24's When and LD-27's cron; L3-01

- **Asked:** Monday night's scheduled run (03:00 UTC Nov 17) hadn't started by 06:51 UTC. GitHub starts scheduled workflows late when it's busy: the course's `oi-plots.yml`, on the same cron, started between 09:41 and 10:31 UTC every night from Nov 11 to Nov 16, about 7 hours late. A run that late falls on the next trading day before its close, which LD-24 refused, red. The options: let a run before the open plan that day, and move the cron off the hour; the same, keeping `0 3`; no change, running it by hand after the close.
- **Outcome:** a run before the open plans that day's session from the last close, as the night before's would have: L-S1 counts from the last close, not the run's date. Only a run during a session, from the 09:30 open to its close, is refused. The cron moves to `17 3 * * *` (03:17 UTC: 22:17 EST), off the top of the hour, which GitHub names as its busiest time. (Recommended.)
- **What follows:** the close snapshot already counted from the last close, so the pick is unchanged. A Monday run before the open still plans Monday and places its put from Friday's close (LD-25). A run before the open still needs the price file current to the last close (L-B1).

### LD-32 — A stale price file is a warning while Sanji has written no book
**Status:** SETTLED · **Basis:** PO, 2026-11-17 · **Affects:** Spec › Trade rules (L-B1), Run log; amends LD-14 for L-B1; L3-01

- **Asked:** Sanji's price file stops at Fri Nov 13: the course's server (Luffy) last pushed to every student repo at 21:00 UTC that day, and the Monday price update never came. Under LD-14 every run then fails L-B1 and shows red, at whatever hour, until Luffy catches up. Sanji has resolved no order, so the book is cash and can't have moved. The options: a warning while Sanji has written no book; keep L-B1 strict.
- **Outcome:** while neither `positions.json` nor `fills.json` exists, a price file behind the last completed session doesn't stop the night: the run decides as usual and its row's reason ends with "(L-B1 warning: …)", saying how far behind it is. A Sanji that hasn't priced a session can't have filled an order in it. Once either file exists, L-B1 is strict again, as LD-14 has it. (Recommended.)
- **Checked:** at 02:40 ET on Nov 17, a dry run planned Tuesday from Monday's close, kept Monday's order (L-P1) and logged the warning.

### LD-33 — A volatility workflow and its charts: IV against RV20, and the smile
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** Spec › Scope, Volatility, Site; UI-SPEC §6 › Live; L4-02

- **Asked:** the course's clarification: besides the open order on the page and the scheduled nightly run, the work should show a GitHub Action that gets data from LSEG and a chart of it, as the course's `oi-plots.yml` does. Interesting, maybe implied against realized vol.
- **The charts:** two, side by side on the live page. NVDA's ATM implied vol against its 20-day realized vol, a point a session, the gap between them shaded: the wheel's edge, since selling options pays when implied vol runs above what the stock then realizes. And the coming week's smile at the last close, the close and L-P3's pick marked; it needs no history. (Recommended. The others: IV against RV alone; the smile alone; each week's straddle-implied move against the actual.)
- **Where:** its own workflow, like the course's `oi-plots.yml` beside its deploy: a failed chart pull can't touch the orders, and the order job still asks LSEG only when it trades. (Recommended. The other: a step in the nightly.)
- **History:** a backfill of about three months, by hand, after its `--plan-only` estimate, then a point a night. (Recommended. The other: from the first night only.)
- **Drawn:** on the site, by its ECharts and theme, from committed numbers: IVs and RV20, never LSEG's quotes. No new dependency. (Recommended. The other: a PNG made in the action, which needs matplotlib.)
- **The tenor:** the weekly expiry nearest 30 calendar days out, a tie going later, so it matches RV20's month and doesn't jump as an expiry nears. (Recommended. The other: the coming weekly, the one the wheel sells.)
- **ATM IV:** the mean of the call's and the put's IV at the strike nearest the close, among strikes with both sides quoted, a tie going lower. (Recommended. The other: the call alone, as the backtests had it, DEC-25.)
- **RV20:** the 20 daily log returns ending at the session's own close, × √252, so it is read at the same instant as the IV. (Recommended. The other: the 21 closes before the session, as the backtests had it, DEC-26.)
- **The smile:** the out-of-the-money side, puts below the close and calls above: the liquid quotes. (Recommended. The other: both rights at every strike.)

### LD-15 — LSEG data on the page
**Status:** SETTLED · **Basis:** PO, 2026-11-15 · **Affects:** Spec › Run log, Site; UI-SPEC §6 › Live; L4-01

- **Asked:** in the class of Nov 10, the professor relayed the library's view that an app displaying LSEG data to the public could breach the licence: "we're not going to display it directly. We're just going to explain it." The recommendation was a page with our decisions and no LSEG quotes.
- **Outcome:** that concern was about the professor's own app, not this work, so the page isn't restricted. Asked next whether to show the pick's quote: yes. Each run-log row carries the picked option's bid, ask, mid and spread at the close, and the page's run log shows them (Recommended). Rows logged before (Nov 15's) show "—" for them.
- `pmcc live-probe` still prints counts only and keeps the quotes in its report (LD-21): that was its design, not this question's.

### LD-16 — The page's route and nav name
**Status:** SETTLED · **Basis:** PO, 2026-11-15 · **Affects:** UI-SPEC §6, §7; L4-01

- **Outcome:** `#/live/NVDA`, "Live" in the nav after the wheel's pages; the PMCC's Compare page stays the landing page. (Recommended. The alternative was the live page as the landing page.)

## Open

None.

## Engineering

### LD-17 — Sanji's files are exempt from the formatting hooks
**Status:** ENG · **Affects:** L1-01

- **Built 2026-11-13 (L1-01).** CI has failed on every Sanji push since Nov 5: CI runs pre-commit on every file, and `price_history.json` has no final newline, which `end-of-file-fixer` rejects. Sanji's files (`price_history.json`, `positions.json`, `fills.json`) are excluded from every file-fixing hook, as the raw cache is; the repo-policy test pins it. We never rewrite them.

### LD-18 — ID prefixes
**Status:** ENG

- Decisions `LD-nn`, rules `L-…` (L-B1, L-P3, L-O1), invariants `LINV-01` … `LINV-09`, backlog items `L0-01` …. None collides with the PMCC's (`DEC-nn`, `E-…`, `INV-…`, `P0-01`, `L-01` deferred items, whose form differs) or the wheel's (`WD-nn`, `W-…`, `WINV-…`).

### LD-20 — Code layout
**Status:** ENG

- `pmcc/data/lseg/platform.py`: the platform session from the environment (and its fake for tests). `pmcc/live/`: the order model and writer, Sanji's file readers, the rules and the run, beside the wheel's code, which is untouched. `configs/live.yaml`: the rules. `pmcc live` (`just live`): one run. `.github/workflows/nightly.yml`: the schedule. Details are recorded at each item.

### LD-21 — The headless session and the close snapshot (L1-02)
**Status:** ENG · **Affects:** Spec › Data; L1-02, L2-03

- **Session:** `pmcc/data/lseg/platform.py`: `PlatformCredentials.from_env` reads the three variables as given, spaces included (a missing or blank one is named, never its value), and `platform_session` opens lseg-data's platform session (`Definition(app_key, GrantPassword(username, password), signon_control=True)`), makes it the default and checks it reports Opened before anything is asked. lseg-data 2.1.1's `Session.open()` returns Closed on a failed sign-in instead of raising, so the check matters; a contract test builds the real session offline and pins both its shape and that return. An error while building or opening the session is re-raised as an outage with every credential masked, as typed, URL-encoded and JSON-escaped, and without its original as the cause (LINV-09). It always closes.
- **signon_control:** `True`, as in the course's nightly job: opening takes the account's sign-on from another platform session, so a session left open elsewhere can't fail the nightly run. If that turns out to sign the PO out of something they use, it's a question for the PO.
- **The snapshot:** `pmcc/live/snapshot.py`, through the same `HistoryProvider` port and batched fetch as the backtests (single-RIC re-asks, retries, fail-soft unlisted strikes). For the last completed session: the stock's close, the last trade in the close bar (if LSEG hasn't published that bar, the snapshot stops: an earlier trade is not the close); and every put and call from 10% below the close to 10% above, in $2.50 steps, for the expiry of the week of the session after it (L-P2), each with its bid, ask and last trade in the close bar. The session after is counted from the session read, so the close and the expiry always pair; for the nightly run, after the close, it is L-S1's first session after the run's date. How L-S1 treats a run before the close is for L2-03. The band and step are L-P3's and L-C3's params in `configs/live.yaml` (L2-03; the probe uses L-P3's). A 0.30-delta weekly sits a few percent from the money. A strike LSEG doesn't list comes back unlisted. L2-03's pick reads this snapshot.
- **The probe:** `pmcc live-probe --symbol NVDA` (`just live-probe NVDA`) writes the snapshot to `data_cache/probes/live_NVDA_{time}.json` (gitignored, never overwritten), prints counts only, and exits 1 if no option had a valid quote at the close. `.github/workflows/live-probe.yml` runs it by hand in Actions with the repo's secrets: read-only, the secrets in that one step, the report kept as a one-day artifact. The artifact holds LSEG's quotes; the PO is fine with it as is (2026-11-13, at the code review).
- **Probe result (2026-11-14, the PO's run in Actions):** the session opened headlessly; NVDA closed $162.83 on Fri Nov 13; for the Nov 20 expiry, of 30 contracts asked from $145 to $180, 28 were listed (not $147.50: NVDA's strikes are $5 apart below $150) and all 28 had a valid bid and ask at the close, spreads about 1–2% of the mid. The $162.50 pair holds put-call parity to about $0.02.

### LD-22 — Reading the order language strictly (L2-01)
**Status:** ENG · **Affects:** Spec › Orders; L2-01

- **Where:** `pmcc/live/orders.py`: an `Order` model (pydantic, strict, unknown fields forbidden), `parse_orders`, `read_orders`, `render_orders` and `write_orders`. Every order is checked before the file is written, and an invalid one fails with nothing written (LINV-01). Orders already in the file, ours or placed by hand (LD-12's tests), are read through the same checks; a bad one raises `OrderError`, as does a file that isn't UTF-8 JSON. What the run then does is LD-14's question.
- **Strict where the page is silent:** tokens (`expiry`, `strike`, `lmt_prc`) must be JSON strings, as in all the page's examples; `qty` and `underlying` must be JSON whole numbers (not `true`, `"1"` or `1.5`); `for` and a date expiry must be real calendar dates, and a date expiry can't be before `for`; a field is given or left out, never `null`; a numeric strike or limit must be above zero; `NDTE` takes no leading zero; `delta:X` takes 0 < X < 100 with no sign, and `premium:X` X > 0; `otm:N` and `itm:N` take N ≥ 1; `pct:X` takes an optional sign and a whole number (LD-29, its code review: the page shows no decimal). Anything the page doesn't show is refused, so we never send Sanji something it might reject. Whether `for` is a trading session, and whether an id is already in Sanji's `fills.json` (the page's "Unique in the repo"), need the calendar and Sanji's book: the run checks those (L2-02, L2-03; LINV-05).
- **The page's own rules:** a limit order needs `lmt_prc` and a market order mustn't have one; a put or call needs `expiry` and `strike`, and shares carry neither; `vega:` is reserved and rejected; ids are unique in the file. Rules that depend on the book (a `SEL` with no long, a `BTC` with no short) are the live rules', at L2-03.
- **The file:** a JSON list (`[]` when empty), two-space indent, LF, a final newline, the page's field order, absent fields left out (an omitted `ref` stays omitted, so a hand-written order round-trips unchanged). It's written whole, replacing the last: staged as a `*.partial` file beside it, which `.gitignore` keeps out of any commit if a run dies mid-write.
- **Ids and strikes:** `order_id` makes LD-19's `wheel-{for}-{P|C}-{strike}`, `strike_token` writes a strike as a plain number (`155`, `152.5`), and `pct_token` as its whole percent from a reference (`pct:-5`, LD-29).

### LD-24 — The night's run: book, rules, file and log (L2-02, L2-03)
**Status:** ENG · **Affects:** Spec › Data, Trade rules, Orders, Run log; L2-02, L2-03

- **Where:** `configs/live.yaml` (every `L-` rule in the spec's order, its params and words, every threshold under its rule: the strike band and target delta under L-P3 and L-C3, the starting cash under L-P4; plus the conid and r), read by `pmcc/live/config.py`, which refuses a missing, extra, misordered or mistyped rule or param at load, before LSEG is asked. Names and formats the modules share are in `pmcc/live/names.py`. `pmcc/live/book.py` reads Sanji's files (L-B1, L-B2), `pmcc/live/rules.py` picks from the close snapshot (L-P3, L-C3, L-T1, L-P4), and `pmcc/live/run.py` runs the night. `pmcc live --symbol NVDA [--dry-run] [--root DIR]` (`just live NVDA`) is the command; it prints one ASCII line, since the Windows console can't print "−".
- **L-B1 over every instrument:** the price file's latest date over all its entries must be the last completed session. NVDA's entry is empty until the price job's next run, so NVDA alone would make Sunday's book look stale.
- **L-B2 without Sanji's formats:** Sanji wasn't resolving orders, so `positions.json` and `fills.json` were never seen. With neither, the book is cash alone at the starting cash; either one appearing stops the run (LD-14) until L5-01 reads it. The Put, Shares and Call states are built and tested through the decision alone (given a book), not from Sanji's files.
- **When:** a run on a trading day before its close is refused and writes nothing: the spec's L-S1 plans the first session after the run's date, and only after the close does that pair with the close the snapshot reads. The nightly 22:00 run is always after it. Amended (PO, LD-31): GitHub starts the cron hours late, so L-S1 counts from the last close and only a run during a session, from its open to its close, is refused; a run before the open plans that day.
- **LSEG only when needed:** the snapshot is pulled only when the session planned is its week's first and the book is Cash or Shares (Friday to Sunday for a Monday, PO, LD-25), with the strike rule's band; other nights ask LSEG nothing. A run past the session calendar (2027) is refused like one during a session (LD-31).
- **The picks:** the backtests' chain pricer (Black-Scholes, IV from the close's mid, T from the close to the expiry session's close, ACT/365), OTM only, nearest the target delta, a tie further out of the money; a contract whose IV doesn't solve can't be picked. They read the close snapshot, not a `MarketView` (PO, LD-26).
- **The checks:** LINV-02 to LINV-05 and LINV-07 are checked before anything is written. The root and `mkt/` order files must agree when read (L-B2), so a write that stopped between the two shows red the next night.
- **Failures (LD-14):** once the sessions are known, anything that stops a night (a stale or unreadable book, an LSEG outage, a check, an order the language rejects, a write) logs a failed row and raises; `pmcc live` turns each into a "no new order" exit 1, never a traceback.
- **The log:** `live/runs.jsonl`, one JSON line a run, failed runs included. Failed rows carry the rule they failed under: `L-B1`/`L-B2`; `L-P3`/`L-C3` for an LSEG outage during the pick; the decision's rule for a failed check or write; `L-S1` when the snapshot plans the wrong session. A row holds the run time, the sessions, the state, cash, the cost basis, the outcome, the rule and why, the order id, and the pick's contract, strike, expiry, delta and IV, with its bid, ask, mid and spread at the close (PO, LD-15; LD-28).

### LD-27 — The nightly workflow (L3-01)
**Status:** ENG · **Affects:** Spec › Nightly job; L3-01

- **Where:** `.github/workflows/nightly.yml`: cron `0 3 * * *` (`17 3 * * *` since LD-31) and a manual run, on `main` only, one run at a time: a run started while another is going waits for it and never cancels it (GitHub keeps only the newest of the waiting ones, which plans the same). It installs from `uv.lock` and runs `pmcc live --symbol NVDA`; the three LSEG secrets are given to that step alone (LINV-09). Its token may write the repo's contents and nothing else.
- **The commit (LD-06):** as `github-actions[bot]`, `git add` names only `open_orders.json`, `mkt/open_orders.json` and `live/runs.jsonl`, so nothing else the run leaves behind can be committed; a night that changed none of them commits nothing. It then pulls with a rebase and pushes to `main`, up to three tries, ten and then twenty seconds apart, since Sanji pushes to the same branch; Sanji never writes these files, so the rebase can't conflict with it. Checked against a scratch remote with a push landing mid-run.
- **A failed night (LD-14):** `pmcc live` logs a failed row and exits 1, so the commit step runs whenever the run step ran, pass or fail. After a failure it puts both order files back as they were checked out and commits the log row alone, so a failed night never changes an order, even one written before the failure; the job stays red from the run step (neither it nor the job may continue on error). A run refused during a session (LD-31), or a cancelled job, commits nothing.
- **CI and the site (LD-06):** `ci.yml` also runs on the nightly workflow's completion (`workflow_run`, on `main`), which checks out `main`'s latest commit, the bot's included. It checks every night's commit, pass or fail, and uploads and deploys the site only after a successful night, as the spec says; a failed night's row reaches the page with the next deploy (the next good night or Sanji's push). CI shares one group on `main`: a run after the nightly never cancels another, while a push's run may cancel it, since that builds a newer `main` and deploys. A nightly that committed nothing (cancelled, refused) still starts CI on an unchanged `main`: free runner minutes on a public repo, accepted.
- **Lateness:** GitHub can start a scheduled run late, or drop one under load. A dropped weekend night is covered by the other two (LD-25); a dropped weeknight only misses its log row. A manual run covers either.

### LD-28 — The live page's data and layout (L4-01)
**Status:** ENG · **Affects:** UI-SPEC §6 › Live; L4-01

- **`live.json`:** `pmcc export` writes it beside `index.json` and `rules.json` when given the repo root (`--live`, the current directory by default; CI's export runs from the root), and the index names it (`live`). `pmcc/export/live.py` builds it at export time, like the index, so the page can't disagree with the files: the root's `open_orders.json`, read through the order language's checks; Sanji's `positions.json` and `fills.json` (under `mkt/` first), their text exactly as written and never parsed, null when absent: their format is unknown until L5-01, and a file Sanji leaves half-written must not stop the whole site's export on his push; every row of `live/runs.jsonl`, money as dollars, none before the first run; the root's `configs/live.yaml` (so `--live DIR` reads one checkout, never two): its rules in their words, the conid, the starting cash and r; and the wheel's backtest summary from its committed result. An order file or run-log row that can't be read, or a missing config, stops the export, with nothing written. Its schema, `live.schema.json`, gives the page its types. The schema version is unchanged: the index only gains a field, and every result file keeps its own.
- **Quotes in the log (LD-15):** written as dollars to two places at least and four at most (`2.435`), so a mid on a half cent is exact; `spread` is (ask − bid) / mid, as L-T1 reads it.
- **The page:** `web/src/pages/Live.tsx` and `pages/live/sections.tsx`, per UI-SPEC §6 › Live. Readouts come from the latest run-log row. The algorithm's prose holds the "why" text (PO, 2026-11-16), with the backtest's figures read from `live.json`, and its rules table follows the prose in the same panel. The prose restates L-P3's −0.30 and L-O1's "mid at the open", and names the first week (to Nov 20): the PO kept the numbers for readability (2026-11-16, at the code review), so a change to either rule's params changes the prose too. The decision readout goes by the row's outcome. Strikes sort by value. Sanji's files are shown as their text (a file block) until L5-01 knows their rows. The open orders' file is rebuilt in the order page's field order, absent fields left out, so it reads as the file does.

### LD-34 — The volatility workflow's files, pulls and schedule (L4-02)
**Status:** ENG · **Affects:** Spec › Volatility; UI-SPEC §6 › Live; L4-02

- **Code:** `pmcc/live/vol.py` (the tenor, the ATM pair, RV20, the smile, which sessions to fill, the files; pure) and `pmcc/live/vol_fetch.py` (LSEG, through the backtests' fetch: batched, retried, an unlisted strike fail-soft). `pmcc vol --symbol NVDA [--since DAY] [--plan-only] [--root DIR]` (`just vol NVDA`) is the command. The closes are the snapshot's: the last trade in each session's close bar (LD-21). IVs are the live picks' (LD-11, LD-13). `rules.price_at_close` is shared with L-P3 and L-C3.
- **The pulls:** first the stock's closes, from 20 sessions before the first point to the last, in one request: the plan, which `--plan-only` prints (sessions, expiries, contracts, requests) before anything else is asked. Then, expiry by expiry (sessions share the tenor's expiry for about a week), every put and call within $7.50 of each session's close, $2.50 apart, over those sessions' close bars: the nearest listed strike is among them whether NVDA lists strikes $2.50 or $5 apart. The smile is the nightly run's close snapshot (`take_snapshot`, L-P3's band) and L-P3's pick (`select`).
- **The files:** `live/vol.jsonl`, one point a session (session, close, expiry, ATM strike, call and put IV, their mean, RV20), only ever appended to; a session with no strike quoted on both sides keeps a row with null IVs. `live/smile.json`, the last session's smile (each strike's right, IV and delta; the close; the pick), replaced when a later session's is taken. Both hold numbers derived from LSEG's quotes, never the quotes (PO, LD-33).
- **What a run fills:** the sessions after the last point up to the last completed session, or the last alone on a first run; with `--since`, every session missing from that day. More than 10 behind without `--since` stops the run, so a long pull is always asked for by hand after its plan (CLAUDE.md › LSEG access). A run with both files current asks LSEG nothing. There is no time guard: the last completed session is the same before the open and during the session.
- **Failure:** an outage, or a session with no close (LSEG hasn't published it), writes nothing and exits 1; the workflow commits nothing and stays red. The orders are never touched.
- **The workflow:** `.github/workflows/vol.yml`, cron `47 3 * * *` (03:47 UTC: 22:47 EST), 30 minutes after the nightly's, and by hand with `since` and `plan_only` inputs, passed to the command through the environment, never pasted into the script. Main only, one run at a time, contents write; the secrets in the pull's step alone. The Actions bot commits only the two files, after a pull, three tries, as the nightly does; a plan commits nothing. CI's `workflow_run` lists it beside the nightly, so the site redeploys after a successful pull.
- **Export and page:** `live.json` gains `vol` (the points by session; a session twice stops the export) and `smile` (null before the first). The page's two panels and their tokens are UI-SPEC §6 › Live's and §3's: `--iv-line` (MARK), `--rv-line` (NAV_LINE), `--vol-gap-shade` (MARK at 14%). Each chart's values are in a table in a disclosure under it.

### LD-35 — The open orders show the strike LSEG gave the run beside the one sent
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** Spec › Site; UI-SPEC §6 › Live (Open orders); L4-02's follow-up

- **Asked:** the open orders' strike should come from the nightly run's LSEG data. The Open orders panel showed only the token Sanji gets, `pct:-5` (LD-29), not the $155 put the run picked from LSEG's chain at the close. The options: show LSEG's strike beside the token, on the page only; or send it to Sanji as a number, reversing LD-29, so a gap at the open leaves the put at another delta.
- **Outcome:** the page only. The Open orders table shows "Picked at the close", the strike and delta LSEG gave the run, beside "Sent as", the token in `open_orders.json`, which is unchanged. (Recommended.)
- **How the page finds it:** from the run log in `live.json`, the latest row that ordered, for the order's session, the same contract and expiry; matched by those, not the id, since Monday Nov 16's order was re-sent under a new id (LD-29). A dash when no row matches. No change to the export or the run.
- **With it:** the smile's caption says its dashed strike is the put L-P3 *would* pick from that close, since an order goes in only for a week's first session.
- **The rules last (PO, the same day):** the rule table leaves the algorithm panel for its own, "The rules", the last on the page; the algorithm's prose ends with a line pointing to it.
- **The table alone (PO, the same day):** the Open orders panel drops its `open_orders.json` disclosure, the file's text, and shows only the table; the file is still in the repo for Sanji.

### LD-36 — The site's name, home page and menus
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** Spec › Site; UI-SPEC §2, §6 (Home), §7; L4-03

- **Asked:** the site has outgrown its header: "PMCC Backtest" names one of three strategies, and ten pages sit in one flat row. A home page with a title and a link to each strategy; a new name; a dropdown per strategy holding its pages.
- **The name:** "Algo Trading Strategies", in the bar and the browser tab. (Recommended. The others: "Options Strategy Backtests"; "FINTECH 535: Algo Trading".)
- **The home page:** `#/`, which opened the PMCC's Compare page, is now a card per strategy: what it does, its status, one headline from its own file (the live wheel's open orders and last run; the wheel's P&L and Sharpe; the PMCC's P&L by strategy), and links to its pages. (Recommended. The other: a plain linked list.)
- **The order:** the live wheel first, then the wheel backtest, then the PMCC backtest, in the menus and on the home page. (Recommended. The other: oldest first.)
- **The menus:** one per strategy, its pages inside. The live wheel has one page, so its entry is a plain link (an engineering call, the PO's to overrule).
- **No symbol picker:** every strategy has data for NVDA alone, so the picker goes (the PO: "there's no data for any other ticker"). The routes keep their symbol, so every link still works.
- **No ident line:** the grey "NVDA · hourly · 2026-03-30 → 2026-09-25" showed the PMCC's window on every page, the live page's included; it goes. (The PO, over the recommended per-strategy line.)
- **Universe and Data off the menus:** on the public site Data says only that a data connection is needed, and Universe screens one symbol. Their routes still work. (Recommended.)
- **A strategy label:** each page but home names its strategy under the bar, `PMCC BACKTEST › QUANT`. (Recommended.)
- **How the menus work (ENG):** a disclosure, not an ARIA menu, as site navigation should be: a button that shows a list of links, closed by a link, Escape (focus back on the button), or a click or focus outside. No new dependency.

### LD-37 — The home page's look: modern, less text, a moving background
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** UI-SPEC §6 (Home); amends LD-36's home page; L4-04

- **Asked:** make the home page less text-heavy, more dynamic and modern: clean and minimal with an interesting design. Asked: the layout (tiles with small charts, recommended; a live hero over compact rows; plain rows), the motion (subtle, home only, recommended; none), and the look (the same palette made airier, recommended; a modern break).
- **Layout:** tiles, no charts; the text made more interesting, like a modern homepage (the PO). So: a big headline, one big figure per tile, one sentence each, the pages as pill links.
- **Motion:** "something in the background", not tied to the data (the PO). So: three blurred lights in the palette's amber, cyan and violet drifting slowly, and a faint drifting grid; still under reduced motion. The charts' no-animation rule (UI-SPEC §4) is unchanged.
- **Look:** a modern break (the PO, over the recommended airier terminal look): rounded, translucent tiles that lift on hover, display type, no panel chrome. The home page only; the pages behind it keep the square terminal look (DEC-71's square corners and no shadows hold there).
- **Copy (PO, the same day):** the headline "Harvesting the volatility risk premium.", the subtitle "Systematic options strategies". First drafted as "Selling premium, one week at a time." over a line about the live wheel; the PO asked for professional copy, a subtitle not about the live wheel. Offered: the volatility risk premium (recommended), "Trading volatility, not direction." (set aside as overstated: both strategies are net long delta), and the Greeks; the PO took the first's headline with the shortest subtitle.
- **Styles:** `web/src/theme/home.css`, colours only as tokens or `color-mix` of tokens, so no new palette value.

### LD-38 — The site calls the live wheel "Wheel forward test"; its home tile tells the week's trade
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** UI-SPEC §2, §6 (Home), §7; Spec › Site; L4-04's follow-up

- **Asked:** "live" misdescribes it: the strategy isn't trading live, it runs each night and another system (Sanji) fills its orders. And the home tile's `$155 put` over `Open order · expires Nov 20` didn't tell the story. Offered for the name: "Wheel forward test" (recommended), "Paper wheel", "Nightly wheel"; for the tile: the volatility premium it's harvesting (recommended), this week's trade as a story, the capital at work.
- **Outcome:** "Wheel forward test", the industry's term for running a backtested strategy forward on data it hasn't seen, beside "Wheel backtest". Its one page is named "Overview" (an engineering call, the PO's to overrule), so its label reads "Wheel forward test › Overview". And the tile tells this week's trade: "Selling a $155 put", then "Delta −0.32 · IV 88.2% · expires Nov 20", the pick's at the close (LD-35); "No trade open" when there's none. The kicker is "Forward test · nightly", the headline's pill "Last nightly run …".
- **"Selling", not "Short":** the preview the PO chose read "Short a $155 put"; the page says "Selling", since the order is open and Sanji hasn't filled it, so nothing is held yet.
- **Unchanged:** the route `#/live/NVDA`, so links already shared still work; and the project's docs, commands and files, which keep "the live wheel" as the project's name.

### LD-39 — The smile chart is named a skew
**Status:** SETTLED · **Basis:** PO, 2026-11-18 · **Affects:** UI-SPEC §6 › Live (panel 3); Spec › Site; L4-02

- **Asked:** the chart doesn't look like a smile. Why: stock options show a skew (puts dearer than calls), not a currency-style smile; this week's expiry spans earnings, whose expected jump lifts every strike's IV about equally and flattens the curve; and the strikes reach only 10% from the close, short of the wings where a smile curves. Offered: this week's and the ~30-day expiry together, strikes out to ±25% (recommended); rename it and keep the data; switch to the ~30-day expiry.
- **Outcome:** rename it, keep the data. The panel is "This week's skew"; its caption says stock options skew rather than smile, and an expiry that spans earnings sits high and flat. The pull, `live/smile.json` and its code keep the name "smile".

### LD-40 — The algorithm's and the skew's copy, the PO's own
**Status:** SETTLED · **Basis:** PO, 2026-11-19 · **Affects:** UI-SPEC §6 › Live (the algorithm; panel 3's caption); L4-02's follow-up

- **Asked:** the PO wrote both texts, in the first person, and asked for an accuracy check.
- **Outcome:** the PO's text, as written but for these fixes, each against the code or the results:
  - **Cash check:** "enough cash to cover 100 shares" → "enough cash to buy 100 shares at the strike, with a 10% cushion for a gap at the open" (L-P4's `gap_allowance`, LD-29).
  - **The Sharpe it's compared with:** "my original PMCC strategy" → "my baseline PMCC strategy": 1.24 is the baseline's; quant's was 1.11.
  - **The workflows:** "One checks for updates to open orders" → it reads Sanji's book, decides the next order and writes `open_orders.json`, asking LSEG for option prices on the nights it trades; "the other pulls the latest market data" → NVDA's volatility, for the page's charts (L3-01, L4-02).
  - **The rules kept:** "the same rules I used in the backtest" → "the backtest's rules for choosing trades": the selection (the 0.30-delta put and call, the cost-basis floor) is the backtest's, but an order is now decided from the prior close, its strike sent as a percent, with the gap cushion.
  - **The rules panel:** "their corresponding run-log IDs" → "the IDs the run log cites": the IDs are the rules', and the run log cites them.
  - Smaller: "the previous day's" → "the previous trading day's" (Monday's order is from Friday's close); the earnings risk is "the bigger move it prices", not the higher IV itself; in the skew's caption, "the impact of earnings on certain expirations" → "the impact of earnings: when an expiration includes an earnings announcement…", since the chart shows one expiration at a time.
- **Checked:** NVIDIA reported fiscal Q3 2027 after the close on Tue Nov 17, 2026, inside the week ending Nov 20, so "NVDA's earnings fall during that period" holds. The backtest's figures ($4,171.50, 16.7%, $25,000, Sharpe 1.57 against 1.24, Mar 30 – Sep 25, 2026) are read from `live.json`, not typed in. The link to the review is the site's own route, not the github.io URL, so it works on any host.
- **The skew's caption, again (PO, 2026-11-19):** replaced by the PO's shorter one: what the chart shows, what higher IV means for the premium and the risk, and the dashed strike. One fix: "the put strike selected by the strategy" → "the put strike the strategy would select from this close", since an order goes in only for a week's first session, so most nights the line marks a pick that isn't traded.
- **The algorithm, again (PO, 2026-11-19):** replaced by the PO's shorter text, which adds the two ideas the forward test tests (whether a −0.30 delta balances premium against assignment, and whether high-IV premium pays for the risk of being assigned above the market), earnings weeks kept to test them. Fixes, as before: "the previous day's" → "the previous trading day's"; "enough cash to cover 100 shares plus a 10% cushion" → "enough cash to buy 100 shares at the strike, plus a 10% cushion"; "checks the order book" → "checks my current positions and fills" (an order book is the market's bids and offers; the course's order system isn't named, as readers don't know "Sanji", PO), with "writes it to `open_orders.json`" added; "their corresponding run-log IDs" → "the IDs the run log cites"; the review's link is the site's own route. Its figures (16.7%, $25,000, Sharpe 1.57 against 1.24, Mar 30 – Sep 25, 2026) are still read from `live.json`.

### LD-41 — The skew shows the market's expected move, from the ATM straddle
**Status:** SETTLED · **Basis:** PO, 2026-11-19 · **Affects:** Spec › Volatility; UI-SPEC §3, §6 › Live (panel 3); amends LD-34's smile file; L4-02's follow-up

- **Asked:** show the market-implied expected move for the selected expiration, beside the selected strike. Offered for the method: one standard deviation from ATM IV (close × IV × √time; recommended, as it shows from the data already pulled), or the ATM straddle's price (the traders' estimate, about 0.8 of the 1σ move, needing the pull to keep it). For where: a band on the skew chart and a line under it (recommended), or a panel of its own.
- **Outcome:** the ATM straddle's price; a band and a line.
  - **The straddle:** the skew's expiry's strike nearest the close with both its call and put quoted at the close, a tie going lower (the IV chart's ATM rule, LD-33), priced as the call's mid plus the put's (each half-even to $0.0001, DEC-44). The move is that price either side of the close.
  - **The file:** `live/smile.json` gains `straddle` (`strike`, `price`), null when no strike had both sides quoted. A price derived from two quotes, as LD-34's files keep, not a quote. A file pulled before this reads as null, so the page says "No expected move for this close" until the next nightly pull writes one.
  - **The page:** a neutral band (`--move-shade`, TEXT at 9%: data, so never amber) from close − move to close + move, labelled "Expected move"; under the chart, the move in dollars and as a share of the close, its range, the straddle's strike, and the pick's distance below the close, inside or outside the move.
- **The 145 against 155 question (answered, nothing changed):** the open order's $155 was picked from Fri Nov 13's $162.83 close with a week to expiry; the skew's dashed $145 is what L-P3 would pick from the latest close ($150.86 on Nov 18), with two days left. NVDA fell about 7% between them.

### LD-42 — The site doesn't name Sanji
**Status:** SETTLED · **Basis:** PO, 2026-11-20 · **Affects:** UI-SPEC §6 › Live; `configs/live.yaml`'s rule texts; the run log's reasons; L4-02's follow-up

- **Asked:** readers don't know what "Sanji" is, and the PO has been taking the name out of the page's copy. It also reached the page from the rule texts (the rules table) and the reasons the nightly run logs (the run log, the decision readout). Offered: both (recommended), the rule texts only, or neither.
- **Outcome:** both. On the page: the readout hints ("What the account holds"; "The starting cash until the first fill"), the Open orders caption and the Positions and Fills notes say "the course's order system" or "the account". The rule texts of L-B1, L-B2 and L-O1 say "the course's price file", "the order system". The run's reasons say "the order system expires it…" (L-P1, L-C1) and "the course's price job hasn't caught up" (L-B1); L-B2's failure, "the course's order system has written…".
- **Unchanged:** run-log rows already written keep their words; nothing the strategy decides changes; the project's docs, code and commands keep "Sanji" as the course's system's name (the spec's §The course's side defines it), as does the CLI's help, which only the PO reads.

### LD-43 — The skew marks the open order's strike, not tonight's pick
**Status:** SETTLED · **Basis:** PO, 2026-11-20 · **Affects:** UI-SPEC §6 › Live (panel 3); amends LD-33's dashed pick and LD-41's line; L4-02's follow-up

- **Asked:** the skew's dashed $145 (L-P3's pick from Nov 18's close) beside the open order's $155 (picked from Nov 13's) made no sense to the PO: why show a pick that isn't part of the strategy? Mid-week the strategy trades nothing, so the line marked a trade it wasn't making. Offered: the open order's strike (recommended), no line, or both, labelled.
- **Outcome:** the open order's strike. The dashed line is the open order's, labelled "Order", when its expiry is the skew's: its strike as LSEG picked it at the close (LD-35), else as sent when that's a number (a call's). No line when no order expires that day. On the night a week's order is chosen, the order is that night's pick, so the two never differ then. The line under the chart says where it sits: "The order's $155.00 put is 2.7% above the close, in the money, inside the move."
- **Unchanged:** `live/smile.json` still keeps L-P3's pick (the page no longer shows it); the caption's last sentence now reads "The dashed line marks the strike of the open order."

# Volatility thesis (`TD-nn`)

Nov 21, 2026 · companion to the [Thesis spec](THESIS-SPEC.md), the source of truth for the thesis assignment as amended here. The statuses and maintenance rules above apply; the live wheel's `LD-nn` entries decide nothing here, nor these anything there.

## Thesis index

| ID | Decision | Status | Ask at |
| --- | --- | --- | --- |
| TD-01 | The thesis assignment's docs | SETTLED (PO): the spec as `docs/THESIS-SPEC.md` with a scope section; `TD-nn` here; a T phase in the build plan; the live wheel's docs stay live | — |
| TD-02 | Due date | SETTLED (PO): Tue Nov 24 2026, 11:59 pm ET | — |
| TD-03 | Scope: the thesis, its daily tracker and their page | SETTLED (PO): spec §6–8, §11 and §12's Sanji part out; the live wheel untouched | — |
| TD-04 | S&P 500 and VIX closes from LSEG's platform session | SETTLED (PO): from 2014; a probe first | — |
| TD-05 | The credit series: LSEG if it has the history, else FRED | SETTLED (PO): FRED's public CSV approved as a new outside source | — |
| TD-06 | The raw credit spread is charted | SETTLED (PO): whatever tells the story best; charted, its 450 bps line drawn | — |
| TD-07 | R5: a rough, evidence-informed estimate | SETTLED (PO): explicit cost assumptions and limitations; trade-level net P&L waits for the backtest | T2-02 (its form) |
| TD-08 | K1–K3 kept as written; only K1 calculated | SETTLED (PO): K2 and K3 "Not yet evaluated — requires strategy backtesting" | — |
| TD-09 | A `thesis` workflow commits the tracker's files | SETTLED (PO): 04:17 UTC and by hand; commits only `live/thesis/`; widens LD-06 | — |
| TD-10 | One thesis page, in the site's look | SETTLED (PO): `#/thesis`, a "Volatility thesis" menu, a home tile; no trading-comparison or forward-record panels | T4-01 (layout, copy) |
| TD-11 | ID prefixes | ENG | — |
| TD-12 | Code layout | ENG | — |
| TD-13 | The thesis's own command, not `pmcc` | SETTLED (PO): `thesis probe` and `thesis run`, a second entry point; the code stays in the package | — |
| TD-14 | The data probe (T1-01) | ENG | — |
| TD-15 | The thesis calendar, 2014–2027, and its business days | ENG | — |
| TD-16 | The tracker's conventions and missing-data rules (T2-01) | SETTLED (PO): the readings accepted, with the PO's missing-data rules | — |
| TD-17 | FRED through its official API, with a key | SETTLED (PO): `FRED_API_KEY`, a GitHub secret; amends TD-05 | — |
| TD-18 | The probe's first full run, and what it changed (T1-01) | ENG | — |
| TD-19 | The probe's second run: credit from FRED, SPXW's expiry (T1-01) | ENG: LSEG not entitled to ICE's OAS, so FRED (TD-05's rule) | — |
| TD-20 | The probe's third run: SPXW's chain, and no spec condor that day (T1-01) | ENG | — |
| TD-21 | R5's form: the premium beside the measured spreads | SETTLED (PO): measured leg spreads, stressed 1.5× and 2× | — |
| TD-22 | The probe stays strict about outages | SETTLED (PO) | — |
| TD-23 | "Preliminary historical evidence", without an evidence classification | SETTLED (PO) | — |
| TD-24 | K1: a current rolling assessment, no latch yet | SETTLED (PO): the latch deferred to backtesting | — |
| TD-25 | Two more signal states, a blocked assessment that stops nothing | SETTLED (PO) | — |
| TD-26 | The evidence and statuses' conventions (T2-02) | ENG | — |
| TD-27 | `thesis run`, its file and its workflow (T3-01, T3-02) | ENG | — |
| TD-28 | The thesis page: order, charts, home tile | SETTLED (PO); amends LD-36, LD-38's order | — |
| TD-29 | The thesis page, as built, and `thesis run` corrected (T4-01) | ENG | — |
| TD-30 | The thesis page, redesigned for a reader | SETTLED (PO); replaces TD-28's order and labels | — |
| TD-31 | The redesign, as built (T4-02) | ENG | — |

## Thesis settled

### TD-01 — The thesis assignment's docs
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** all docs; CLAUDE.md; README; T0-01

- The spec the PO supplied (`FINTECH_535_Volatility_Thesis_System_Spec.md`) becomes `docs/THESIS-SPEC.md`, its body unchanged, with a "Scope for this assignment" section at the top (TD-03). It is the thesis's source of truth, as amended by `TD-nn` entries.
- Its decisions are this part of DECISIONS (`TD-nn`); its backlog is a T phase in the [build plan](BUILD-PLAN.md). The live wheel keeps running, so its spec, decisions and plan stay live, not archived. (Recommended.)

### TD-02 — Due date
**Status:** SETTLED · **Basis:** PO, 2026-11-21

- Due Tue Nov 24 2026, 11:59 pm ET.

### TD-03 — Scope: the thesis, its daily tracker and their page
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec › Scope for this assignment

- **Asked:** the spec describes a whole research system (contract selection, a ledger and NAV, a trade backtest, policy comparisons A–F, a bootstrap, private storage, a Sanji adapter); the assignment asks for R1–R7.
- **Outcome:** this assignment builds the tracker (§5: the EWMA forecast, VIX against 30-day forecast vol and the matured realized vol, the shock episodes, one candidate per episode, the credit condition), the thesis page with all seven items, and a nightly workflow that keeps it current. Spec §6–8 (options, execution, backtest), §11 (beyond the public JSON's provenance) and §12's Sanji part wait for the backtesting assignment and the final project. The live wheel runs on, unchanged. (Recommended.)

### TD-04 — S&P 500 and VIX closes from LSEG's platform session
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §4.2; CLAUDE.md › Hard rules (LSEG access); T1-01, T3-01

- The S&P 500 price index's and VIX's daily closes come from LSEG, over the headless platform session the live wheel uses (LD-05, LD-21), from 2014-01-01: the 252 sessions of warmup before the spec's 2015 start. (Recommended.)
- A probe comes first (T1-01): it checks the index and VIX histories' coverage, the credit series LSEG offers, and a current SPXW chain, before anything is built on them.

### TD-05 — The credit series: LSEG if it has the history, else FRED
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §4.2; CLAUDE.md › Hard rules; T1-01, T3-01

- **Asked:** FRED's BAMLH0A0HYM2 (ICE BofA US High Yield OAS) now supplies only about three years, so a FRED-only tracker has few credit-tagged episodes and its credit tests are exploratory.
- **Outcome:** use LSEG's series of the same definition if the probe finds a long history; otherwise FRED's public CSV (no API key, read with the standard library, so no new dependency; **amended by TD-17:** FRED's official API with a key). FRED is approved as a new outside source: only the thesis's probe and nightly run contact it, sending nothing about the user or the project. No other credit metric is substituted and no series is spliced silently (spec §4.2). (Recommended.)

### TD-06 — The raw credit spread is charted
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §4.2, §10 (component 4); UI-SPEC (T4-01)

- **Asked:** the spec shows only the stable/unstable flag unless raw credit values are authorized, since ICE and FRED restrict redistribution. Recommended: the flag and its three checks.
- **Outcome:** the PO leaned towards charting the raw spread, "whatever tells the story better and is clear for a human to understand what we're showing and why". Charted: the OAS in basis points, with its 450 bps line and the periods it fails the stability checks marked, beside the VIX chart. A level against its threshold during a VIX spike shows the thesis at a glance; a flag alone doesn't. The page names the source and its copyright holder. This is the PO's authorization under §10 component 4.
- **Risk:** the committed JSON holds the raw values, so it is downloadable. ICE's terms are ICE's, not the course's; see the build plan's thesis risks.

### TD-07 — R5: a rough, evidence-informed estimate
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §2 (R5), §8 › R5; T2-02

- **Asked:** the spec shows "NOT YET ESTIMATED" until a trade backtest exists; the assignment wants a rough note now.
- **Outcome:** "For now, that section can provide a rough, evidence-informed estimate with explicit cost assumptions and limitations. A full trade-level net-P&L analysis can wait for the backtesting assignment." (PO.) It is labelled a gross economic premium, not tradable alpha.
- **Recommended form (confirmed and completed by TD-21):** the edge is the mean and median 30-day variance premium (VIX against the realized vol that followed), on all days and on candidate days, stable and unstable credit apart, with counts. The cost is the round-trip natural spread of a 0.20-delta, 30-day SPXW condor from the probe's chain snapshot, plus spec §7.2's $2 per contract transaction, as a share of its credit.

### TD-08 — K1–K3 kept as written; only K1 calculated
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §9 › R4; T2-02, T4-01

- **Asked:** K2 and K3 need trades, and K1 may fall short of its sample of 30. Keep them frozen as written, or swap K2 and K3 for versions the tracker can measure now.
- **Outcome (PO):** keep K1–K3 and their thresholds as written; trade-based evaluation belongs to the backtesting phase.
  - **K1:** calculated from the matured tracker observations available. Shown: its formula, threshold, available sample count and provisional current value. Fewer than 30 qualifying episodes is `INSUFFICIENT_DATA`; the threshold is never lowered to produce a result.
  - **K2 and K3:** shown with their definitions, thresholds and required sample sizes, labelled "Not yet evaluated — requires strategy backtesting"; their current value and observed sample count shown as unavailable. No trade simulator or P&L is built for this milestone.
  - No condition is replaced merely to make every card calculable. Insufficient evidence never displays as passing. The conditions are kept for the later backtest; only what the tracker supports is calculated now.
  - Completion here means clearly defining the conditions and honestly showing what can be assessed today.

### TD-09 — A `thesis` workflow commits the tracker's files
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** CLAUDE.md › Hard rules (automated writers); amends LD-06 for this workflow; T3-02

- Its own workflow, like `vol` (LD-33): nightly at 04:17 UTC, after the orders' (03:17) and the volatility's (03:47), and by hand. It re-pulls the history each night (a few thousand daily rows), so no private store is needed. Its Actions bot commits only `live/thesis/*.json`, which hold the tracker's derived series and the inputs' daily closes and spreads, never option quotes. A failed pull commits nothing and the job stays red. CI runs on its completion and redeploys the site. (Recommended.)

### TD-10 — One thesis page, in the site's look
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** Thesis spec §10; UI-SPEC (T4-01)

- One page, `#/thesis`, in the existing look, with its own "Volatility thesis" menu and a home tile. It shows spec §10's components 1–4 and 7–10; it leaves out the trading comparison (5) and the forward record (6) rather than show placeholders. Its dated current-state summary is generated only from the tracked series (VIX's level and percentile, RV5 and RV20, the forecast gap, the credit state): no Treasury yields, no news. (Recommended.) The layout and copy are asked at T4-01.

### TD-13 — The thesis's own command, not `pmcc`
**Status:** SETTLED · **Basis:** PO, 2026-11-21 · **Affects:** TD-12; CLAUDE.md › LSEG access; T1-01, T3-01, T3-02

- **Asked:** the PO: why `pmcc thesis`, when the thesis has nothing to do with the PMCC? `pmcc` is only the package's and its command's name, left from the first assignment; the live wheel runs through it too. The options: a command of the thesis's own; `just` recipes over `pmcc thesis`; renaming the whole package.
- **Outcome:** the thesis gets its own command, `thesis`, a second entry point in `pyproject.toml` beside `pmcc`: `thesis probe` (`just thesis-probe`) and `thesis run` (`just thesis`). The code stays in the package, since it reuses the LSEG session, the calendar, logging and the export; the `thesis` workflow runs `thesis run`. The entry point is added with the first subcommand (T1-01). The live wheel's commands keep their names. Renaming the package waits until after the final project, if ever. (Recommended.)

### TD-17 — FRED through its official API, with a key
**Status:** SETTLED · **Basis:** PO, 2026-11-22 · **Affects:** amends TD-05 (the public CSV, no key); CLAUDE.md › FRED, Credentials; T1-01, T3-01, T3-02

- **Asked:** the first Actions run of the probe (2026-11-22) timed out reading FRED's public CSV, `fredgraph.csv`, at 30 s. It may slow or block requests from cloud runners; one run can't tell. The options: FRED's official API with a free key, the supported route for automated clients; or the public CSV only for runs on the PO's machine.
- **Outcome:** the official API, `api.stlouisfed.org/fred/series/observations` (`file_type=json`), with the PO's key in `FRED_API_KEY`: a GitHub secret in Actions (the PO sets it), an environment variable locally. (Recommended.)
- **The key** is read only by `pmcc/thesis/fred.py` (`FredKey.from_env`), never printed: not in a repr, an error or a log; every message is masked, the key as typed and URL-encoded, since it rides in the URL. A missing key stops the probe before anything is asked.
- **Answers:** FRED not answering (a connection, a timeout, a cut-off body, HTTP 429 or a 5xx) is retried as TD-14 says, then an outage; FRED refusing (another 4xx: a bad key, an unknown series) or an unreadable answer is a `FredError` at once, carrying FRED's own `error_message`.
- **Unchanged:** FRED is still only the fallback if LSEG lacks the history (TD-05), and still read with the standard library.

### TD-21 — R5's form: the premium beside the measured spreads
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** completes TD-07; Thesis spec §8 › R5; T2-02, T4-01

- **Asked:** the probe's Nov 20 chain was quoted but spec §6.2's condor was skipped that day (TD-20), so no condor round trip exists. The options: the legs' measured spreads; those and a Monday re-probe; a stated assumption only.
- **Outcome (PO):** the measured leg spreads. From that snapshot, the legs from 0.10 to 0.30 absolute delta: median spreads of 9.65 points on puts (9.71% of the mid) and 8.65 on calls (19.61%), plus $2 a contract a transaction, with a stressed case at 1.5× the spread and 2× the fees. That the spec's condor was skipped that day, and why, is said plainly. One dated sample, `configs/thesis.yaml`'s `r5_cost`. (Recommended.)
- **The edge (PO):** the 30-day variance premium (implied less the realized that followed), mean and median, on all matured sessions and on candidate days, stable- and unstable-credit candidates apart, each with its count; beside the cost, labelled "gross economic premium, not tradable alpha". Candidates without credit data are their own group. (Recommended.)
- **Built** (`pmcc.thesis.evidence`): a round trip at the natural price gives up about one full spread a leg, so a leg's cost is its spread share of the mid plus two fees over the mid; stressed, 1.5× the spread share and 2× the fees. To set the edge on a comparable scale, each cohort also carries the mean share by which VIX overstated the realized vol that followed, labelled rough (an option's value isn't proportional to vol).

### TD-22 — The probe stays strict about outages
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** TD-14; T1-01

- **Asked:** should the probe write the other sections when one source goes down, and exit 1?
- **Outcome (PO):** no: T1-01 is done, so the probe keeps its rule, an outage writes nothing. (Recommended.)

### TD-23 — "Preliminary historical evidence", without an evidence classification
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** Thesis spec §8.4, §9 (`evidence_status`), §10 component 4; T2-02, T4-01

- **Asked:** `evidence_status` is `INSUFFICIENT_EVIDENCE` until 20 matured stable- and 20 unstable-credit candidates exist (§8.4); the spec doesn't define `SUPPORTIVE`, `MIXED` or `UNSUPPORTIVE`, and credit from 2023-11-21 won't reach the gate for years.
- **Outcome (PO):** scoped to the thesis assignment and the daily tracker.
  - The 20 per cohort is documented as a future validation target. It never blocks the website or stops the pipeline, reached or not.
  - The section is titled "Preliminary historical evidence". It shows the matured observations: their date range, count, mean realized variance premium, and the stable-against-unstable comparison where both groups exist.
  - The results are described in plain language ("The average premium was positive in the available stable-credit episodes"), saying clearly that a small sample doesn't establish a reliable edge.
  - With one group empty: "Credit-regime comparison unavailable in this sample." With nothing matured, that is said directly, and the daily forecast tracker stays.
  - No `SUPPORTIVE` / `MIXED` / `UNSUPPORTIVE` classification: two sample means alone would make those labels sound more definitive than the analysis warrants.
  - It updates normally whatever the sample size; the qualifying-event rules are never changed to make more observations. Full statistical validation and trade-based profitability testing stay outside this assignment.
- **Built:** `evidence_status` is always `INSUFFICIENT_EVIDENCE` in this milestone, the gate's counts shown beside it; `pmcc.thesis.evidence.statements` writes the sentences.

### TD-24 — K1: a current rolling assessment, no latch yet
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** Thesis spec §9 › R4 ("A FAIL cannot be erased …"); T2-02, T4-01

- **Asked:** the nightly run recomputes K1 from scratch, so a `FAIL` could vanish when a loss rolls out of its 30-episode window; the spec forbids that. Build a latch now, or defer it?
- **Outcome (PO):** defer the persistent latch to the backtesting phase. K1 shows its current rolling value, sample count, threshold and assessment date, labelled a current rolling assessment. That persistent failure tracking and resumption controls aren't implemented in this milestone is documented. The condition is shown as defined.

### TD-25 — Two more signal states, a blocked assessment that stops nothing
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** Thesis spec §9 (`signal_status`); T2-02, T3-01, T4-01

- **Asked:** a candidate whose credit is unavailable, and a search a missing feature blocked, fit none of the spec's `signal_status` values.
- **Outcome (PO):** add `CREDIT_UNAVAILABLE` and `INCOMPLETE_CANDIDATE_SEARCH`. Neither is read as eligible, filtered out, or a confirmed absence of a candidate. The signal's assessment is marked blocked, but all available tracker data still update and show: a blocked assessment never stops the nightly pipeline or its publication.
- **The page's labels (PO):** "Credit data unavailable — eligibility cannot be assessed" and "Incomplete observation window — candidate assessment unavailable", each with the affected date or episode and a brief reason.
- **Built** (`pmcc.thesis.status`): `signal` carries the status, an `assessment` (`OK` or `BLOCKED`), the episode's ID, shock, candidate and window end, and the reason.

### TD-28 — The thesis page: order, charts, home tile
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** completes TD-10, TD-06; amends LD-36, LD-38 (the menu's and the tiles' order); Thesis spec §10; UI-SPEC; T4-01

- **Asked:** the panel order and copy, the tracker's and the credit spread's charts, and the menu entry and home tile.
- **Order (PO):** the assignment's items in order, with plain headings; methodology and sources last, folded. The thesis, horizons and macro paragraph are spec §1's text. (Recommended.)
- **The tracker (PO):** two stacked panes with one date axis and one zoom. The outcome is labelled "Subsequent 30-day realized volatility", plotted at its forecast-origin date, the tooltip showing the origin and the outcome's end; pending or incomplete outcomes are blank. Event shading is subtle. Eligible, filtered-out and unavailable-data markers differ by both shape and colour. The periods without credit coverage are clearly identified.
- **Credit (PO):** the spread and the 450 bps line, unstable and unavailable credit shaded apart. The latest level and the five- and twenty-observation changes, against their thresholds, are in a small visible summary, not only in tooltips, with the observation's date and when it became available.
- **Menu and tile (PO):** "Volatility Thesis" first in both. The tile's figure is VIX minus the 30-day forecast, signed, labelled "volatility points"; below it a readable assessment and the data-through date; "Daily thesis tracker" as its subtitle; a direct link. If the gap can't be calculated it says "Unavailable", never zero. It never implies the gap is an expected trading return.

### TD-30 — The thesis page, redesigned for a reader
**Status:** SETTLED · **Basis:** PO, 2026-11-23 · **Affects:** replaces TD-28's panel order, readouts and labels, and the page's part of TD-10; TD-25's labels; Thesis spec §1 (R1, R2, R6), §10; UI-SPEC § Thesis; T4-02

- **Asked by the PO:** the page made readers work too hard to see what each number, chart and table means. No change to the calculations, event definitions, thresholds or observations; backend changes only to supply existing calculations to the page.
- **Order:** the idea and its horizons; the latest assessment; the daily tracker; preliminary historical evidence; what would invalidate the thesis; potential return and trading costs; macro conditions; methodology, sources and detailed data behind disclosures. The assignment's six items stay in the normal reading flow.
- **The idea:** the title, the one-sentence thesis, the explanation and the macro paragraph are the PO's copy, in spec §1. A hypothesis being investigated; three horizons, two of them planning estimates.
- **The latest assessment** replaces the readouts and "Today's state": one headline from the backend's signal state, one or two sentences, three supporting observations, the data's dates. All generated from the data; the frontend is never a second signal engine. A historical qualifying observation's date is kept apart from the latest readings. "Research conditions met" never implies a trade or a profit; missing data is never a failed condition or a zero. Labels: `NO_SHOCK` "No qualifying volatility spike to monitor", `SEARCHING` "Watching a recent volatility spike", `NO_CANDIDATE` "No qualifying observation in this search window", `ELIGIBLE` "Research conditions met", `FILTERED_OUT` "Candidate did not meet the credit rules", `CREDIT_UNAVAILABLE` "Credit data needed to assess eligibility", `INCOMPLETE_CANDIDATE_SEARCH` "Missing observations prevent assessment".
- **The tracker:** one chart by default (VIX, our forecast, what followed), with range presets beside the slider; the gap's pane, its threshold, the search windows and the markers under "Show signal details", on the same axis and zoom; raw tables behind named disclosures.
- **Credit:** its purpose before its measurements; the rule a spread breaks is said in words; the chart, the three checks and the dates under "Explore credit conditions".
- **Evidence:** stable against unstable credit first, each with its completed count and average gap; the sample's limits and what is left out beside it; full statistics behind a disclosure. A gap is never a trading return, nor proof of mispricing; no classification (TD-23).
- **Wrong-if:** three stacked cards, K1–K3's definitions unchanged and their exact formulas expandable. K1 reads "Preliminary: n of the required 30 observations available"; K2 and K3 "Evaluated in the next phase: strategy backtesting."; no zero for an unmeasured value.
- **Return and costs:** the gross premium and the quote sample's cost apart, each with its unit; never subtracted; net returns not estimated. Assumptions, stress cases and the structure skipped that day behind a disclosure.
- **Writing and layout:** meaning before formula; a readable size at 100% zoom; a centred column with wider charts; detailed tables only inside disclosures, each with its purpose in a sentence; no colour-only states; styles scoped so no other page changes.
- **Data:** the page gets the existing thresholds, times and dates; what a file lacks shows as unavailable where it would be, never as zero. Freshness is separate from how much evidence there is.

## Thesis engineering

### TD-11 — ID prefixes
**Status:** ENG

- Decisions `TD-nn`, backlog items `T0-01` …. The spec's own IDs are kept as written: deliverables `R1`–`R7`, wrong-if conditions `K1`–`K3`, sources `S1`–`S7`, and its config keys (§13). None collides with the PMCC's (`DEC-nn`, `E-T1`'s rule form), the wheel's (`WD-nn`, `W-…`) or the live wheel's (`LD-nn`, `L-…`).

### TD-12 — Code layout
**Status:** ENG

- `pmcc/thesis/`: the tracker, pure (features, horizons, outcomes, episodes, candidates, the credit condition, K1, R5's note, the public files), reading the spec's keys from `configs/thesis.yaml`. LSEG's pulls live under `pmcc/data/lseg/` (CLAUDE.md › LSEG access); the FRED reader uses only the standard library. The commands are the thesis's own (TD-13): `thesis probe` (T1-01) and `thesis run` (T3-01); `live/thesis/` holds the committed files. Details are recorded at each item.

### TD-14 — The data probe (T1-01)
**Status:** ENG · **Affects:** Thesis spec §4.1–§4.3; T1-01, T2-02, T3-01

- **Command:** `thesis probe` (`just thesis-probe`; TD-13), a second Typer app in `pmcc/cli.py`, since only `pmcc.cli` may open an LSEG session or configure logging (the import-boundary tests). `.github/workflows/thesis-probe.yml` runs it by hand in Actions, as `live-probe.yml` does: read-only, the secrets in its one step, the report kept as a one-day artifact (LD-21's posture). Nothing is cached or committed.
- **Four sections, each on its own:** a source that answered but couldn't be read (an LSEG search refused, FRED's answer not the series' CSV, no SPXW spelling listed) is written into its section, and the others still run. An outage (the LSEG session closing or failing persistently, FRED not answering) aborts the whole probe with nothing written, as CLAUDE.md requires of LSEG and FRED. The run also fails, with the report written, when the index's or VIX's closes don't come back. The console prints counts and dates, never values.
- **Closes:** `.SPX` and `.VIX`, daily bars from 2014-01-01 through the backtests' batched fetch (`fetch_rics`, `Interval.DAILY`), fields `TRDPRC_1`, `HIGH_1`, `LOW_1` and `OPEN_PRC` with each one's count; the days one series has and the other lacks; and its sessions without a bar and bars on its closed days against the thesis's 2014–2027 calendar (TD-15), so the history table is checked against the tape.
- **Credit on LSEG:** the RIC of ICE BofA US High Yield OAS isn't known, so the probe searches (`discovery.search`, four queries, `RIC,DocumentTitle`, ten hits each) and reads the first six RICs found as daily tables with whatever columns LSEG sends (`get_history` with no fields; since TD-18, each search's first three, index RICs first, up to eight). `pmcc/data/lseg/discovery.py` is that adapter (its pandas stops there); its table type, `DailyTable`, sits in the port module, `pmcc/data/provider.py`. lseg-data's errors come back as the port's `TransientError`, and a non-table answer (None included) as `UnreadableAnswerError`, never as an empty series. A RIC found by two searches is read once.
- **Credit on FRED:** `pmcc/thesis/fred.py`, with the standard library, a generic client name; T3-01 reuses it. First the public CSV (TD-05); since TD-17, FRED's official API with the `FRED_API_KEY` key. A day without a value (`.`) is kept as None. FRED not answering is `FredUnavailableError`, an outage; FRED refusing, or an answer that isn't the series' observations, is `FredError`. The first Actions run (2026-11-22) timed out reading the CSV at 30 s, after the LSEG sections had run, so the whole probe wrote nothing (TD-17): a request now waits up to 60 s and is tried three times, 10 s and then 30 s apart, before FRED counts as unavailable; a refusal or an unreadable answer isn't asked again.
- **SPXW (R5's cost sample, TD-07):** `pmcc/thesis/spxw.py`. The equity RIC builder caps strikes at $999.99, so index strikes are spelled here: in tenths, and, as LSEG's OPRA convention has it, with a lower-case month letter. That spelling is unproven, so the at-the-money pair is asked in four spellings (`SPXW` or `SPX`, lower or upper case) and the first LSEG lists is used for the chain. Every threshold is in `configs/thesis.yaml`'s `cost_sample` section (CLAUDE.md: every threshold in YAML): §13's options values for §6.2's contract rules, §6.3's spread test, §7.2's fee, Cboe's $100 multiplier, the rough rate, and the probe's strike step and windows. The expiry is the session 28–35 days after the next session nearest 30 (a tie earlier; since TD-19, the nearest LSEG lists); strikes 5 points apart in a window around each estimated 0.20-delta strike (VIX as the vol), puts from 94% to 104% of it and calls from 97% to 104%; bid and ask in the close bar, as the live snapshot reads them (LD-21). Deltas are Black-Scholes on the spot implied by the at-the-money pair's put-call parity (so no dividend input), IV from the mid, r a flat 4.32%: rough, and labelled so. The condor follows spec §6.2's delta, tolerance and wing rules and §6.3's spread test; its costs are §7.2's (the legs' summed spread for a natural round trip, and $2 × 8 = $16, 0.16 points). The report counts the contracts LSEG listed apart from those quoted at the close.
- **Not probed:** the contracts' settlement, exercise style and multiplier (spec §4.1, §4.3). They need LSEG's reference fields, whose names aren't known here; for a cost sample the profile rests on Cboe's SPXW specification [S5] (PM-settled, European, cash, $100). The backtesting assignment, which trades the contracts, must verify them.

### TD-15 — The thesis calendar, 2014–2027, and its business days
**Status:** ENG · **Affects:** Thesis spec §4.4, §5.2; T2-01

- **History table:** `configs/calendar_history.yaml` holds NYSE's closures and 13:00 early closes for 2014–2024, in the shipped table's schema. `pmcc.thesis.calendar.load_thesis_calendar` joins it to `configs/calendar.yaml` (2025–2027) and refuses tables that don't meet day to day. The shipped file is unchanged: `pmcc probe` reads its first day, and the backtests and the live wheel read it alone. A test checks the joined calendar against the shipped one on every day of 2025–2027.
- **Checked:** every listed day against NYSE's rules, computed independently in the tests: the fixed and Monday holidays, Good Friday from Easter, Juneteenth from 2022, Saturday holidays observed the Friday before and Sunday ones the Monday after, no closure on Dec 31 2021 for a Saturday New Year's Day, the Dec 5 2018 closure, and early closes on the day after Thanksgiving and on Jul 3 and Dec 24 when Monday to Thursday and open. The same rules reproduce 2025–2027, Carter's closure aside. Checked against the S&P 500 index's daily tape, 2014-01-02 to 2026-11-20: no session without a bar, no bar on a closed day (TD-18).
- **Business days:** a "US business day" for credit's publication lag and age (§4.4) is an NYSE session. ICE's own index calendar follows the bond market's holidays (Columbus Day, Veterans Day), so its lag can differ from this by a day around those holidays.

### TD-16 — The tracker's conventions and missing-data rules (T2-01)
**Status:** SETTLED · **Basis:** PO, 2026-11-21 (built as ENG, then the readings below put to the PO) · **Affects:** Thesis spec §4.4, §5.1–§5.5; T2-01

- **Code:** `pmcc/thesis/` (`config`, `calendar`, `features`, `outcomes`, `episodes`, `credit`, `tracker`), pure, plain Python; `run_tracker` is the entry point. `configs/thesis.yaml` holds §13's forecast, shock, normalization, credit and evidence values, loaded strictly and hashed as canonical JSON. Two keys are added so no time lives in code: `decision_time_et` and `credit.assumed_publication_time_et`, both §4.4's and §7.1's 20:30. §13's bootstrap keys and its trading sections wait for the backtest.
- **EWMA start:** `v` first exists at the 60th valid return, as the mean of the first 60 squared returns, that one included; the recursion runs from the 61st.
- **Missing closes:** a missing close removes that session's return and the next one's; nothing is forward-filled. The EWMA has no value on a session without a return and resumes from its last value at the next valid one. An RV window needs every return present. A session is warm once 252 valid returns exist.
- **Horizon:** `N_t` counts the sessions after t through t + 30 calendar days, that day included, by date, so DST and early closes don't change it. The realized outcome uses the same sessions. It is `PENDING` (null) until the horizon's last session has an index close, and `INCOMPLETE` if a return in it is missing.
- **Percentile:** linear interpolation between order statistics (numpy's default, Hyndman–Fan type 7) over the 252 sessions before t, t excluded. A shock test missing a VIX value, or on a session that isn't warm, is unknown, not false.
- **Episodes:** a window is the 10 sessions after the shock. `RV_5(t-3)` is three sessions back. A missing feature on a window session before any qualifying one makes the episode `INCOMPLETE_CANDIDATE_SEARCH`; a window running past the data is `SEARCHING`. Each episode's ID is `v1.0:{shock day}`.
- **The calendar's end:** a shock in the calendar's last 10 sessions opens an episode whose window stops at the calendar's last day; with no candidate in it, it is `SEARCHING`, noted so (a code review's fix, 2026-11-21).
- **Credit:** the comparators are the 5th and 20th usable source observations before the latest, so 21 are needed. Business days are counted on the calendar, so `credit.credit_series` builds a source's series keeping only points inside it (from 2014-01-02), and `run_tracker` refuses an observation outside it, naming it (a code review's fix). The latest may be at most 3 business days old at the session's 20:30 decision; otherwise, or with too few observations, credit is `UNAVAILABLE`, which blocks an entry without calling credit unstable. Observations must have non-decreasing `available_at` in date order, which the assumed lag gives; later vintages would need a different index.
- **Tests:** spec §14 tests 1 (data after t changes nothing known at t, checked at three cut points), 2 (credit published a day late isn't used; 3.52 → 352), 3 (repeated shocks don't extend a window; credit can't move a candidate) and 4 (a weekend, a holiday, a leap day, both DST changes, immature outcomes null).
- **Asked:** five readings of the spec: the EWMA's first value at the 60th return (not the 61st); a missing return skipped rather than restarting the 60-return initialisation; the horizon's end inclusive; `RV_5(t-3)` in sessions; credit's comparators in the source's own observations.
- **Outcome (PO):** all five accepted, with these missing-data rules, scoped to the current tracker:
  - **EWMA start-up:** accumulate 60 valid one-session returns; a gap doesn't restart the count.
  - **Returns:** each from consecutive scheduled session closes. If Tuesday's close is missing, there is no Tuesday or Wednesday return: Wednesday against Monday is a two-session return and is never used as a daily one.
  - **The session index stays intact.** RV5 and RV20 need every return in their 5- and 20-session windows; otherwise they're unavailable.
  - **Outcomes:** a matured 30-day realized variance with a required return missing is `INCOMPLETE`, never computed from the returns that remain.
  - **Weekends and exchange holidays** are expected calendar gaps, not missing data: the return across one is a single-session return.
  - **Credit:** the availability and freshness checks above apply as they are.
- **Checked:** the code already held each rule; three tests were added to pin the ones no test named: the start-up counting across a gap, RV20 unavailable across a missing return, and a holiday's return as one session.

### TD-18 — The probe's first full run, and what it changed (T1-01)
**Status:** ENG · **Affects:** Thesis spec §4.1–§4.4; TD-14, TD-15; T1-01, T2-02, T3-01

- **Run:** Actions, 2026-11-22 22:37 ET (`data_cache/probes/thesis_20261122T223713.json`, gitignored), the last close Fri Nov 20.
- **The index:** `.SPX`, 3,242 sessions from 2014-01-02 to 2026-11-20, every field on every one. Against the thesis calendar (TD-15): no session without a bar, no bar on a closed day. The 2014–2024 history table holds against the tape.
- **VIX:** `.VIX`, 3,275 bars over the same span: every index session, plus 33 on days NYSE was closed, from 2022-05-30 (Memorial Day, Juneteenth, Jul 4, Labor Day, Thanksgiving, MLK Day, Presidents' Day), when Cboe still computes the index. The tracker runs on NYSE's sessions (§4.4), and `run_tracker` refuses a value on any other day, so T3-01 keeps VIX's values on sessions only and logs how many it dropped. Nothing the spec computes uses a closed day.
- **Credit on FRED:** BAMLH0A0HYM2 through the API (TD-17), 794 rows, 786 valued, from 2023-11-21 to 2026-11-19, last 3.52 (352 bps). Three years only, as spec §4.2 warned: FRED serves ICE's series for a rolling three years.
- **Credit on LSEG:** the fourth search found `.MERH0A0`, "ICE BofA US High Yield Index", but its table wasn't read: the first six RICs across all searches went to Chord Energy bonds (from 2025) and S&P 500 Bond Index high-yield OAS indexes (`.SP5SH…O`, whose `TRDPRC_1` is a spread level in bps but which end 2022-11-29). The probe now reads each search's first three RICs, index RICs (LSEG's `.` prefix) before the rest, up to eight in all: the S&P indexes and `.MERH0A0`, `.MERH0A3`, `.MERH0A1`.
- **SPXW:** expiry Wed 2026-12-23, 30 days from Mon Nov 23; at-the-money strike 6,910. None of the four spellings (`SPXWl232669100.U` …) answered on hourly bars: a wrong spelling, a missing entitlement, or index options served only daily can't be told apart from that. The probe now asks the spellings daily if none answers hourly, and prices the condor on the first bar size that answers (a daily bar's bid and ask are its last of the day, labelled so); and it searches for SPXW (`SPXW`, `S&P 500 Index weekly option`) and asks up to eight of the RICs LSEG gives, hourly and daily.
- **Next:** a second run settles whether LSEG holds ICE's OAS with history and how SPXW is spelled or entitled; the credit source then goes to the PO if LSEG's history is short too.

### TD-19 — The probe's second run: credit from FRED, SPXW's expiry (T1-01)
**Status:** ENG · **Affects:** Thesis spec §4.1, §4.2, §6.2; TD-05, TD-14, TD-18; T1-01, T2-02, T3-01

- **Run:** Actions, 2026-11-22 23:18 ET (`data_cache/probes/thesis_20261122T231844.json`, gitignored), with TD-18's changes. The closes and FRED's answer match the first run's.
- **Credit on LSEG: not entitled.** `.MERH0A0` (ICE BofA US High Yield Index) answers `TSCC.QS.UserNotPermission.92000`, "User has no permission", and `.MERH0A3` and `.MERH0A1` answer `TS.Interday.UserNotPermission.70112`. The S&P 500 Bond Index high-yield OAS indexes end 2022-11-29 and aren't ICE's series. So, by TD-05's rule (LSEG if it holds the history, otherwise FRED), **the credit series is FRED's BAMLH0A0HYM2**, from 2023-11-21: episodes before that are `CREDIT_UNAVAILABLE`, and K1 and R5's credit cohorts show what that leaves, `INSUFFICIENT_DATA` if under the threshold (TD-08), never relaxed.
- **SPXW's spelling is proven:** LSEG's own search gives `SPXWa292777300.U` for the Jan 29 2027 7,730 call and `SPXWm292777300.U` for the put: root `SPXW`, a lower-case month letter, the strike in tenths, as `spxw.option_ric` builds it. All eight RICs checked answer the Nov 20 session, hourly and daily, so the platform session is entitled to SPXW.
- **What failed was the expiry.** The probe asked Wed Dec 23 2026, the session nearest 30 days, in every spelling, and nothing answered, while other SPXW contracts did: LSEG returned nothing for that expiry (wording corrected, TD-29). The probe had read §6.2's "an expiration 28–35 calendar days from the intended execution session, closest to 30 days" as any session. Now every session in the window is a candidate, nearest 30 first and a tie earlier (`spxw.candidate_expiries`); the at-the-money pair is asked at each, in each spelling, and the nearest expiry LSEG lists is used. That is the spec's rule as written, not a change to it.
- **Next:** a third run, for the cost sample.

### TD-20 — The probe's third run: SPXW's chain, and no spec condor that day (T1-01)
**Status:** ENG · **Affects:** Thesis spec §6.2, §6.3, §7.2; TD-07, TD-19; T1-01, T2-02

- **Run:** Actions, 2026-11-22 23:42 ET (`data_cache/probes/thesis_20261122T234215.json`, gitignored), with TD-19's change. The close it reads, Fri Nov 20, is itself a VIX spike: VIX 35.89, the index 6,910.39.
- **Expiry:** Thu Dec 24 2026, 31 days from Mon Nov 23: the third candidate. LSEG returned nothing for Dec 23 and Dec 22's pair; it answered Dec 24's, hourly, `SPXW` with a lower-case month letter.
- **The chain:** 239 contracts asked, 76 answered, all 76 quoted at the close bar and priced, 55 inside §6.3's spread test. The parity spot is 6,901.85. LSEG answered puts that far out every 25 points, not 5 (6,225, 6,250, 6,275, 6,300 …); calls near 7,400 every 5 or 10.
- **The short legs exist:** the 6,300 put at −0.201 delta (95.9 / 105.5) and the 7,400 call at 0.204 (54.7 / 61.3), both inside the spread test. IVs: puts near 0.20 delta about 40%, calls about 25%.
- **No spec condor:** §6.2 step 4's widths run from 0.005 × 6,910 ≈ 35 to 1.5 × that ≈ 52 points. The only put wing in that range is the 6,250 at 50, quoted 88.5 / 122.5: a 34-point spread, past the test's 21, and a mid above the 6,300 put's. The call side has 7,440 at 40, which the put side doesn't. So, by §6.2, the trade is skipped that day, and the probe reports no condor. Nothing was widened or rounded to make one (§6.2 step 8).
- **What the quotes do show,** for R5's cost (TD-07): legs between 0.10 and 0.30 absolute delta have median spreads of 9.65 points on puts (n = 20, 9.7% of the mid) and 8.65 on calls (n = 24, 19.6%). A natural round trip gives up about one spread a leg; the fee is $2 a contract a transaction, 0.16 points for a condor's eight.
- **T1-01 is done:** every source's coverage is shown and recorded (TD-18 to TD-20). How R5 uses these quotes is T2-02's question to the PO.

### TD-26 — The evidence and statuses' conventions (T2-02)
**Status:** ENG · **Affects:** Thesis spec §8, §9, §10; T2-02, T3-01

- **Code:** `pmcc/thesis/evidence.py` (the cohorts, the statements, K1–K3, R5's cost) and `pmcc/thesis/status.py` (the statuses, the current state), pure, on a `Tracker`.
- **Matured only:** a cohort or K1 reads a session only when its outcome is `MATURED`, with its VIX. K1's "latest 30" are the 30 latest stable-credit candidates by candidate day; below 30 it is `INSUFFICIENT_DATA`, and its mean over those available is shown as provisional (TD-08).
- **`data_status`:** `CURRENT` when `data_through` is the last session decided at the run's time (completed, until TD-29); `STALE` when older; `BLOCKED` with no data at all. Credit doesn't set it: credit unavailable blocks the signal's assessment instead (TD-25).
- **`signal_status`:** the latest episode's state while `data_through` is from its shock through its window's last session; `NO_SHOCK` otherwise. A candidate found earlier in a window still in progress keeps its eligibility as the signal.
- **`thesis_status`:** `PAUSED` while K1 is `FAIL`; otherwise `PROVISIONAL`, since K2 and K3 aren't evaluated. `run_status` is the nightly run's, set in T3-01.
- **The current state:** `data_through`'s VIX, the shock test's 80th-percentile level over the 252 sessions before and VIX's share of them at or below it, its ratio to five sessions earlier, the forecast vol and gap, RV5, RV20 and credit at the decision.

### TD-27 — `thesis run`, its file and its workflow (T3-01, T3-02)
**Status:** ENG · **Affects:** Thesis spec §10, §12; TD-09; T3-01, T3-02, T4-01

- **Command:** `thesis run` (`just thesis`), `pmcc/thesis/run.py`: `.SPX` and `.VIX` daily closes from 2014-01-01 in one batched request over the platform session; FRED's BAMLH0A0HYM2 through its API, percent to bps; then `run_tracker`, the evidence and the statuses, as of the run's time. Everything is re-derived each night and nothing is cached (TD-09). `--plan-only` prints the two requests and asks nothing. An outage, an empty series, an unreadable FRED answer, a tracker input error or a value the model refuses writes nothing and exits 1. The console prints counts and dates, no values.
- **Closed days:** closes on days the calendar has no session for are left out and counted, and the count is in the VIX source's note (TD-18).
- **One file:** `live/thesis/thesis.json`, the only file under `live/thesis/` (TD-09's glob). Its model, `pmcc.export.thesis_models.Thesis`, holds the provenance (§10: schema version, model version, config hash, `generated_at`, `data_through`, `data_status`, each source's provider, identifier, coverage and units), the statuses, the signal, the current state, the evidence (cohorts, statements, K1–K3, R5's cost), every episode, and a row per session (the closes, the forecast and RV, the matured realized vol, the outcome's status, and credit at the decision). About 3,300 rows.
- **Numbers:** canonical JSON, as the results (DEC-50): keys sorted, floats to 6 places. The model refuses NaN and infinities (`allow_inf_nan=False`), so a bad number stops the write instead of printing as null (§10). It's written to a temporary file, then moved into place.
- **Export:** `pmcc export` reads `live/thesis/thesis.json` if it exists, checks it against the model (a failure stops the export), writes it as `thesis.json`, and names it in `index.json`'s new `thesis` field. `thesis.schema.json` joins the schemas, so the page's types come from it.
- **Workflow:** `.github/workflows/thesis.yml`, as `vol.yml`: 04:17 UTC and by hand with a `plan_only` input; the LSEG secrets and `FRED_API_KEY` in the run's step alone; the Actions bot commits only `live/thesis/thesis.json` after a pull, three tries; a failed run commits nothing and stays red. `ci.yml` runs on its completion and redeploys.

### TD-29 — The thesis page, as built, and `thesis run` corrected (T4-01)
**Status:** ENG · **Affects:** TD-19, TD-20, TD-26, TD-27; Thesis spec §7.1, §9, §10; T3-01, T4-01

- **A fix: the undecided session.** `thesis run` kept every daily bar LSEG returned, and LSEG serves a day's bar while it trades. A run by hand in the day would have published an intraday price as a close, and one between the close and 20:30 a signal before spec §7.1 allows it, reading credit assumed available only at 20:30. A session whose 20:30 decision hasn't passed is now left out, and `data_status` is `CURRENT` at the last session *decided* (TD-26 said completed). The scheduled run, at 23:17 EST, was never affected, nor the first night's file.
- **Stale:** the file carries `expected_by`, noon New York the day after the next session (`configs/thesis.yaml`'s `update_due_time_et`; a scheduled run can start hours late, LD-27). A page read after it shows a stale banner, whatever the file says of itself, since a failed night leaves the last file in place (spec §9: never a falsely fresh chart).
- **New fields:** each outcome's end, each session's observation date and changes, when the latest observation became usable, and the rules' thresholds (`parameters`), so the page never retypes one. They default to null, so the first night's file still reads: the page shows dashes for them until a night writes them.
- **Copy:** spec §1's text, less its pointers to the spec's own sections and its instructions to the implementer. Every status shows in words, never its code. The R5 note's sentence sets the candidates' mean overstatement beside one leg's measured round trip, with no verdict. FRED's API notice and ICE's attribution are shown.
- **Charts:** VIX cyan, the forecast off-white and dashed, the realized violet: the palette's cyan and off-white are close for some colour-blind readers, so the dash tells them apart too. Candidates: a green circle, a red square, an off-white triangle. The zoom is a slider and a drag; the wheel scrolls the page. It opens on about two years.
- **Evidence sentences (TD-23):** "Neither credit group has a matured episode yet." is now said when that is so; it was missing.
- **Home:** four tiles, so the page widens to 1,400 px; two across at 1,100 px or less, one at 700 px or less.
- **A correction:** TD-19 and TD-20 said Dec 22 and 23 and some strikes "aren't listed". What the probe showed is that LSEG returned nothing for them; that doesn't prove Cboe lists none. Their wording is corrected. The rule used (the nearest expiry LSEG answers) and the condor's result are unchanged.
- **Checked:** rebuilding the first night's file with the new code, from its own closes and spreads, gives the same forecasts, outcomes and 56 episodes.

### TD-31 — The redesign, as built (T4-02)
**Status:** ENG · **Affects:** TD-27, TD-29, TD-30; T4-02

- **The tracker's own verdicts:** `thesis.json`'s current state gains §5.4's tests (`swings_below_long`, `swings_not_rising`, `gap_ok`, with RV5 at the comparison session) and §5.5's (`credit_level_ok`, `credit_change_short_ok`, `credit_change_long_ok`), and each condition its `required` count. §5.4's come from `episodes.checks`, the function that picks candidates, refactored out of `qualifies` with its results unchanged. They default to null, so earlier files still read.
- **Words:** `web/src/pages/thesis/assessment.ts`, pure: the state's sentence by the backend's status, two sentences on the readings, the observations with the file's verdicts ("Meets the condition", "Does not meet the condition", "Not assessed"). "Substantially more" means the gap passes its check; "only slightly more", that it is positive and doesn't.
- **The zoom:** presets of 126, 252 (the default), 756 and all sessions. The slider reports its window (`Chart`'s `onZoom`) without a redraw, so a drag isn't interrupted, and the details open on it. The slider alone zooms: the wheel and a finger scroll the page.
- **Legends** are HTML, so they wrap on a phone and name shapes in words. Chart text is 13 px.
- **Styles:** `web/src/theme/thesis.css`, all under `.th`. The rules T4-01 added to `shell.css` for spacing notes against charts and tables also moved other pages by a few pixels; they are removed.
- **The payload:** the deployed file was the first night's (Nov 23 00:59 ET), before T4-01's fields; the producer was already right, so the next `thesis` run writes them all. Until then the page says where each missing value would be.
- **Home tile:** its line uses the new labels.
