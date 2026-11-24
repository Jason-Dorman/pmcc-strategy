// The volatility thesis's charts (UI-SPEC §6 › Thesis; PO, TD-28, TD-30). Their legends are HTML
// beside them (`pages/thesis/`), so they wrap on a phone and name each shape in words.
//
// The default chart: VIX, our forecast, and the volatility of the following 30 days, plotted at
// the day it is measured from and blank until its window completes.
//
// With the signal details: the same lines over each spike's search window, shaded faintly, and a
// second pane, on the same date axis and zoom, of VIX minus the forecast with the rule's threshold
// and each qualifying observation, its credit told by shape and colour; the years without credit
// data shaded and labelled.
//
// The credit spread: as known at each session's decision, its level limit a dashed reference, the
// sessions credit was not stable and the ones it was unavailable shaded apart.
import { iv, orDash } from "../../format/number";
import { bps, bpsChange, creditLabel, eligibilityLabel, volPts } from "../../format/thesis";
import {
  baseOption,
  lineSeries,
  LINE,
  PANE_TICKS,
  plotGrid,
  READING_FONT,
  ruler,
  valueAxis,
  zoom,
  ZOOM_GRID,
  ZOOM_PANES,
  type Palette,
} from "../../theme/echarts";
import { SIZE_MARK } from "../../theme/tokens";
import type { ThesisEpisode, ThesisPoint } from "../../types/generated/thesis";
import { longDate, monthAxis, sessionAxis } from "./axis";
import { tipHtml, type TipRow } from "./tooltip";

export const TRACKER_SERIES = {
  vix: "Market-priced volatility — VIX",
  forecast: "Our volatility forecast",
  realized: "Actual volatility over the following 30 days",
  gap: "VIX minus our forecast",
} as const;

/** Each kind of qualifying observation: its shape and its colour role, which both differ. */
export const CANDIDATES = [
  { eligibility: "ELIGIBLE", symbol: "circle", role: "eligible-mark" },
  { eligibility: "FILTERED_OUT", symbol: "rect", role: "filtered-mark" },
  { eligibility: "CREDIT_UNAVAILABLE", symbol: "triangle", role: "unavailable-mark" },
] as const;

export const CREDIT_SERIES = {
  spread: "High-yield credit spread",
  unstable: "Credit not stable",
  unavailable: "Credit unavailable",
} as const;

/** The sessions a chart shows, as its first and last index. */
export interface Range {
  start: number;
  end: number;
}

/** The last `sessions` of `count`. */
export function lastSessions(count: number, sessions: number): Range {
  return { start: Math.max(0, count - sessions), end: Math.max(0, count - 1) };
}

const MARKER = 3 * SIZE_MARK;

// The top of an axis, rounded up to a whole ten points, a tick of its own.
const TOP_STEP = 0.1;

function top(extent: { max: number }): number {
  return Math.ceil(extent.max / TOP_STEP + 1e-9) * TOP_STEP;
}

function volTick(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function pointTick(value: number): string {
  const whole = Math.round(value * 100);
  return whole < 0 ? `−${Math.abs(whole)}` : String(whole);
}

interface Labelled {
  axisLabel: object;
}

/** An axis with a reading page's tick size. */
function reading<T extends Labelled>(axis: T): T {
  return { ...axis, axisLabel: { ...axis.axisLabel, fontSize: READING_FONT.tick } };
}

/** The base option at a reading page's sizes, its legend left to the page's HTML. */
function readingBase(p: Palette) {
  const base = baseOption(p);
  return {
    ...base,
    legend: { show: false },
    tooltip: { ...base.tooltip,
               textStyle: { ...base.tooltip.textStyle, fontSize: READING_FONT.tooltip } },
  };
}

/** The first session with a credit value, or none. */
export function creditStart(series: readonly ThesisPoint[]): string | undefined {
  return series.find((p) => p.credit_bps !== null)?.day;
}

/** Each run of consecutive sessions whose credit has `status`, as its first and last index. */
export function creditSpans(series: readonly ThesisPoint[], status: string): [number, number][] {
  const spans: [number, number][] = [];
  series.forEach((point, i) => {
    if (point.credit_status !== status) return;
    const last = spans.at(-1);
    if (last && last[1] === i - 1) last[1] = i;
    else spans.push([i, i]);
  });
  return spans;
}

/** A shaded region over index spans. A session is a point on the axis, so a span is drawn to the
 * next session, and a last session's from the one before: one session still has width. */
function spanArea(days: readonly string[], spans: readonly [number, number][], fill: string) {
  const last = days.length - 1;
  return {
    silent: true,
    itemStyle: { color: fill },
    data: spans.map(([a, b]) => [
      { xAxis: days[a === last ? Math.max(0, a - 1) : a] },
      { xAxis: days[Math.min(last, b + 1)] },
    ]),
  };
}

/** Each episode's search window as index spans, cut at the last session there is. */
export function windowSpans(series: readonly ThesisPoint[],
                            episodes: readonly ThesisEpisode[]): [number, number][] {
  const at = new Map(series.map((p, i) => [p.day, i]));
  return episodes.flatMap((e): [number, number][] => {
    const from = at.get(e.shock_day);
    return from === undefined ? [] : [[from, at.get(e.window_end) ?? series.length - 1]];
  });
}

// ---- tooltips -----------------------------------------------------------------------------------

function realizedRows(p: Palette, point: ThesisPoint): TipRow[] {
  const ends = point.outcome_end === null ? "date not in this file" : longDate(point.outcome_end);
  const value = point.realized_vol !== null ? iv(point.realized_vol)
    : point.outcome === "PENDING" ? "pending" : "not available";
  return [
    [TRACKER_SERIES.realized, value, p["realized-line"]],
    ["  measured from this close", longDate(point.day)],
    ["  to, and known only after", ends],
  ];
}

function priceRows(p: Palette, point: ThesisPoint): TipRow[] {
  return [
    [TRACKER_SERIES.vix, point.vix === null ? "not available" : iv(point.vix / 100), p["vix-line"]],
    [TRACKER_SERIES.forecast, point.forecast_vol === null ? "not available"
      : iv(point.forecast_vol), p["forecast-line"]],
    ...realizedRows(p, point),
  ];
}

function detailRows(p: Palette, point: ThesisPoint, episode: ThesisEpisode | undefined): TipRow[] {
  const rows: TipRow[] = [
    [TRACKER_SERIES.gap, orDash(point.forecast_gap_vol, volPts), p["gap-line"]],
    ["Credit at that decision", point.credit_bps === null ? "no data"
      : `${bps(point.credit_bps)}, ${creditLabel(point.credit_status).toLowerCase()}`],
  ];
  const kind = episode?.eligibility;
  if (kind !== undefined && kind !== null) {
    const role = CANDIDATES.find((c) => c.eligibility === kind)?.role ?? "unavailable-mark";
    rows.push(["Qualifying observation", eligibilityLabel(kind), p[role]]);
  }
  return rows;
}

/** The category an axis tooltip is on: its day. */
function tipDay(params: unknown): string | undefined {
  const first = (Array.isArray(params) ? params[0] : params) as { axisValue?: string } | undefined;
  return first?.axisValue;
}

/** An axis tooltip over a chart's sessions. */
function tooltip(base: object, points: readonly ThesisPoint[],
                 rows: (point: ThesisPoint) => TipRow[], title: (day: string) => string) {
  const byDay = new Map(points.map((s) => [s.day, s]));
  return {
    ...base,
    formatter: (params: unknown) => {
      const day = tipDay(params);
      const point = day === undefined ? undefined : byDay.get(day);
      return point ? tipHtml(title(point.day), rows(point)) : "";
    },
  };
}

// ---- the tracker --------------------------------------------------------------------------------

function priceLines(p: Palette, series: readonly ThesisPoint[], extra: object = {}) {
  return [
    lineSeries(TRACKER_SERIES.vix, series.map((s) => (s.vix === null ? null : s.vix / 100)),
               p["vix-line"], LINE.series, "solid", extra),
    lineSeries(TRACKER_SERIES.forecast, series.map((s) => s.forecast_vol), p["forecast-line"],
               LINE.series, "dashed"),
    lineSeries(TRACKER_SERIES.realized, series.map((s) => s.realized_vol), p["realized-line"],
               LINE.series),
  ];
}

function volAxis(p: Palette, gridIndex: number) {
  return reading(valueAxis(p, { gridIndex, max: top,
                                axisLabel: { ...valueAxis(p).axisLabel, formatter: volTick } }));
}

/** The default chart: what was priced in, our forecast, and what followed. */
export function priceOption(p: Palette, series: readonly ThesisPoint[], range: Range) {
  const base = readingBase(p);
  const axis = sessionAxis(series.map((s) => s.day));
  return {
    ...base,
    grid: ZOOM_GRID.map((g) => plotGrid(p, g)),
    xAxis: reading(monthAxis(p, axis)),
    yAxis: volAxis(p, 0),
    dataZoom: zoom(p, [0], range.start, range.end),
    tooltip: tooltip(base.tooltip, series, (point) => priceRows(p, point),
                     (day) => `${longDate(day)} close`),
    series: priceLines(p, series),
  };
}

/** The default chart with the signal's details over and under it. */
export function trackerOption(p: Palette, series: readonly ThesisPoint[],
                              episodes: readonly ThesisEpisode[], threshold: number | null,
                              range: Range) {
  const base = readingBase(p);
  const axis = sessionAxis(series.map((s) => s.day));
  const days = axis.categories;
  const byDay = new Map(series.map((s) => [s.day, s]));
  const byCandidate = new Map(episodes.flatMap((e) =>
    e.candidate_day === null ? [] : [[e.candidate_day, e] as const]));
  const lower = { xAxisIndex: 1, yAxisIndex: 1 };
  const windows = spanArea(days, windowSpans(series, episodes), p["window-shade"]);
  return {
    ...base,
    grid: ZOOM_PANES.map((g) => plotGrid(p, g)),
    xAxis: [monthAxis(p, axis, 0, false), reading(monthAxis(p, axis, 1))],
    yAxis: [
      volAxis(p, 0),
      reading(valueAxis(p, { gridIndex: 1, max: top, splitNumber: PANE_TICKS + 1,
                             axisLabel: { ...valueAxis(p).axisLabel, formatter: pointTick } })),
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    dataZoom: zoom(p, [0, 1], range.start, range.end),
    tooltip: tooltip(base.tooltip, series,
                     (pt) => [...priceRows(p, pt), ...detailRows(p, pt, byCandidate.get(pt.day))],
                     (day) => `${longDate(day)} close`),
    series: [
      ...priceLines(p, series, { markArea: windows }),
      lineSeries(TRACKER_SERIES.gap, series.map((s) => s.forecast_gap_vol), p["gap-line"],
                 LINE.series, "solid", { ...lower, markArea: noCreditArea(p, series, days),
                                         markLine: thresholdLine(p, threshold) }),
      ...CANDIDATES.map((c) => candidateSeries(p, c, episodes, byDay, lower)),
    ],
  };
}

/** The sessions before any credit data, shaded and labelled. */
function noCreditArea(p: Palette, series: readonly ThesisPoint[], days: readonly string[]) {
  const from = creditStart(series);
  const first = from === undefined ? days.length : days.indexOf(from);
  return {
    ...spanArea(days, first > 0 ? [[0, first - 1]] : [], p["no-credit-shade"]),
    label: { formatter: from ? `No credit data before ${longDate(from)}` : "No credit data",
             position: "insideBottomLeft", color: p["text-muted"], fontFamily: p.fontMono },
  };
}

/** The rule's threshold, dashed, over a dotted zero; the legend names it. */
function thresholdLine(p: Palette, threshold: number | null) {
  const zero = ruler(p, 0);
  if (threshold === null) return zero;
  return {
    ...zero,
    data: [...zero.data,
           { yAxis: threshold, lineStyle: { color: p["threshold-line"], type: "dashed" } }],
  };
}

function candidateSeries(p: Palette, kind: (typeof CANDIDATES)[number],
                         episodes: readonly ThesisEpisode[],
                         byDay: ReadonlyMap<string, ThesisPoint>, lower: object) {
  const colour = p[kind.role];
  return {
    ...lower,
    name: eligibilityLabel(kind.eligibility),
    type: "scatter",
    symbol: kind.symbol,
    symbolSize: MARKER,
    color: colour,
    itemStyle: { color: colour, borderColor: p.surface, borderWidth: LINE.series },
    data: episodes.flatMap((e) => {
      const day = e.candidate_day;
      if (day === null || e.eligibility !== kind.eligibility) return [];
      const gap = byDay.get(day)?.forecast_gap_vol ?? null;
      return gap === null ? [] : [[day, gap]];
    }),
    z: 5,
  };
}

// ---- the credit spread --------------------------------------------------------------------------

const CREDIT_STEP = 50;

export interface CreditLimits {
  level: number;
  short: number;
  long: number;
}

function creditRows(p: Palette, point: ThesisPoint, limits: CreditLimits | null): TipRow[] {
  const limit = (value: number | undefined, format: (v: number) => string) =>
    value === undefined ? "" : ` (limit ${format(value)})`;
  return [
    [CREDIT_SERIES.spread, orDash(point.credit_bps, bps) + limit(limits?.level, bps),
     p["credit-line"]],
    ["Change, 5 observations",
     orDash(point.credit_change_short_bps, bpsChange) + limit(limits?.short, bpsChange)],
    ["Change, 20 observations",
     orDash(point.credit_change_long_bps, bpsChange) + limit(limits?.long, bpsChange)],
    ["Credit", creditLabel(point.credit_status)],
    ["Observation of", orDash(point.credit_observation_date, longDate)],
  ];
}

/** The sessions the credit chart covers: from the first with a value. */
export function creditPoints(series: readonly ThesisPoint[]): readonly ThesisPoint[] {
  const first = series.findIndex((s) => s.credit_bps !== null);
  return first < 0 ? [] : series.slice(first);
}

export function creditOption(p: Palette, points: readonly ThesisPoint[],
                             limits: CreditLimits | null) {
  const base = readingBase(p);
  const axis = sessionAxis(points.map((s) => s.day));
  const shade = (status: string, fill: string) =>
    spanArea(axis.categories, creditSpans(points, status), fill);
  const ceiling = (extent: { max: number }) =>
    Math.ceil(Math.max(extent.max, limits?.level ?? 0) / CREDIT_STEP) * CREDIT_STEP + CREDIT_STEP;
  return {
    ...base,
    grid: ZOOM_GRID.map((g) => plotGrid(p, g)),
    xAxis: reading(monthAxis(p, axis)),
    yAxis: reading(valueAxis(p, {
      min: (extent: { min: number }) => Math.floor(extent.min / CREDIT_STEP) * CREDIT_STEP,
      max: ceiling,
    })),
    dataZoom: zoom(p, [0], 0, axis.categories.length - 1),
    tooltip: tooltip(base.tooltip, points, (point) => creditRows(p, point, limits),
                     (day) => `As known at ${longDate(day)}'s decision`),
    series: [
      lineSeries(CREDIT_SERIES.spread, points.map((s) => s.credit_bps), p["credit-line"],
                 LINE.series, "solid", {
                   markArea: shade("UNSTABLE", p["unstable-shade"]),
                   ...(limits === null ? {} : { markLine: limitLine(p, limits.level) }),
                 }),
      { ...lineSeries(CREDIT_SERIES.unavailable, [], p["no-credit-shade"], LINE.ruler),
        markArea: shade("UNAVAILABLE", p["no-credit-shade"]) },
    ],
  };
}

function limitLine(p: Palette, limit: number) {
  return {
    silent: true,
    symbol: "none",
    lineStyle: { color: p["threshold-line"], width: LINE.ruler, type: "dashed" },
    label: { formatter: `${bps(limit)} limit`, position: "insideEndTop", color: p["text-muted"],
             fontFamily: p.fontMono },
    data: [{ yAxis: limit }],
  };
}
