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
| LD-04 | `open_orders.json` at the repo root | SETTLED (PO) | — |
| LD-05 | The nightly job contacts LSEG | SETTLED (PO) | — |
| LD-06 | The bot commits; the site deploys after each nightly run | SETTLED (PO) | — |
| LD-07 | Limit at mid, at the open | SETTLED (PO) | — |
| LD-08 | One order a week; an unfilled week is skipped | SETTLED (PO) | — |
| LD-09 | Starting cash: $25,000, ours to track | SETTLED (PO) | — |
| LD-10 | The page's contents | SETTLED (PO) | — |
| LD-11 | How a strike is chosen | SETTLED (PO): from LSEG's chain, by us | — |
| LD-12 | NVDA in Robin, and its conid | ASK: testing (test orders placed 2026-11-13) | — |
| LD-13 | Risk-free rate for delta | ASK | L2-03 |
| LD-14 | A stale or unreadable book | ASK | L2-02 |
| LD-15 | No raw LSEG data on the page | ASK | L4-01 |
| LD-16 | The page's route and nav name | ASK | L4-01 |
| LD-17 | Sanji's files are exempt from the formatting hooks | ENG | — |
| LD-18 | ID prefixes | ENG | — |
| LD-19 | What `open_orders.json` holds; order ids | ENG | — |
| LD-20 | Code layout | ENG | — |
| LD-21 | The headless session and the close snapshot (L1-02) | ENG | — |

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

### LD-04 — `open_orders.json` at the repo root
**Status:** SETTLED · **Basis:** PO, 2026-11-13

- **Asked:** the assignment says the repo root; the order language page says `mkt/open_orders.json`.
- **Outcome:** the root. Sanji already writes `price_history.json` at our root (commits since Nov 5).

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

## Open

### LD-11 — How a strike is chosen
**Status:** SETTLED · **Basis:** PO, 2026-11-13 · **Affects:** Spec › Data, L-P3, L-C3, L-O1; L1-02, L2-03

- **Asked:** pull NVDA's chain from LSEG and compute the strike ourselves, or let Sanji pick with a token? Robin, the professor's database, isn't offered to students (class of Nov 10: he offered whitelisting, then chose each student's own headless LSEG access instead); the order page says Sanji rejects `delta:` tokens until Robin has chain snapshots; and no token says "at or above the cost basis".
- **Outcome:** the nightly job pulls NVDA's chain for the week from LSEG with the PO's headless (platform) credentials, which the PO has already used without Workspace running; it computes each strike's delta at the close with the backtests' pricer, and writes the chosen strike as a number and the expiry as a date. Sanji then only resolves a named contract. (Recommended. The alternatives were `"strike": "delta:30"` or `otm:N`.)

### LD-12 — NVDA in Robin, and its conid
**Status:** ASK · **Ask at:** L1-02 (now: the professor's answer may take a day)

- **Context:** every order names its underlying by IBKR conid, "copied from `price_history.json`", and that file tracks only SPY (756733). Whether Robin carries NVDA's stock and options, or starts to when an order names it, isn't documented. If it doesn't, an NVDA order comes back `unresolved`, whatever we pull from LSEG.
- **Conid:** NVDA's is **4815747** (Interactive Brokers' own product list: NVDA, ISIN US67066G1040, NASDAQ, USD; checked 2026-11-13).
- **Test (PO, 2026-11-13: run it, on any session):** orders that are legal but can't fill, whose outcome tells us what Robin carries. A limit buy that never trades through comes back `unfilled` if Sanji could resolve the contract, and `unresolved` if it couldn't:
  1. SPY (756733), `BUY` 1 share, limit $1.00: the control. `unfilled` shows Sanji reads our file at all.
  2. NVDA (4815747), `BUY` 1 share, limit $1.00: `unfilled` means Robin has NVDA's stock.
  3. NVDA, `BUY` 1 put, expiry 2026-11-20, strike `atm`, limit $0.01: `unfilled` means Robin has NVDA's chain, which the real put order needs.
  The three are placed twice in `open_orders.json`: for Fri Nov 13, a session Sanji had already resolved when they were written, in case a later Sanji run (one landed on Sat Nov 7) takes it; and for Mon Nov 16, which Sanji resolves for certain (about 16:30 ET). Their limits can't be reached, so neither set can fill. Each outcome lands in `fills.json`, which also shows us its format (L2-02).
- **Recommendation:** read the outcomes when they land, and ask the professor too, which may answer it sooner. Fall back to SPY only if NVDA comes back `unresolved`; SPY near $754 needs about $75,000 to secure a put, so that fallback also needs a new starting cash.

### LD-13 — Risk-free rate for delta
**Status:** ASK · **Ask at:** L2-03

- **Context:** the backtests used 3.71%, the 3-month Treasury yield before Mar 30. It moves the 0.30-delta pick only at the margin.
- **Recommendation:** the latest FRED DGS3MO, converted to continuous compounding, fixed in `configs/live.yaml` with its date. **Alternative:** keep 3.71%.

### LD-14 — A stale or unreadable book
**Status:** ASK · **Ask at:** L2-02

- **Recommendation:** if Sanji hasn't resolved the last session (L-B1) or `positions.json` doesn't map to one of the four states (L-B2), write no new order, log why, and fail the run so it shows red in Actions. Placing an order on a book we can't read risks a second short option.
- **Alternative:** assume the last state we logged.

### LD-15 — No raw LSEG data on the page
**Status:** ASK · **Ask at:** L4-01

- **Context:** in the class of Nov 10, the professor relayed the library's view that an app displaying LSEG data to the public could breach the licence: "we're not going to display it directly. We're just going to explain it."
- **Recommendation:** the live page shows our decisions (each pick's strike, expiry and delta), our orders and Sanji's files, but no LSEG bids, asks or chains. The older pages are unchanged.
- **Alternative:** also show the picked contract's bid and ask at the close.

### LD-16 — The page's route and nav name
**Status:** ASK · **Ask at:** L4-01

- **Recommendation:** `#/live/NVDA`, "Live" in the nav after the wheel's pages; the PMCC's Compare page stays the landing page.

## Engineering

### LD-17 — Sanji's files are exempt from the formatting hooks
**Status:** ENG · **Affects:** L1-01

- **Built 2026-11-13 (L1-01).** CI has failed on every Sanji push since Nov 5: CI runs pre-commit on every file, and `price_history.json` has no final newline, which `end-of-file-fixer` rejects. Sanji's files (`price_history.json`, `positions.json`, `fills.json`) are excluded from every file-fixing hook, as the raw cache is; the repo-policy test pins it. We never rewrite them.

### LD-18 — ID prefixes
**Status:** ENG

- Decisions `LD-nn`, rules `L-…` (L-B1, L-P3, L-O1), invariants `LINV-01` … `LINV-09`, backlog items `L0-01` …. None collides with the PMCC's (`DEC-nn`, `E-…`, `INV-…`, `P0-01`, `L-01` deferred items, whose form differs) or the wheel's (`WD-nn`, `W-…`, `WINV-…`).

### LD-19 — What `open_orders.json` holds; order ids
**Status:** ENG · **Affects:** Spec › Orders

- Each run keeps every order already in the file whose `for` session Sanji hasn't resolved yet (by `price_history.json`) and adds the night's new order unless its id is already there; it drops the rest, so the file is `[]` when nothing is pending. A run before Sanji resolves Monday can't drop Monday's order, and an order placed by hand (LD-12's tests) survives the nightly run. Sanji ignores orders for other sessions and never fills an id twice.
- An id is `wheel-{for}-{P|C}-{strike}`: unique, and the same on a re-run, so a second run the same night can't place a second order.

### LD-20 — Code layout
**Status:** ENG

- `pmcc/data/lseg/platform.py`: the platform session from the environment (and its fake for tests). `pmcc/live/`: the order model and writer, Sanji's file readers, the rules and the run, beside the wheel's code, which is untouched. `configs/live.yaml`: the rules. `pmcc live` (`just live`): one run. `.github/workflows/nightly.yml`: the schedule. Details are recorded at each item.

### LD-21 — The headless session and the close snapshot (L1-02)
**Status:** ENG · **Affects:** Spec › Data; L1-02, L2-03

- **Session:** `pmcc/data/lseg/platform.py`: `PlatformCredentials.from_env` reads the three variables as given, spaces included (a missing or blank one is named, never its value), and `platform_session` opens lseg-data's platform session (`Definition(app_key, GrantPassword(username, password), signon_control=True)`), makes it the default and checks it reports Opened before anything is asked. lseg-data 2.1.1's `Session.open()` returns Closed on a failed sign-in instead of raising, so the check matters; a contract test builds the real session offline and pins both its shape and that return. An error while building or opening the session is re-raised as an outage with every credential masked, as typed, URL-encoded and JSON-escaped, and without its original as the cause (LINV-09). It always closes.
- **signon_control:** `True`, as in the course's nightly job: opening takes the account's sign-on from another platform session, so a session left open elsewhere can't fail the nightly run. If that turns out to sign the PO out of something they use, it's a question for the PO.
- **The snapshot:** `pmcc/live/snapshot.py`, through the same `HistoryProvider` port and batched fetch as the backtests (single-RIC re-asks, retries, fail-soft unlisted strikes). For the last completed session: the stock's close, the last trade in the close bar (if LSEG hasn't published that bar, the snapshot stops: an earlier trade is not the close); and every put and call from 10% below the close to 10% above, in $2.50 steps, for the expiry of the week of the session after it (L-P2), each with its bid, ask and last trade in the close bar. The session after is counted from the session read, so the close and the expiry always pair; for the nightly run, after the close, it is L-S1's first session after the run's date. How L-S1 treats a run before the close is for L2-03. The band and step move to `configs/live.yaml` at L2-03. A 0.30-delta weekly sits a few percent from the money. A strike LSEG doesn't list comes back unlisted. L2-03's pick reads this snapshot.
- **The probe:** `pmcc live-probe --symbol NVDA` (`just live-probe NVDA`) writes the snapshot to `data_cache/probes/live_NVDA_{time}.json` (gitignored, never overwritten), prints counts only (LD-15), and exits 1 if no option had a valid quote at the close. `.github/workflows/live-probe.yml` runs it by hand in Actions with the repo's secrets: read-only, the secrets in that one step, the report kept as a one-day artifact. The artifact holds LSEG's quotes; the PO is fine with it as is (2026-11-13, at the code review).
