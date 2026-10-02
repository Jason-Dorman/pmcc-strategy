# PMCC Backtest — UI Spec

Sep 25, 2026 · Spec › Site and UI decides what each page shows. `DESIGN-GUIDE.md` and `theme.py` give the **baseline** look (palette, type, terminal layout), which the PO may change (DEC-40). This document ports that baseline to the spec's stack (React, Tailwind, shadcn/ui, TanStack Table, ECharts) and fixes each page's panels. A change to the look goes into the tokens and this document, in the same commit.

## 1. Identity

The baseline identity (DG §1) is a **terminal**, not a dashboard of cards:

- deep-navy ground and amber type
- dense, square-cornered panels butted against each other under one command bar
- a strip of KPI readouts across the top
- hairline rules between everything
- every number in monospace

No rounded corners, no shadows, no floating cards, no whitespace gaps. shadcn/ui components are restyled to match (DEC-71).

## 2. Building blocks

| DG block | React component | Notes |
| --- | --- | --- |
| Command bar | `CommandBar` | **Left:** the wordmark (Space Grotesk, amber, uppercase, 2px tracking); "PMCC BACKTEST" is a placeholder. **Right:** ident `NVDA · hourly · 2026-03-30 → 2026-09-25`, nav (wrapping onto a second line on a phone: seven pages, where the baseline had two), symbol select. No theme toggle: one theme (PO, DEC-03) |
| Nav | inside `CommandBar` | Compare · Baseline · Quant · Rules · Methodology · Universe · Data. Muted at rest; the current page is amber |
| Readout strip | `Readouts` | Per KPI: label (muted caps), value (amber mono, 20px), and a one-line hint defining the number |
| Panel grid | `PanelGrid` | 10 columns. Widths: 10 (full), 5 + 5, 6 + 4. A row's widths sum to 10 |
| Panel | `Panel` | **Header:** `[n]` (amber mono), NAME (display caps), note (mono muted, one line, truncated). **Body:** figure or table. **Caption:** HTML below the body |
| Table | `DataTable` | TanStack; see §5 |
| Figure | `Chart` | ECharts; see §4 |
| Prose | `Note`, `Details` | `<b>` renders amber (emphasis is chrome, not data); long reference material folds into a disclosure |
| Warning | `WarningBanner` | `NEGATIVE`-tinted box: synthetic data, schema mismatch, Reg T breach statement |
| Footer | `ManifestFooter` | Manifest of the data on screen: git SHA (linked to the commit), config / data / lock hashes (short), run time, data source |

- **Numbering:** panels holding a figure or table are numbered `[1]`, `[2]`, … in page order. Prose panels are unnumbered. Numbers are computed at render time, so the shared strategy page numbers correctly whichever sections it shows.
- **Breakpoints** (DG §4):
  - ≥ 1400px: the full 10-column grid.
  - 1101–1399px: two columns.
  - ≤ 1100px: one column.

## 3. Tokens (DEC-70)

`web/src/theme/tokens.css` is the only place colours and font stacks exist. Its values are `theme.py`'s, unchanged. There is one theme, dark: the PO kept the look identical to `DESIGN-GUIDE.md` and `theme.py`, with no light theme (PO, DEC-03). The panel chrome is `web/src/theme/shell.css`, `theme.py`'s `PAGE_CSS` ported with a `pm-` prefix (the commentary grid and the Plotly menu, which have no counterpart here, aren't); Tailwind's utilities read the tokens by name (`web/src/theme/index.css`).

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
| `MARGIN_IM` / `MARGIN_MM` | `--margin-im` / `--margin-mm` | IM / MM rulers |
| `FIT_LINE` / `IDENTITY_LINE` | `--fit-line` / `--identity-line` | OLS fit / y = x |
| chart roles (PO, DEC-04) | `--long-leg` → `--nav-line`; `--short-leg` → `--mark`; `--strategy-quant` → `--nav-line`; `--strategy-baseline` → `--mark`; `--available-funds` → `--text` | each role is `var()` of a palette colour, never a hex value; charts name the role (`tokens.ts`'s `ROLE_TOKENS`) |
| derived | `--negative-tint` / `--negative-shade` | `NEGATIVE` at 14% (a warning's ground) / 30% (available funds below zero) |
| `FONT_DISPLAY` / `FONT_BODY` / `FONT_MONO` | `--font-display` / `--font-body` / `--font-mono` | Space Grotesk / Inter / JetBrains Mono, self-hosted (DEC-72) |

**Layout constants.** `web/src/theme/tokens.ts` holds these, typed. They're consumed by components and never re-typed as literals.

| Group | Constants |
| --- | --- |
| Grid | `GRID_COLUMNS` 10; `W_FULL` 10; `W_HALF` 5; `W_HERO` 6; `W_SIDECAR` 4 |
| Breakpoints | `BREAK_TWO_COL` 1400; `BREAK_ONE_COL` 1100 |
| Figures | `PANEL_FIGURE_HEIGHT` 360; `HERO_FIGURE_HEIGHT` 600; `FIGURE_MIN_WIDTH` 520 |
| Tables | `TABLE_MIN_WIDTH` 720; `TABLE_MAX_HEIGHT` 420; `TABLE_FONT_SIZE` 11.5; `TABLE_ROW_HEIGHT` 42 (a virtualized row); `TABLE_OVERSCAN` 12 |
| Account lines | NAV 2.2px solid; IM 1.4px dashed; MM 1.2px dotted |
| Markers | mark 4; trade 6; account markers 5 |

**Not ported:** the 3D-surface, sheet, slider and menu tokens in `theme.py` (no 3D here) and `MENU_ACTIVE_BG`.

## 4. Charts (ECharts)

The baseline chart rules (DG §5–6), restated for ECharts:

1. **Base option.** Every chart starts from `baseOption(palette)` (`web/src/theme/echarts.ts`, with the palette read from `tokens.css` as the chart renders; SVG renderer, DEC-106):
   - paper `--surface`, plot `--surface-alt`, gridlines `--grid`
   - body font, mono tick labels
   - mono tooltip on `--surface` with a `--border` edge
   - `animation: false`, no toolbox, no in-canvas title (the panel header is the title)
2. **The band above the plot stays empty.** The legend goes top-left, inside the plot. Captions are HTML under the chart and can wrap.
3. **Size from tokens.** Height comes from tokens. Below `FIGURE_MIN_WIDTH` the panel body scrolls horizontally rather than squashing the chart.
4. **Amber never encodes data.** A mid is a cyan circle and a print a magenta diamond; they always differ in both colour and shape.
5. **References aren't series.** IM, MM, fit lines, y = x and zero lines are thinner and dashed or dotted, and never take a series hue.
6. **Holes render as holes.** Use `connectNulls: false`. A missing value is `null`, never interpolated.
7. **Every time series has mouseover.** An axis tooltip lists every series at that time, in mono, with the time in ET.
8. **The time axis is trading time.** It is a category axis of the result's bars (or sessions), ticked at each session's first point and labelled at each week's (`Mar 30`), so nights and weekends don't take 70% of the width. A label that would overlap the one before it (a short holiday week on a narrow chart) is left out; the first week's is always shown. A market closure is not missing data. Stacked grids share the axis and the pointer.

| Chart | Page · panel | Series and encoding |
| --- | --- | --- |
| Account | Strategy [1] | **Upper grid:** NAV (`--nav-line`, 2.2 solid), IM (`--margin-im`, dashed), MM (`--margin-mm`, dotted). **Lower grid, shared axis:** available funds (`--available-funds`), shaded `--negative-shade` below zero, zero ruler. **Tooltip:** NAV, IM, MM, available funds, excess equity, flags |
| NAV comparison | Comparison [1] | quant NAV (`--strategy-quant`), baseline NAV (`--strategy-baseline`); tooltip shows both and the difference |
| Leg attribution | Strategy [4] | cumulative long-leg P&L (`--long-leg`) vs cumulative net short premium (`--short-leg`) |
| Mid vs print | Methodology [2], [3] | points as cyan circles (x = mid, y = print); OLS fit (`--fit-line`); y = x (`--identity-line`, dashed). Shorts and longs in separate panels; R² and N in the caption |
| Greek residual | Strategy [8] (quant) | one cumulative-residual line (`--text`), beside the DEC-76 table |
| Quote browser | Data [2] (local) | BID/ASK as a band or lines, mid as cyan circles, prints as magenta diamonds |

## 5. Tables (TanStack Table)

**Style** (DG §4 and `theme.py`'s table rules):

- Hairline rules, no zebra striping; the row under the mouse lifts to `--surface-alt`.
- Sticky header, drawn with an inset shadow rather than a border.
- Mono text at 11.5px. Numbers are right-aligned with tabular figures.
- Minimum width 720px; key/value tables are exempt. Maximum height 420px, with internal scroll.

**Behaviour:**

- Every column sorts on a header click, ascending first; a missing value sorts last either way (a gate not evaluated, a week with nothing selected). A gate column sorts by status (fire, pass, n/a), then by the value its cell shows.
- Headers are set in capitals, but a lowercase Greek letter keeps its case (`L δ`; Δ means a change, as in `Cash Δ`).
- Filters are rows of toggles above the table, one per value the rows have, with its count; a row passes when it offers a toggled value, and with none on the filter is off (DEC-106). A filter over rule IDs shows what each rule did, never the ID ("Open long", "Take profit", "Event week"; `web/src/format/rule.ts`, PO, DEC-107), with the rule's condition → action on hover. Per table:
  - Blotter: Trade (by rule, multi-select) and side.
  - Gate log: outcome and Reason (the outcome's rule).
  - Ledger: flags.
- The ledger and blotter use TanStack Virtual, with fixed row heights (`TABLE_ROW_HEIGHT`, 42 px: a RIC over its OCC symbol). A chart's values in a disclosure use it too when they run to every bar.
- A blotter note is cut to one line with an ellipsis; the cell's hover shows it whole.

**Cell classes:**

| Class | Applies to |
| --- | --- |
| `num` | numbers |
| `up` / `down` | Cash Δ by the **sign of the number**; BUY / SELL in the Side column. EXPIRE and ASSIGN stay plain text |
| `skip` | the amber word on a skip outcome |
| `flag` | `--negative` for breaches and stale marks |
| `label` | a cell that names rather than measures |
| stacked | a RIC with its OCC symbol underneath, spaces preserved |

Rule cells show what the rule did in plain words (`Open long`, `Take profit`), never its ID, and link to `#/rules/<ID>` with the rule's condition → action on hover (PO, DEC-107).

**Columns:**

| Table | Columns |
| --- | --- |
| Blotter | Time (ET) · Instrument (RIC / OCC) · Side · Qty · Limit · Fill · Cash Δ · Trade P&L (a close's round trip, net of fees: its cash plus the cash its position was opened for; blank on an opening row; DEC-108) · Rule · Notes |
| Ledger | Time · Long (RIC / K · expiry) · L qty · L mark · L δ · Short (RIC / K · expiry) · S qty · S mark · S δ · Stock · Cash · NAV · IM · MM · Avail. funds · Excess eq. · Flags |
| Gate log | Session · Decision time · Selected (the option, with its δ and mid under it; RIC / OCC put to the PO, DEC-106) · one column per gate the log has, headed by what it checks (No quote, Structure, Event week, Vol premium, Min premium; DEC-107) · Outcome |

Each gate-log gate cell shows its status and the one value it's judged on, where it has one (a ratio, or G-5's mid), e.g. `pass 1.08`, `FIRE 1.32`, `pass $0.6950`, `n/a`, or `—` (not evaluated); hover shows every value, and the cell links to `#/rules/G-n`. The Outcome cell shows "sold" (linked to the rule that sold) or "skipped · <reason>", the reason in plain words and linked to its rule (DEC-107).

## 6. Pages

Readouts come first on every page, then panels in the order listed. Widths are grid columns.

### 6.1 Comparison (landing) — `#/compare/:symbol`

**Readouts:** Quant P&L · Baseline P&L · Quant − Baseline · Quant return on capital · Quant weekly-return 95% CI · Weeks traded (Q / B)

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| — | Purpose | 10 | Prose, 3–4 sentences: what a PMCC is, what the quant layer tests, how to read this page |
| 1 | NAV — baseline vs quant | 10 | overlaid NAV curves (§4) |
| 2 | Headline | 5 | rows = strategies; P&L, return on capital, max drawdown, payoff ratio, mean weekly return with 95% CI |
| 3 | Pooled universe | 5 | both strategies pooled: mean weekly return with week-block CI, total P&L, symbols where quant beat baseline |
| 4 | Ablations | 10 | quant's row, then A1–A5 against it: P&L, Δ vs quant, max drawdown, payoff, weekly-return CI (`robustness.json`, DEC-65) |

### 6.2 Strategy — `#/baseline/:symbol`, `#/quant/:symbol`

One component tree for both pages. The sections shown come from the result's `report.sections` (DEC-54); the page never checks a strategy name.

**Readouts:** Ending NAV · P&L · Return on starting NAV · Return on capital deployed · Max drawdown · Min available funds · Weeks traded / skipped

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| 1 | Account | 10 | NAV with IM and MM, available funds pane (§4) |
| 2 | Reg T | 5 | key/value: starting cash, NAV, IM, MM, available funds, excess equity, min available funds (and when), breach count. If any bar breached, a `WarningBanner` states the position couldn't have been held in a real Reg T account |
| 3 | Cycle statistics | 5 | weeks traded vs skipped (skips by reason, in plain words and linked to the rule, DEC-107); win rate; average win and loss; payoff; premium captured; weekly credit as % of long cost; exit mix (in plain words, linked) |
| 4 | Leg attribution | 10 | table: net short premium (credits, buybacks; a short open at the end, at its mark, if any), X-S5's stock P&L, and long-leg P&L (intrinsic Δ, extrinsic Δ); cumulative two-line chart (DEC-63) |
| 5 | Blotter | 10 | §5 |
| 6 | Gate log | 10 | quant only, via `report.sections`; §5 |
| 7 | Ledger | 10 | §5; virtualized; stale and breach flags |
| 8 | Greek attribution | 10 | quant only; DEC-76 table plus the cumulative-residual line, and each leg's bars wholly residual out of its bars held (DEC-63) |

The numbers above are the quant page's. The baseline page has no [6] or [8], so it renumbers at render time: Blotter is [5] and Ledger is [6].

### 6.3 Trade rules — `#/rules/:ruleId?`

The page is rendered from `rules.json` (DEC-52). Nothing on it is hand-typed.

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| — | How rules work | 10 | Prose: order of operations; the strategies differ only in selection and gates; how to read rule IDs |
| 1 | Entry rules | 10 | ID · Rule · Baseline · Quant (rendered conditions with live values); rationale expands per row |
| 2 | Skip-week gates | 10 | ID · Gate · Condition · Baseline (On/Off) · Quant (On/Off + threshold); rationale |
| 3 | Exit rules | 10 | ID · Trigger · Action; rationale (includes the spec's "why the short is never exercised / no rolls / Friday buffer") |
| 4 | Ablations | 5 | A1–A5: layer removed → replaced by |
| 5 | Sensitivity | 5 | friction, timing and grid definitions |

Arriving at `#/rules/X-S3` scrolls to that row and outlines it in `--accent`. The outline is chrome, not data.

### 6.4 Methodology — `#/methodology/:symbol?`

Panels that depend on the data follow the selected symbol and show pooled figures where they exist.

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| — | Data and RIC scheme | 5 | Prose: LSEG hourly bars, RIC grammar, caret rule, guess-and-check, cache and manifest |
| 1 | Data coverage | 5 | contracts requested / answered / unanswered, mid availability, IV failures, stale-mark rate, unavailable fields |
| — | Bar timing and look-ahead guard | 10 | Prose: the verified convention (DEC-06), decision time = bar end, MarketView's structural guarantee; the session close is the close bar's last trade, not the official closing auction (DEC-23) |
| — | Fill model | 10 | Prose + key/value: mid fills, no quote → no fill, `spread_capture`, fees |
| 2 | Mid vs print — weekly shorts | 5 | scatter of every pair + fitted line; slope, intercept, R², N, median \|print − mid\| as % of spread, the pooled fit beside them (`fill_check.json`, `pooled_fill_check.json`; DEC-64); the caveat that a print can be up to an hour older than the end-of-bar quote |
| 3 | Mid vs print — long-dated longs | 5 | as [2], for the longs (expected to fit worse, and reported whatever it shows, HR-7) |
| — | Reg T treatment | 10 | Prose with exact citations (DEC-10) |
| 4 | Friction | 5 | each strategy at `spread_capture` 0, then 0.25 and 0.50 against it: P&L, Δ, max drawdown, payoff, CI (DEC-65) |
| 5 | Entry timing | 5 | the E-T1 baseline, then each fixed Monday bar against it: P&L, Δ, max drawdown, payoff, CI; range and sample standard deviation over the fixed bars alone; large dispersion flagged as fragility (DEC-65; what counts as large is DEC-67, asked at P7-04) |
| 6 | Parameter grid | 10 | quant at its defaults, then every grid run against it: P&L, Δ, max drawdown, payoff, CI; published in full (no best cell; DEC-65) |
| 7 | Stated assumptions | 10 | key/value: r (value, source, date), q = 0, no early assignment, dividends out of scope (DEC-55), Black-Scholes on American calls, quotes not proven NBBO |

### 6.5 Universe — `#/universe`

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| 1 | Symbol suitability | 10 | symbol · long extrinsic per delta (% of spot) · median spread % (long / short) · average weekly credit after half-spread (% of long cost) · average IV ÷ RV20 · G-3 fires of the weeks it was evaluated; each measure with the weeks it's over, and a note that it's read at each week's first week-open bar from quant's picks (`universe/suitability.json`, DEC-66) |
| 2 | Headline by symbol | 10 | symbol × strategy: P&L, return on capital, max drawdown, payoff, weekly-return CI; each row links to that symbol's comparison page |
| 3 | Pooled universe | 10 | same content as Comparison [3] |

### 6.6 Data — `#/data/:symbol?` (DEC-75)

| Where | Content |
| --- | --- |
| github.io | One full-width panel: **"Data connection required"**, and one line saying raw LSEG data stays on the author's machine and is served locally by `just serve` |
| local (`pmcc serve`) | [1] Coverage by expiry and right (requested, answered, unanswered, rows, mid availability). [2] Quote browser: pick a RIC and see its BID/ASK, mid and prints (§4) |

## 7. Routes and navigation (DEC-73)

| Route | Page |
| --- | --- |
| `#/` | redirects to `#/compare/{first symbol in index}` |
| `#/compare/:symbol` | Comparison (landing) |
| `#/baseline/:symbol` | Baseline PMCC |
| `#/quant/:symbol` | Quant PMCC |
| `#/rules/:ruleId?` | Trade rules |
| `#/methodology/:symbol?` | Methodology |
| `#/universe` | Universe |
| `#/data/:symbol?` | Data |

- **Symbol selector:** in the command bar on every page. Changing it keeps the current page and swaps the symbol. Pages without a symbol remember the last one for links back.
- **Unknown symbol or missing run:** an in-panel "No results for …" state, never a blank page or a thrown error.
- **Traceability:**
  - a blotter rule ID → `#/rules/<ID>`
  - a gate-log gate → `#/rules/G-n`
  - a skip count in cycle statistics → `#/rules/<ID>`

## 8. States

| State | Trigger | Rendering |
| --- | --- | --- |
| Loading | a fetch is in flight | the panel body shows a flat `--surface-alt` block; no spinner |
| Missing run | the index lacks the run | in-panel "No results for SYMBOL / RUN" |
| Schema mismatch | `schema_version` ≠ the app's | page-level `WarningBanner` |
| Synthetic data | the index lists any run with `data_source = synthetic` (every page, since Comparison and Universe mix runs) | page-level `WarningBanner`: "Synthetic data — not market results" (DEC-74) |
| Stale mark | ledger flag | the mark cell uses `flag`, with a tooltip "last valid mid carried; never filled" |
| Negative available funds | any ledger row flagged | the Reg T panel banner, plus row flags |
| Data page on github.io | hostname ends in `github.io` | "Data connection required" |

## 9. Formatting (`web/src/format/`)

| Value | Format |
| --- | --- |
| Money | `$12,345.67`; negatives with a true minus (−); 4 dp only in audit tooltips. A P&L or a part of one shows its sign: `+$3,672.50`, `−$490.00` (zero unsigned) |
| Chart ticks (money) | `$15.2k` from a thousand up, else whole dollars (`−$850`) |
| Counts | grouped by thousands; a negative (short shares) with a true minus: `−100 sh` |
| Option prices | `$2.3450` (4 dp, as quantized) |
| Percent | 1 dp; spreads < 1% at 2 dp |
| Greeks, IV | δ 2 dp; IV as % at 1 dp |
| Time | `2026-09-14 10:00 ET` |
| Instrument | RIC on top, OCC symbol underneath (`QQQ   260918C00710000`, spaces preserved) |
| Rule IDs | mono, linked |

## 10. Responsive and accessibility checks

- **Widths:** 390, 1100, 1366 and 1600 px. Playwright captures screenshots in CI, and they are reviewed by eye at P7-08. DG §6: check the rendered page, not only the tests.
- **Contrast:** every text pairing clears AA (4.5:1), and data marks clear 3:1, on the grounds they sit on. `web/src/theme/contrast.test.ts` pins this, and that `shell.css`'s grid and breakpoints match `tokens.ts`.
- **Keyboard:** every control can be reached by keyboard, with an amber focus ring (chrome). Every chart has an HTML caption, and its values are also available in a table.
- **Token lint:** `web/src/theme/tokenlint.test.ts` fails on a hex colour, `rgb()`/`hsl()`, a font-family name, a px value, an arbitrary Tailwind value, or a unitless number in a style (which React reads as px) anywhere in `web/src/`, `index.html`, `vite.config.ts`, `eslint.config.js` and `web/scripts/`, outside `web/src/theme/`; test files are exempt, since they plant samples. Tailwind's own palette and font stacks are switched off (`index.css`), so only the tokens exist. `contrast.test.ts` also holds every token to `theme.py`'s value (DEC-03). This ports the old repo's grep test (DG §5, rule 1).
