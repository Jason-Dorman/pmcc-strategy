# The look: a guide for the coding agent

The new project must look like **Options Surface Lab** (live example:
https://jason-dorman.github.io/options-surface-lab/covered-call/). This folder brings the whole
look over. **Don't redesign it. Reuse it.**

| File | What it is | What to do |
|---|---|---|
| `theme.py` | Every colour, font, size and layout measurement, plus the page stylesheet (`PAGE_CSS`) and Plotly helpers. No imports. | Copy into the package **unchanged**. |
| `page_shell.py` | The page chrome: command bar, KPI strip, numbered panels, tables, the full HTML document. Needs only `plotly` and `theme.py`. | Copy beside `theme.py`, then edit the five site constants at the top (`WORDMARK`, `PAGE_WORDMARKS`, `SITE_PATHS`, `LOCAL_PATHS`, `NAV_LABELS`). |
| `example_page.py` | A 60-line page using every building block. `python example_page.py` writes `example_page.html`. | Read it, then delete it once the real builder exists. |

The result is one self-contained static HTML file per page. The stylesheet is inlined, and the
only external requests are the Plotly CDN and Google Fonts. It suits GitHub Pages with no backend.

## 1. The identity in one paragraph

A **terminal**: a deep-navy background, **amber type**, and dense, square-cornered panels butted
against each other under a single command bar, with a strip of KPI readouts across the top and
hairline rules between everything. There are no floating cards and no whitespace gaps. Every
number is monospace. "Bloomberg" describes the *arrangement*, not the colours.

## 2. Palette (all in `theme.py`; always use the token, never the hex)

| Token | Hex | Job |
|---|---|---|
| `BG` | `#060B16` | page background |
| `SURFACE` | `#0C1526` | panels, figure paper |
| `SURFACE_ALT` | `#111E33` | panel headers, plot interior, "no data" cells |
| `BORDER` / `GRID` | `#1B2A44` / `#1F3152` | hairlines / gridlines |
| `TEXT` | `#E8E3D9` | body text (warm off-white) |
| `TEXT_MUTED` | `#94897A` | captions, ticks, labels |
| `ACCENT` | `#FFB000` | **amber**: headings, KPI values, panel numbers, emphasis. **Never data.** |
| `MARK` | `#22E3D0` | cyan: a quoted mid / mark (circle markers) |
| `TRADE` | `#FF2E88` | magenta: an actual trade print (diamond markers) |
| `MARK_PUT` / `TRADE_PUT` | `#A78BFA` / `#3DDC84` | violet / green: the put versions |
| `POSITIVE` / `NEGATIVE` | `#2FD4A0` / `#FF4D6D` | up / down, BUY / SELL, cash in / out |
| `NAV_LINE` | `#A78BFA` | the account's NAV line (solid, 2.2px) |
| `MARGIN_IM` / `MARGIN_MM` | `#7FA8D9` / `#6E8CB8` | initial / maintenance margin (dashed / dotted, thinner) |
| `FIT_LINE` / `IDENTITY_LINE` | `#7FA8D9` / `TEXT_MUTED` | regression fit / `y = x` |
| `WARN` | `#FFB000` | warnings (shares the amber) |

All text pairings clear WCAG AA (4.5:1). Don't add a new hue without asking the user. Every free
region of the colour wheel sits close to the amber or to an existing series colour, so a "new"
colour ends up as a near-shade of one that already means something.

## 3. Typography

| Role | Font | Where |
|---|---|---|
| Display | Space Grotesk | wordmark, panel names |
| Body | Inter | prose, captions, controls |
| Mono | JetBrains Mono | **every number**: KPIs, ticks, table cells, hover |

These load from Google Fonts (`theme.GOOGLE_FONTS_LINK`, already in `PageShell.document`), and every stack falls back to a system font.

## 4. Building a page

```python
import theme as T
from page_shell import PageShell, nav_for, with_caption

shell = PageShell("Tab title", wordmark="Page Name")       # one PageShell per page, never shared
html = shell.document(
    bar=shell.command_bar("QQQ · hourly · window", nav=nav_for("index", site=False)),
    readouts=shell.readouts([("NAV", "$76,240.00", "Cash + long call − short call.")]),
    panels=[
        shell.figure_panel(1, "Account", "right-aligned note", fig, width=T.W_FULL),
        shell.panel("Blotter", "note", shell.table(cols, rows), n=2, width=T.W_FULL),
        shell.panel("Write-up", "", '<div class="osl-note">…</div>', width=T.W_FULL),  # prose: no number
    ],
)
```

- **Grid:** 10 columns. The widths are `T.W_FULL` (10), `T.W_HALF` (5), and `T.W_HERO` / `T.W_SIDECAR` (6/4). A row's widths must sum to 10, or the grid shows a hole. Below 1400px the grid goes to two columns, and below 1100px to one.
- **Panels are numbered `[n]`** when they hold a figure or table. Prose panels are unnumbered.
- **Figures:** start every layout from `T.figure_layout(...)` and use `T.axis()`, `T.legend(x=0.0, xanchor="left")` and `T.account_line("nav"|"im"|"mm")`. **Set `height=` to the panel's height** (`T.PANEL_FIGURE_HEIGHT` 360, or `T.HERO_FIGURE_HEIGHT` 600). Plotly draws at `layout.height` regardless of the box, so a taller figure paints over the panel below it.
- **Captions:** `with_caption(fig, "how to read this")`. The panel renders it as HTML that wraps. **Never put captions or titles in the band above the plot** as Plotly annotations. They collide with the legend at some screen width, every time.
- **Tables:** `shell.table(columns, rows)`. A cell is `"text"` or `("text", "css-class")`. Classes: `osl-num` for numbers (right-aligned, mono), `osl-up` / `osl-down` for BUY / SELL and positive / negative cash (class cash by the **sign of the number**, not by the side), `osl-skip` for a skip reason, `osl-flag` for a breached margin flag, `osl-label` for a name. Use `Stacked(main, sub)` for a two-line cell (a RIC with its OCC symbol underneath). Tables have a 720px minimum width and **scroll rather than squash**, so give them `W_FULL` panels. Use `kv=True` for two-column key/value tables.
- **Prose:** `<div class="osl-note">`, where `<b>` renders in amber. Use `<details class="osl-details"><summary>…</summary><div class="osl-details-body">…</div></details>` for long reference material, so the prose leads.
- **Generated data** gets a `shell.warning("…")` banner, so a page built from fake data can never pass for real.

## 5. Rules the look must not break

1. **No colour, font or pixel value outside `theme.py`.** The old repo enforced this with a test that grepped every other module for hex codes and font names. Port that test.
2. **Amber is type, never data.** No series, line or marker is amber.
3. **A mark and a print always differ in colour *and* marker shape** (cyan circle vs magenta diamond).
4. **A reference is not a series.** Margin requirements, fits, `y = x` and spot lines are thinner and dashed or muted, never a series hue or amber.
5. **Holes render as holes.** Missing data is visibly empty (`SURFACE_ALT` cell, a gap in a line with `connectgaps=False`), never interpolated over silently. Interpolation is labelled as interpolation.
6. **The band above a plot stays empty.** Captions are HTML, and the legend goes top-left inside the plot. The modebar is off (the shell does this).
7. **Keep numbers in mono and right-aligned** in tables, so decimals line up.

## 6. Pitfalls the old project hit (each one shipped at least once)

- **CSS fails open.** A missing class is silent. The width classes `.osl-w1`…`.osl-w10` are generated from `GRID_COLUMNS` in `theme.py`, so never hand-write them.
- **Check the rendered page, not only the tests.** Every bad layout defect was visible only in the built HTML. Open it, or screenshot it headlessly: `"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --window-size=1500,1000 --virtual-time-budget=8000 --screenshot=out.png file:///C:/…/page.html`. Check narrow widths too (e.g. 390, 1100, 1366).
- **Byte-reproducible output:** `page_shell` pins Plotly's JSON engine to the standard library (`JSON_ENGINE`). Leave that alone, or a machine with `orjson` installed builds a different file from CI.
- **Rebuild the page in the same commit** as any change to what it says or how it's styled, if the built HTML is committed.
- **Plotly's JSON escapes `/`** as `\/`. A CI grep for text containing `/` never matches the built page.
- **Pin `plotly`** (7.0.0 was used) and the other requirements.

## 7. For a poor man's covered call, ask the user before colouring the two legs

The old page never had two option legs in one chart. **The colours are the user's call.** Offer these options:

- **Recommended:** keep the existing roles. The account chart stays NAV / IM / MM. If a chart shows the long call's value and the short call's value separately, draw the **long call in `NAV_LINE` violet** (it's the asset) and the **short call in `MARK` cyan** (a quoted mark), with a legend. No new hue is needed.
- **Or:** long call `POSITIVE` and short call `NEGATIVE`. This is simple, but it reuses the up/down meaning, which the tables already give to BUY/SELL.

Whichever is chosen, add it as named tokens in `theme.py` (e.g. `LONG_LEG`, `SHORT_LEG`) rather than using the hex in the figure code.
