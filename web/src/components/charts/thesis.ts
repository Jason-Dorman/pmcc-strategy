// The volatility thesis's charts (UI-SPEC §6 › Thesis; T4-01; PO, TD-28).
//
// The tracker, two panes over one date axis and one zoom. Above: VIX, the 30-day forecast, and the
// volatility that followed, plotted at the day it is forecast from and blank until it matures.
// Below: VIX less the forecast, the rule's threshold, and each episode's candidate, its credit
// told by shape and colour. A spike's search window is shaded faintly, and the years without
// credit data are shaded and labelled.
//
// The credit spread: as known at each session's decision, its level limit a dashed reference, the
// sessions credit was unstable and the ones it was unavailable shaded apart.
import { iv, orDash } from "../../format/number";
import {
  bps,
  bpsChange,
  creditLabel,
  eligibilityLabel,
  volPts,
} from "../../format/thesis";
import {
  baseOption,
  lineSeries,
  LINE,
  PANE_TICKS,
  plotGrid,
  ruler,
  shadeKey,
  valueAxis,
  zoom,
  ZOOM_GRID,
  ZOOM_PANE_LEGEND,
  ZOOM_PANES,
  type Palette,
} from "../../theme/echarts";
import { SIZE_MARK } from "../../theme/tokens";
import type { ThesisEpisode, ThesisPoint } from "../../types/generated/thesis";
import { longDate, monthAxis, sessionAxis } from "./axis";
import { tipHtml, type TipRow } from "./tooltip";

export const TRACKER_SERIES = {
  vix: "VIX",
  forecast: "30-day forecast volatility",
  realized: "Subsequent 30-day realized volatility",
  gap: "VIX minus forecast",
  window: "Spike's search window",
  noCredit: "No credit data",
} as const;

/** Each kind of candidate: its name, its shape and its colour role (PO, TD-28: both differ). */
export const CANDIDATES = [
  { eligibility: "ELIGIBLE", symbol: "circle", role: "eligible-mark" },
  { eligibility: "FILTERED_OUT", symbol: "rect", role: "filtered-mark" },
  { eligibility: "CREDIT_UNAVAILABLE", symbol: "triangle", role: "unavailable-mark" },
] as const;

export const CREDIT_SERIES = {
  spread: "High-yield spread",
  unstable: "Credit unstable",
  unavailable: "Credit unavailable",
} as const;

// The chart opens on about two years of sessions; the slider reaches the rest.
const OPENING_SESSIONS = 504;
const MARKER = 3 * SIZE_MARK;

/** The first session shown when the chart opens. */
export function opening(count: number): number {
  return Math.max(0, count - OPENING_SESSIONS);
}

// Room above the highest point for the legend, up to a whole ten points, a tick of its own.
const HEADROOM = 0.25;
const TOP_STEP = 0.1;

function top(extent: { min: number; max: number }): number {
  const raised = extent.max + (extent.max - extent.min) * HEADROOM;
  return Math.ceil(raised / TOP_STEP - 1e-9) * TOP_STEP;
}

function volTick(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function pointTick(value: number): string {
  const points = Math.round(value * 100);
  return points < 0 ? `−${Math.abs(points)}` : String(points);
}

/** The threshold's legend entry: `Candidate needs 3 points`. */
export function thresholdName(threshold: number): string {
  return `Candidate needs ${pointTick(threshold)} points`;
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

function realizedRows(p: Palette, point: ThesisPoint): TipRow[] {
  const ends = point.outcome_end;
  const value = point.realized_vol !== null ? iv(point.realized_vol)
    : point.outcome === "PENDING" ? "pending" : "not available";
  const rows: TipRow[] = [[TRACKER_SERIES.realized, value, p["realized-line"]],
                          ["  measured from", longDate(point.day)]];
  if (ends !== null) rows.push(["  measured to", longDate(ends)]);
  return rows;
}

function trackerTip(p: Palette, point: ThesisPoint, episode: ThesisEpisode | undefined): string {
  const rows: TipRow[] = [
    [TRACKER_SERIES.vix, point.vix === null ? "—" : iv(point.vix / 100), p["vix-line"]],
    [TRACKER_SERIES.forecast, orDash(point.forecast_vol, iv), p["forecast-line"]],
    ...realizedRows(p, point),
    [TRACKER_SERIES.gap, orDash(point.forecast_gap_vol, volPts), p["gap-line"]],
    ["Credit", point.credit_bps === null ? "no data"
      : `${bps(point.credit_bps)}, ${creditLabel(point.credit_status).toLowerCase()}`],
  ];
  const kind = episode?.eligibility;
  if (kind !== undefined && kind !== null) {
    const role = CANDIDATES.find((c) => c.eligibility === kind)?.role ?? "unavailable-mark";
    rows.push(["Candidate", eligibilityLabel(kind), p[role]]);
  }
  return tipHtml(`${point.day} close`, rows);
}

/** The category an axis tooltip is on: its day. */
function tipDay(params: unknown): string | undefined {
  const first = (Array.isArray(params) ? params[0] : params) as { axisValue?: string } | undefined;
  return first?.axisValue;
}

export function trackerOption(p: Palette, series: readonly ThesisPoint[],
                              episodes: readonly ThesisEpisode[], threshold: number | null) {
  const base = baseOption(p);
  const axis = sessionAxis(series.map((s) => s.day));
  const days = axis.categories;
  const byDay = new Map(series.map((s) => [s.day, s]));
  const byCandidate = new Map(episodes.flatMap((e) =>
    e.candidate_day === null ? [] : [[e.candidate_day, e] as const]));
  const from = creditStart(series);
  const firstCredit = from === undefined ? days.length : days.indexOf(from);
  const lower = { xAxisIndex: 1, yAxisIndex: 1 };
  const windows = spanArea(days, windowSpans(series, episodes), p["window-shade"]);
  const noCredit = {
    ...spanArea(days, firstCredit > 0 ? [[0, Math.max(0, firstCredit - 1)]] : [],
                p["no-credit-shade"]),
    label: { formatter: from ? `No credit data before ${longDate(from)}` : "No credit data",
             position: "insideBottomRight", color: p["text-muted"], fontFamily: p.fontMono },
  };
  const { vix, forecast, realized, gap, window, noCredit: none } = TRACKER_SERIES;
  const needed = threshold === null ? null : thresholdName(threshold);
  return {
    ...base,
    grid: ZOOM_PANES.map((g) => plotGrid(p, g)),
    xAxis: [monthAxis(p, axis, 0, false), monthAxis(p, axis, 1)],
    yAxis: [
      valueAxis(p, { gridIndex: 0, max: top,
                     axisLabel: { ...valueAxis(p).axisLabel, formatter: volTick } }),
      valueAxis(p, { gridIndex: 1, max: top, splitNumber: PANE_TICKS + 1,
                     axisLabel: { ...valueAxis(p).axisLabel, formatter: pointTick } }),
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    dataZoom: zoom(p, [0, 1], opening(days.length), days.length - 1),
    legend: [
      { ...base.legend, data: [vix, forecast, realized, { name: window, icon: "rect" }] },
      { ...base.legend, ...ZOOM_PANE_LEGEND,
        data: [gap, ...(needed === null ? [] : [needed]), ...CANDIDATES.map((c) => eligibilityLabel(c.eligibility)),
               { name: none, icon: "rect" }] },
    ],
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const day = tipDay(params);
        const point = day === undefined ? undefined : byDay.get(day);
        return point ? trackerTip(p, point, byCandidate.get(point.day)) : "";
      },
    },
    series: [
      lineSeries(vix, series.map((s) => (s.vix === null ? null : s.vix / 100)), p["vix-line"],
                 LINE.series, "solid", { markArea: windows }),
      lineSeries(forecast, series.map((s) => s.forecast_vol), p["forecast-line"], LINE.series,
                 "dashed"),
      lineSeries(realized, series.map((s) => s.realized_vol), p["realized-line"], LINE.series),
      lineSeries(gap, series.map((s) => s.forecast_gap_vol), p["gap-line"], LINE.series, "solid",
                 { ...lower, markArea: noCredit, markLine: thresholdLine(p, threshold) }),
      ...(needed === null ? [] : [
        lineSeries(needed, [], p["threshold-line"], LINE.ruler, "dashed", { ...lower }),
      ]),
      shadeKey(window, p["window-shade"]),
      shadeKey(none, p["no-credit-shade"], { ...lower }),
      ...CANDIDATES.map((c) => candidateSeries(p, c, episodes, byDay, lower)),
    ],
  };
}

/** The rule's threshold, dashed, over a dotted zero; its legend entry names it. */
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

function creditTip(p: Palette, point: ThesisPoint, limits: CreditLimits | null): string {
  const limit = (value: number | undefined, format: (v: number) => string) =>
    value === undefined ? "" : ` (limit ${format(value)})`;
  const rows: TipRow[] = [
    [CREDIT_SERIES.spread, orDash(point.credit_bps, bps) + limit(limits?.level, bps),
     p["credit-line"]],
    ["Change, 5 observations",
     orDash(point.credit_change_short_bps, bpsChange) + limit(limits?.short, bpsChange)],
    ["Change, 20 observations",
     orDash(point.credit_change_long_bps, bpsChange) + limit(limits?.long, bpsChange)],
    ["Credit", creditLabel(point.credit_status)],
  ];
  if (point.credit_observation_date !== null) {
    rows.push(["Observation of", longDate(point.credit_observation_date)]);
  }
  return tipHtml(`As known at ${point.day}'s decision`, rows);
}

export interface CreditLimits {
  level: number;
  short: number;
  long: number;
}

/** The sessions the credit chart covers: from the first with a value. */
export function creditPoints(series: readonly ThesisPoint[]): readonly ThesisPoint[] {
  const first = series.findIndex((s) => s.credit_bps !== null);
  return first < 0 ? [] : series.slice(first);
}

export function creditOption(p: Palette, points: readonly ThesisPoint[],
                             limits: CreditLimits | null) {
  const base = baseOption(p);
  const axis = sessionAxis(points.map((s) => s.day));
  const byDay = new Map(points.map((s) => [s.day, s]));
  const shade = (status: string, fill: string) =>
    spanArea(axis.categories, creditSpans(points, status), fill);
  const { spread, unstable, unavailable } = CREDIT_SERIES;
  const ceiling = (extent: { max: number }) =>
    Math.ceil((Math.max(extent.max, limits?.level ?? 0) + CREDIT_STEP) / CREDIT_STEP) * CREDIT_STEP;
  return {
    ...base,
    grid: ZOOM_GRID.map((g) => plotGrid(p, g)),
    xAxis: monthAxis(p, axis),
    yAxis: valueAxis(p, {
      min: (extent: { min: number }) => Math.floor(extent.min / CREDIT_STEP) * CREDIT_STEP,
      max: ceiling,
    }),
    dataZoom: zoom(p, [0], 0, axis.categories.length - 1),
    legend: { ...base.legend,
              data: [spread, { name: unstable, icon: "rect" },
                     { name: unavailable, icon: "rect" }] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const day = tipDay(params);
        const point = day === undefined ? undefined : byDay.get(day);
        return point ? creditTip(p, point, limits) : "";
      },
    },
    series: [
      lineSeries(spread, points.map((s) => s.credit_bps), p["credit-line"], LINE.series, "solid", {
        markArea: shade("UNSTABLE", p["unstable-shade"]),
        ...(limits === null ? {} : { markLine: limitLine(p, limits.level) }),
      }),
      shadeKey(unstable, p["unstable-shade"]),
      { ...shadeKey(unavailable, p["no-credit-shade"]),
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
