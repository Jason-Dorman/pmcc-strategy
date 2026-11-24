# UI Spec — the site's look, the live page and the thesis page

Nov 13, 2026 · The live page joins the existing site and must look like it (LD-01), as the wheel's pages did (WD-01, archived); the wheel's page layouts are in this spec's archived copy, [archive/wheel/UI-SPEC.md](archive/wheel/UI-SPEC.md). This document carries over only the **styling** from the PMCC's UI spec, now archived in [archive/pmcc/UI-SPEC.md](archive/pmcc/UI-SPEC.md); the PMCC's page layouts stay there. Section numbers match the archived spec's, so the web code's styling citations (`UI-SPEC §3`, `§10`) still point at the same topics. `DESIGN-GUIDE.md` (DG) and `theme.py` are the baseline look; a change to the look goes into `web/src/theme/` and this document in the same commit.

## 1. Identity

A **terminal**, not a dashboard of cards:

- deep-navy ground and amber type
- dense, square-cornered panels butted against each other under one command bar
- a strip of KPI readouts across the top
- hairline rules between everything
- every number in monospace

No rounded corners, no shadows, no floating cards, no whitespace gaps. Two pages break from it by the PO's choice, each in its own scoped stylesheet: Home (LD-37) and the thesis page (TD-30). shadcn/ui components are restyled to match. One theme, dark; no theme toggle.

## 2. Building blocks

| Block | React component | Notes |
| --- | --- | --- |
| Command bar | `CommandBar` | **Left:** the wordmark, "Algo Trading Strategies" (display font, amber, uppercase, tracked), a link to the home page. **Right:** the nav, wrapping on a phone. No ident line and no symbol select: every strategy runs on NVDA alone (PO, LD-36) |
| Nav | `CommandBar`, `NavMenu` | A menu per strategy, in this order (PO, LD-36, TD-28): **Volatility Thesis** (one page, Overview, so a plain link to it); **Wheel forward test** (PO, LD-38; one page, Overview, so a plain link to it); **Wheel backtest** ▾ Wheel, Wheel review; **PMCC backtest** ▾ Compare, Baseline, Quant, Rules, Methodology. Universe and Data are in no menu; their routes still work. A menu is a disclosure: a button showing a list of links under it, closed by a link, Escape, or a click or focus outside. Muted at rest; the current strategy's entry and the current page in its list are amber |
| Strategy label | `AppShell` | Under the bar on every page but home: the page's strategy and name, `PMCC BACKTEST › QUANT` (mono caps, muted; the page's name in text, the › amber) (PO, LD-36) |
| Readout strip | `Readouts` | Per KPI: label (muted caps), value (amber mono), and a one-line hint defining the number |
| Panel grid | `PanelGrid` | 10 columns. Widths: 10 (full), 5 + 5, 6 + 4. A row's widths sum to 10 |
| Panel | `Panel` | **Header:** `[n]` (amber mono), NAME (display caps), note (mono muted, one line, truncated). **Body:** figure or table. **Caption:** HTML below the body |
| Table | `DataTable` | TanStack; see §5 |
| Figure | `Chart` | ECharts; see §4 |
| Prose | `Note`, `Details` | `<b>` renders amber (emphasis is chrome, not data); long reference material folds into a disclosure |
| Warning | `WarningBanner` | `NEGATIVE`-tinted box: synthetic data, schema mismatch |

- **Numbering:** panels holding a figure or table are numbered `[1]`, `[2]`, … in page order, computed at render time. Prose panels are unnumbered.
- **Breakpoints:** ≥ 1400px the full 10-column grid; 1101–1399px two columns; ≤ 1100px one column.
- **Copy:** a rule is named by what it does ("Put assigned"), never by its ID; IDs appear only in ID columns. Greeks are named in words, never symbols. These two, and rule cells in plain words (§5), are the PMCC PO's content choices, kept for the wheel by its PO (WD-22). A wheel rule links to its row on the wheel review page.

## 3. Tokens

`web/src/theme/tokens.css` is the only place colours and font stacks exist; its values are `theme.py`'s. No hex colour, font name or px literal appears outside `web/src/theme/`.

| theme.py | CSS variable | Role |
| --- | --- | --- |
| `BG` | `--bg` | page ground |
| `SURFACE` | `--surface` | panels, chart paper |
| `SURFACE_ALT` | `--surface-alt` | panel headers, plot interior, empty cells |
| `BORDER` / `GRID` | `--border` / `--grid` | hairlines / gridlines |
| `TEXT` / `TEXT_MUTED` / `TEXT_INVERSE` | `--text` / `--text-muted` / `--text-inverse` | body / captions, ticks, labels / type on amber |
| `ACCENT` / `ACCENT_DIM` | `--accent` / `--accent-dim` | amber type and chrome. **Never data.** |
| `MARK` / `TRADE` / `TRADE_EDGE` | `--mark` / `--trade` / `--trade-edge` | a mid (circle) / a trade print (diamond) / the diamond outline |
| `POSITIVE` / `NEGATIVE` | `--positive` / `--negative` | BUY / SELL, cash in / out, gains / losses |
| `WARN` | `--warn` | skip reasons (words only) |
| `NAV_LINE` | `--nav-line` | the NAV series |
| `FIT_LINE` / `IDENTITY_LINE` | `--fit-line` / `--identity-line` | OLS fit / y = x |
| chart roles | `var()` of a palette colour, named in `tokens.ts`'s `ROLE_TOKENS` | charts name a role, never a colour. The wheel's NAV chart adds `--spot-line` (TEXT), `--strike-line` (MARGIN_IM) and `--basis-line` (IDENTITY_LINE) (WD-32); the live page's volatility adds `--iv-line` (MARK: implied vol, a quoted mark's) and `--rv-line` (NAV_LINE: the stock's realized) (LD-33); the thesis's tracker adds `--vix-line` (MARK), `--forecast-line` (TEXT, always dashed), `--realized-line` (NAV_LINE), `--gap-line` (TEXT_MUTED), `--credit-line` (MARK), `--threshold-line` (MARGIN_IM, a dashed reference), `--eligible-mark` (POSITIVE, a circle), `--filtered-mark` (NEGATIVE, a square) and `--unavailable-mark` (TEXT, a triangle) (TD-28, TD-29) |
| derived | `--negative-tint` / `--negative-shade` / `--shares-shade` / `--vol-gap-shade` / `--move-shade` | `NEGATIVE` at 14% (a warning's ground) / 30% (a shaded breach); `NAV_LINE` at 14% (the wheel's bars holding shares, WD-32); `MARK` at 14% (the live page's gap between IV and RV20, LD-33); `TEXT` at 9% (the skew's expected move, neutral, LD-41). The thesis adds `--window-shade` (`TEXT` at 7%: a spike's search window), `--no-credit-shade` (`MARGIN_IM` at 14%: no credit data) and `--unstable-shade` (`NEGATIVE` at 18%: credit unstable) (TD-28) and `--pending-shade` (`NAV_LINE` at 10%: 30-day outcomes pending) (TD-32) |
| `FONT_DISPLAY` / `FONT_BODY` / `FONT_MONO` | `--font-display` / `--font-body` / `--font-mono` | Space Grotesk / Inter / JetBrains Mono, self-hosted |

**Layout constants** live typed in `web/src/theme/tokens.ts` and are never re-typed as literals: the grid (`GRID_COLUMNS` 10, `W_FULL`, `W_HALF`, `W_HERO`, `W_SIDECAR`), breakpoints, figure heights (`PANEL_FIGURE_HEIGHT`, `HERO_FIGURE_HEIGHT`, `FIGURE_MIN_WIDTH`), table sizes (`TABLE_MIN_WIDTH`, `TABLE_MAX_HEIGHT`, `TABLE_FONT_SIZE`, `TABLE_ROW_HEIGHT`, `TABLE_OVERSCAN`), account line weights and marker sizes.

## 4. Charts (ECharts)

1. **Base option.** Every chart starts from `baseOption(palette)` (`web/src/theme/echarts.ts`, SVG renderer): paper `--surface`, plot `--surface-alt`, gridlines `--grid`; body font, mono tick labels; mono tooltip on `--surface` with a `--border` edge; no animation, no toolbox, no in-canvas title (the panel header is the title).
2. **The band above the plot stays empty.** The legend goes top-left, inside the plot. Captions are HTML under the chart.
3. **Size from tokens.** Below `FIGURE_MIN_WIDTH` the panel body scrolls horizontally rather than squashing the chart.
4. **Amber never encodes data.** A mid is a cyan circle and a print a magenta diamond; they differ in both colour and shape.
5. **References aren't series.** Fit lines, y = x and zero lines are thinner and dashed or dotted, and never take a series hue.
6. **Holes render as holes.** `connectNulls: false`; a missing value is `null`, never interpolated.
7. **Every time series has mouseover.** An axis tooltip lists every series at that time, in mono, with the time in ET.
8. **The time axis is trading time.** A category axis of the result's bars (or sessions), ticked at each session's first point and labelled at each week's; nights and weekends take no width. Stacked grids share the axis and the pointer. A chart over years (the thesis's) is ticked and labelled by month, `Nov 2026`, over a zoom slider; the mouse wheel scrolls the page, never the zoom.

## 5. Tables (TanStack Table)

**Style:** hairline rules, no zebra striping; the row under the mouse lifts to `--surface-alt`. Sticky header drawn with an inset shadow. Mono text; numbers right-aligned with tabular figures. Minimum width `TABLE_MIN_WIDTH` (key/value tables exempt); maximum height `TABLE_MAX_HEIGHT` with internal scroll.

**Behaviour:**

- Every column sorts on a header click, ascending first; a missing value sorts last either way.
- Headers in capitals; Δ means a change (`Cash Δ`).
- Filters are rows of toggles above the table, one per value present, with its count. A filter over rule IDs shows what each rule did, never the ID, with the rule's condition → action on hover.
- Long tables (ledger, blotter) are virtualized with fixed row heights (`TABLE_ROW_HEIGHT`: a RIC over its OCC symbol).
- A long note is cut to one line with an ellipsis; hover shows it whole.

**Cell classes:**

| Class | Applies to |
| --- | --- |
| `num` | numbers |
| `up` / `down` | Cash Δ by the sign of the number; BUY / SELL in the Side column. EXPIRE and ASSIGN stay plain |
| `skip` | the amber word on a skip outcome |
| `flag` | `--negative` for breaches and stale marks |
| `label` | a cell that names rather than measures |
| stacked | a RIC with its OCC symbol underneath, spaces preserved |

Rule cells show what the rule did in plain words and link to that rule.

## 6. Pages

### Home — `#/` (PO, LD-36, LD-37)

A modern break from the terminal look, on this page alone (PO, LD-37): no readouts, no panel chrome, no strategy label; rounded, layered tiles over a slowly moving backdrop. Its styles are `web/src/theme/home.css`, every colour a token or a mix of tokens.

- **Backdrop:** three large blurred lights in the palette's amber, cyan and violet (`--accent`, `--mark`, `--nav-line`) drifting slowly behind the page, and a faint grid fading out from the top, drifting too. Decoration only: it shows no data. Still when the system asks for reduced motion.
- **Headline:** an eyebrow (`NVDA · OPTIONS · LSEG DATA`, mono caps), the title "Harvesting the volatility risk premium." in the display font ("volatility risk premium." an amber → cyan → violet gradient), the subtitle "Systematic options strategies" (PO, LD-37), and a pill with a green dot: "Last nightly run …" from the run log's last row (PO, LD-38).
- **Tiles**, four across (two at ≤ 1100px, one at ≤ 700px), the thesis first, then the forward test (PO, TD-28). Each: a kicker (mono caps: "Forward test · nightly", or "Backtest · Mar 30 – Sep 25"), the strategy's name linking to its first page, one big amber figure, a mono detail line, one sentence on what it does, and its pages as pill links. A tile lifts and its edge turns amber on hover or focus.

| Tile | Figure | Detail | From |
| --- | --- | --- | --- |
| Volatility Thesis (kicker "Daily thesis tracker") | VIX minus the 30-day forecast, signed, with "volatility points" under it; "Unavailable", never zero, without one (PO, TD-28) | the signal in words, the data-through date, and "Stale: an update is overdue" when it is; its sentence says the gap isn't an expected trading return | `thesis.json` |
| Wheel forward test | this week's trade as a story (PO, LD-38): `Selling a $155 put`, the open order's option as LSEG picked it (LD-35), a step smaller than the other figures so it fits a line; "No trade open" when there's none | `Delta −0.32 · IV 88.2% · expires Nov 20`, the pick's at the close | `live.json` |
| Wheel backtest | its P&L | its return and Sharpe | `live.json`'s `backtest` |
| PMCC backtest | the baseline's P&L | the baseline's return, quant's P&L | `universe/headline.json` |

A tile's figure is "—" while its file loads or if it's missing; its links always show.

**PMCC pages:** unchanged; their layouts are in the archived spec. Each now carries the strategy label (§2).

**Wheel pages:** unchanged; their layouts are in the wheel's archived copy of this spec, [archive/wheel/UI-SPEC.md](archive/wheel/UI-SPEC.md) §6 (LD-01).

**Live page** (PO, LD-10; route and name: PO, LD-16; built at L4-01, LD-28). Readouts first, then panels in the order listed. Widths are grid columns; a prose panel is unnumbered. Its data is `live.json`. It shows each pick's quote at the close (PO, LD-15).

### Live — `#/live/:symbol` (LD-16)

**Readouts:** State (Cash, Put, Shares, Call, in words) · Cash · Cost basis (while shares are held) · Next session · Tonight's decision (an order, or no order and why) · Last run (its time, and a flag if the last run failed or the book was stale)

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| — | The algorithm | 10 | Prose, the PO's own account in the first person (PO, LD-40): what the wheel does each week; why it was chosen; the two ideas it tests, earnings weeks kept to test them; the two nightly workflows; why it was chosen, with the backtest's result and a link to `#/wheel-review/NVDA` (Spec › Why the wheel); a line pointing to the rules, the last panel (PO, LD-35) |
| 1 | Open orders | 10 | `open_orders.json` as the nightly run left it: a table (id, for, action, qty, contract, expiry, the strike and delta LSEG gave the run at the close, from the run log, "—" when no row matches (PO, LD-35), the strike as sent, limit, ref), the table alone (PO, LD-35); "No open orders tonight" for `[]` |
| 2 | Implied against realized | 5 | `live/vol.jsonl` (PO, LD-33): ATM IV about 30 days out (`--iv-line`) and RV20 (`--rv-line`) by session on the trading-time axis, the gap between them shaded (`--vol-gap-shade`), a hole where either is missing; the y axis in whole percents with room above for the legend; the tooltip gives both, the gap in points and the expiry and strike; the values in a table under it, newest first; "No volatility pulled yet" before the first |
| 3 | This week's skew | 5 | `live/smile.json` (PO, LD-33; named a skew, PO, LD-39): each out-of-the-money strike's IV at the last close, by strike, in `--iv-line` with markers; the close a solid reference (`--spot-line`) and the open order's strike a dashed line (`--strike-line`, labelled "Order"), when an order expires on the skew's date (PO, LD-43; it was L-P3's pick from that close), each labelled inside the plot; the expected move a band from close − straddle to close + straddle (`--move-shade`, labelled "Expected move") and a line under the chart: `Expected move by Nov 20: ±$8.45 (±5.6%), $142.41 to $159.31: the price of the $150.00 straddle at the close. The order's $155.00 put is 2.7% above the close, in the money, inside the move.` ("No expected move for this close" without a straddle) (PO, LD-41); the tooltip gives the right, IV and delta; the values in a table under it; "No skew pulled yet" before the first; the caption, the PO's (PO, LD-40), says what the chart shows, what IV means for the premium sold and the risk taken, and what the dashed strike is |
| 4 | Positions | 5 | Sanji's `positions.json` as written (a file block), until L5-01 knows its rows: then each holding as a row, and cash; "No positions yet" before the first fill |
| 5 | Fills | 5 | Sanji's `fills.json` as written, until L5-01: then a blotter (PO, LD-30), each fill as a row, newest first, joined to the night and order that placed it: time, contract, side, quantity, limit, fill, outcome (filled, unfilled, unresolved, rejected), cash change, the rule, and once settled its P&L; "No fills yet" before the first |
| 6 | Nightly run log | 10 | one row per run, newest first: run time, the session planned, state, cash, outcome, rule, why, the option picked at the close, the strike sent (LD-29), its delta and IV, and its bid, ask, mid and spread at the close ("—" on rows logged before them, PO, LD-15) |
| 7 | The rules | 10 | `configs/live.yaml`'s rules, each in words with its ID, as a table; last on the page (PO, LD-35) |

### Thesis — `#/thesis` (PO, TD-30; T4-02, TD-31)

A reading page, its own break from the terminal look (as Home's is): `web/src/theme/thesis.css`, every rule under `.th`, every colour a token. A centred column up to 720 px for prose, 1,120 px for charts, cards and tables (`.th-wide`); 17 px body text, display-font headings, captions at 15 px; rounded surfaces, space between sections, few rules. On a phone everything stacks and nothing scrolls sideways outside a detailed table. From `thesis.json`; the idea and the macro paragraph need no file.

In order, each a named section, with a contents list that moves focus to one:

1. **The idea:** the eyebrow ("a hypothesis being investigated"), the title, the one-sentence thesis, the explanation, three horizons and the note that two are planning estimates.
2. **Latest assessment:** the headline (the backend's signal state in words), one or two sentences on the latest readings, the state's own dates (leading when it is about an earlier qualifying observation), three observations (pricing gap, market swings, credit conditions) each with the tracker's verdict as an icon and words; the feed's freshness, data-through date, last update and next expected. Then VIX, volatility point and basis point defined, why credit matters, and "Explore credit conditions": the rule broken in words, the spread with its limit and its not-stable and unavailable sessions shaded apart, the three checks, the dates, the values, the attribution.
3. **How much volatility was priced in—and what followed?** One chart: VIX, our forecast (dashed) and the actual volatility of the following 30 days at its origin date, blank until complete, the sessions still pending shaded faintly with "30-day outcomes still pending" in the band above the plot while they are in range (TD-32); its unit above it; presets (6 months, 1 year, the default, 3 years, all) and a slider; an HTML legend. "Show signal details" adds, on the same axis and zoom, the search windows, the gap's pane (in volatility points, so labelled) with its threshold, and the qualifying observations by shape and colour. The tooltip gives the window's first day and the day it became known. "View daily observations" and "View volatility spikes and qualifying observations" hold the tables.
4. **Preliminary historical evidence:** stable and unstable credit, each with its completed count and average gap; the sample's limits and the observations left out, beside them; "Explore the historical observations" holds every group and observation.
5. **What would invalidate the thesis:** three stacked cards, each the plain condition, the sample it needs and one assessment statement; the value, its unit and date, and the exact formula in its disclosure (TD-32).
6. **Potential return and trading costs:** the observed volatility gap (stable credit first, then the broader comparison) and the estimated cost apart, each with its unit and denominator (TD-32); "Cost assumptions and limitations".
7. **Macro conditions.**
8. **Methodology, sources and detailed data:** each behind a named disclosure.

A value the file lacks is said to be missing where it would be ("Not in this file", "Not measured yet", "Pending"); never zero, never a failed check. Stale says the data feed is out of date, and nothing about the evidence. Disclosures are native `details`, opened by keyboard.

## 7. Routes

Hash routing (GitHub Pages has no SPA fallback); the URL is the state. The PMCC's routes are in the archived spec; the wheel adds two (PO, WD-22). `#/` is the home page (PO, LD-36); it used to open the PMCC's Compare page:

| Route | Page |
| --- | --- |
| `#/wheel/:symbol` | Wheel; `?bar=<the bar's end time>` chooses the portfolio's bar |
| `#/wheel-review/:symbol/:ruleId?` | Wheel review; a wheel rule's link lands on its row |

Every wheel rule named on the wheel pages (blotter, gate log, cycle statistics, filters) links to `#/wheel-review/:symbol/<ID>`.

The live assignment adds one (PO, LD-16), the "Wheel forward test" entry first in the nav (PO, LD-36, LD-38), its page named Overview:

| Route | Page |
| --- | --- |
| `#/live/:symbol` | Live |

The thesis adds one, first in the nav (PO, TD-28):

| Route | Page |
| --- | --- |
| `#/thesis` | Thesis |

## 8. States

| State | Rendering |
| --- | --- |
| Loading | the panel body shows a flat `--surface-alt` block; no spinner |
| Missing run | in-panel "No results for SYMBOL / RUN" |
| Schema mismatch | page-level `WarningBanner` |
| Synthetic data | page-level `WarningBanner`: "Synthetic data — not market results" |
| Stale tracker | in the thesis page's latest assessment, "Data feed out of date: an update is overdue or failed", with its dates; repeated under the tracker's chart (TD-29, TD-30) |
| Stale mark | the mark cell uses `flag`, with a tooltip "last valid mid carried; never filled" |

## 9. Formatting (`web/src/format/`)

| Value | Format |
| --- | --- |
| Money | `$12,345.67`; negatives with a true minus (−); a P&L shows its sign: `+$3,672.50`, `−$490.00` (zero unsigned) |
| Chart ticks (money) | `$15.2k` from a thousand up, else whole dollars |
| Counts | grouped by thousands; `100 sh` |
| Option prices | `$2.3450` (4 dp) |
| Percent | 1 dp; spreads < 1% at 2 dp |
| Greeks, IV | delta 2 dp; IV as % at 1 dp |
| A vol difference, a spread, a premium (the thesis) | `+11.9 pts`; `347 bps`, a change `+17 bps`; `+0.0019`, 30-day total variance |
| Time | `2026-09-14 10:00 ET` |
| Instrument | RIC on top, OCC symbol underneath, spaces preserved |

## 10. Responsive and accessibility checks

- **Widths:** 390, 1100, 1366 and 1600 px, screenshotted by Playwright and reviewed by eye.
- **Contrast:** every text pairing clears AA (4.5:1) and data marks 3:1; `web/src/theme/contrast.test.ts` pins it.
- **Keyboard:** every control reachable, with an amber focus ring. Every chart has an HTML caption and its values in a table.
- **Token lint:** `web/src/theme/tokenlint.test.ts` fails on any hex colour, `rgb()`/`hsl()`, font name, px value, arbitrary Tailwind value or unitless style number outside `web/src/theme/`.
