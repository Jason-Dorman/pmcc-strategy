# Decisions — Live Wheel

Nov 13, 2026 · companion to the [Live spec](LIVE-SPEC.md), the source of truth for the live assignment

The user is the product owner (PO). This log tracks what the spec leaves open, the PO's answers, and engineering choices. It starts fresh for the live assignment; the PMCC's log (`DEC-nn`) and the wheel's (`WD-nn`) are archived in [archive/pmcc/DECISIONS.md](archive/pmcc/DECISIONS.md) and [archive/wheel/DECISIONS.md](archive/wheel/DECISIONS.md) and decide nothing here (LD-01). Entries are `LD-nn`, so they never collide with a citation in the older code.

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
- **Copy (ENG, the PO's to change):** the headline "Selling premium, one week at a time.", since both strategies sell a weekly option; the lede "A wheel that trades live every night, and the two backtests that led to it."
- **Styles:** `web/src/theme/home.css`, colours only as tokens or `color-mix` of tokens, so no new palette value.
