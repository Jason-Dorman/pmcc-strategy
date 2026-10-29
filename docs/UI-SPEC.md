# UI Spec — the site's look, and the wheel's pages

Oct 26, 2026 · The wheel's pages join the existing site and must look like it (WD-01). This document carries over only the **styling** from the PMCC's UI spec, now archived in [archive/pmcc/UI-SPEC.md](archive/pmcc/UI-SPEC.md); the PMCC's page layouts stay there. Section numbers match the archived spec's, so the web code's styling citations (`UI-SPEC §3`, `§10`) still point at the same topics. `DESIGN-GUIDE.md` (DG) and `theme.py` are the baseline look; a change to the look goes into `web/src/theme/` and this document in the same commit.

## 1. Identity

A **terminal**, not a dashboard of cards:

- deep-navy ground and amber type
- dense, square-cornered panels butted against each other under one command bar
- a strip of KPI readouts across the top
- hairline rules between everything
- every number in monospace

No rounded corners, no shadows, no floating cards, no whitespace gaps. shadcn/ui components are restyled to match. One theme, dark; no theme toggle.

## 2. Building blocks

| Block | React component | Notes |
| --- | --- | --- |
| Command bar | `CommandBar` | **Left:** the wordmark (display font, amber, uppercase, tracked). **Right:** the ident (symbol · bar size · window), the nav (wrapping on a phone), the symbol select |
| Nav | inside `CommandBar` | Muted at rest; the current page is amber. The wheel's two entries, Wheel and Wheel review, follow Quant (PO, WD-22) |
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
| chart roles | `var()` of a palette colour, named in `tokens.ts`'s `ROLE_TOKENS` | charts name a role, never a colour. The wheel's NAV chart adds `--spot-line` (TEXT), `--strike-line` (MARGIN_IM) and `--basis-line` (IDENTITY_LINE) (WD-32) |
| derived | `--negative-tint` / `--negative-shade` / `--shares-shade` | `NEGATIVE` at 14% (a warning's ground) / 30% (a shaded breach); `NAV_LINE` at 14% (the wheel's bars holding shares, WD-32) |
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
8. **The time axis is trading time.** A category axis of the result's bars (or sessions), ticked at each session's first point and labelled at each week's; nights and weekends take no width. Stacked grids share the axis and the pointer.

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

**PMCC pages:** unchanged; their layouts are in the archived spec.

**Wheel pages** (PO, WD-22; built at W4-01, WD-32). Their headings carry no number, so the PMCC code's `§6.n` citations still mean the archived spec's pages. Readouts come first on every page, then panels in the order listed. Widths are grid columns; a prose panel is unnumbered.

### Wheel — `#/wheel/:symbol?bar=`

**Readouts:** Ending NAV · P&L (from the starting cash) · Return on starting cash · Sharpe (annualized; from N daily returns) · Max drawdown ($, and its %) · Complete cycles (and one open at the end) · Weeks sold / skipped (of N)

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| 1 | NAV | 10 | NAV, shaded (`--shares-shade`) over the bars holding shares; a lower pane of the stock's last trade (`--spot-line`), the held option's strike (`--strike-line`, dashed step) and the cost basis (`--basis-line`, dotted step); the chosen bar a thin `--accent` rule on both. A click on either pane picks the bar under it |
| 2 | Portfolio at a bar | 6 | ◀, a session select, a bar select, ▶; then key/value: the bar, what is held (in words), the stock's last trade, cash, reserved for the put, free cash, shares at their mark, the short put and the short call (contracts × RIC, OCC, strike and expiry, mark with its value to the book, delta; a stale mark in `flag`), the cost basis per share, NAV, flags. Opens on the URL's `?bar=`, else the last bar |
| 3 | Cycle statistics | 4 | key/value: weeks sold / skipped; skips by reason (in plain words, linked); puts sold, expired and assigned; calls sold, expired and called away; complete cycles (and one open); premium; the share of bars in each state |
| 4 | Blotter | 10 | §5, with Trade P&L on the closing rows (WD-28); filters by rule (in words) and side |
| 5 | Gate log | 10 | per week: session, put or call, decision time, the option picked (delta against its target, mid, spread), outcome (sold, or skipped and the rule, linked), notes |
| 6 | Ledger | 10 | §5, virtualized: time (a button that picks the bar for [2], the chosen row outlined in `--accent`), what is held, stock, cash, reserved, free cash, shares, each short leg with its mark and delta, cost basis, NAV, flags; filters by what is held and by flag |

### Wheel review — `#/wheel-review/:symbol/:ruleId?`

**Readouts:** Claims met (n of 3) · P&L · Return on starting cash (the S&P 500's in the hint) · Sharpe (the baseline PMCC's in the hint) · Prints inside the quote (of N prints)

| # | Panel | Width | Content |
| --- | --- | --- | --- |
| — | Thesis | 10 | Prose: the thesis word for word as fixed (Spec › Thesis), then how many claims the results meet, each named |
| 1 | Verdicts | 10 | per claim: the thesis's words, its test, the wheel's number, the benchmark's, Met or Not met (in `flag`) |
| 2 | Benchmarks | 10 | the wheel, the baseline PMCC and the S&P 500's price return: starting cash, return, Sharpe, max drawdown %; the caption names the baseline's run and config and the index's closes and source |
| — | Fill model | 10 | Prose and key/value: fills at the mid, the spread capture and fee the run used, assignment at the strike, r, the options sold, the share of prints inside the quote and R² over all of them |
| 3 | Mid vs print — puts | 5 | the methodology scatter (§4) of every put pair, its fit (the symbol's column alone) with the share of prints inside the quote, and every pair in a disclosure |
| 4 | Mid vs print — calls | 5 | as [3], for the calls |
| 5 | Friction runs | 10 | one row per wheel run by spread capture, at mid first ("reference"): P&L, Δ against at mid, return, Sharpe, max drawdown, which claims are met |
| 6 | Rules | 10 | the config's rules in order: ID · Rule (its question) · What happens (its summary, the rule stated exactly on hover); ▸ opens the reasoning. `:ruleId` scrolls to that row and outlines it in `--accent`; an ID the results lack says so |

## 7. Routes

Hash routing (GitHub Pages has no SPA fallback); the URL is the state. The PMCC's routes are in the archived spec; the wheel adds two (PO, WD-22), and `#/` still opens the PMCC's Compare page:

| Route | Page |
| --- | --- |
| `#/wheel/:symbol` | Wheel; `?bar=<the bar's end time>` chooses the portfolio's bar |
| `#/wheel-review/:symbol/:ruleId?` | Wheel review; a wheel rule's link lands on its row |

Every wheel rule named on the wheel pages (blotter, gate log, cycle statistics, filters) links to `#/wheel-review/:symbol/<ID>`.

## 8. States

| State | Rendering |
| --- | --- |
| Loading | the panel body shows a flat `--surface-alt` block; no spinner |
| Missing run | in-panel "No results for SYMBOL / RUN" |
| Schema mismatch | page-level `WarningBanner` |
| Synthetic data | page-level `WarningBanner`: "Synthetic data — not market results" |
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
| Time | `2026-09-14 10:00 ET` |
| Instrument | RIC on top, OCC symbol underneath, spaces preserved |

## 10. Responsive and accessibility checks

- **Widths:** 390, 1100, 1366 and 1600 px, screenshotted by Playwright and reviewed by eye.
- **Contrast:** every text pairing clears AA (4.5:1) and data marks 3:1; `web/src/theme/contrast.test.ts` pins it.
- **Keyboard:** every control reachable, with an amber focus ring. Every chart has an HTML caption and its values in a table.
- **Token lint:** `web/src/theme/tokenlint.test.ts` fails on any hex colour, `rgb()`/`hsl()`, font name, px value, arbitrary Tailwind value or unitless style number outside `web/src/theme/`.
