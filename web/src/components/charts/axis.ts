// The time axis is trading time (UI-SPEC §4 rule 8): a category axis of the bars or sessions the
// result has, so nights, weekends and holidays take no width. A tick marks each session's first
// point and a label each week's, as `Mar 30`.
import { timeET } from "../../format/time";
import { categoryAxisStyle, type Palette } from "../../theme/echarts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_MS = 86_400_000;

/** The Monday of a date's calendar week, both `YYYY-MM-DD`. */
export function weekOf(date: string): string {
  const [y, m, d] = date.split("-").map(Number);
  const day = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, d ?? 1));
  const monday = new Date(day.getTime() - ((day.getUTCDay() + 6) % 7) * DAY_MS);
  return monday.toISOString().slice(0, 10);
}

/** `2026-03-30` → `Mar 30`. */
export function shortDate(date: string): string {
  const [, m, d] = date.split("-").map(Number);
  return `${MONTHS[(m ?? 1) - 1] ?? ""} ${d ?? ""}`;
}

export interface TradingAxis {
  /** Each point's category: its time in ET, or its session date. */
  categories: string[];
  /** Each point's ET date. */
  dates: string[];
  /** The point opens its session (a tick). */
  sessionStarts: boolean[];
  /** The point opens its week (a label). */
  weekStarts: boolean[];
}

function axisOf(categories: string[], dates: string[]): TradingAxis {
  const sessionStarts = dates.map((d, i) => i === 0 || d !== dates[i - 1]);
  const weekStarts = dates.map((d, i) => i === 0 || weekOf(d) !== weekOf(dates[i - 1] ?? d));
  return { categories, dates, sessionStarts, weekStarts };
}

/** `2026-03-30` → `Mar 2026`. */
export function monthYear(date: string): string {
  const [y, m] = date.split("-").map(Number);
  return `${MONTHS[(m ?? 1) - 1] ?? ""} ${y ?? ""}`;
}

/** `2026-11-20` → `Nov 20, 2026`. */
export function longDate(date: string): string {
  return `${shortDate(date)}, ${date.slice(0, 4)}`;
}

/** An axis of bars, by their end times. */
export function barAxis(times: readonly string[]): TradingAxis {
  const categories = times.map(timeET);
  return axisOf(categories, categories.map((c) => c.slice(0, 10)));
}

/** An axis of sessions, by their dates. */
export function sessionAxis(sessions: readonly string[]): TradingAxis {
  return axisOf([...sessions], [...sessions]);
}

/**
 * The category x-axis for a grid, ticked by session and labelled by week. A short week (a
 * holiday) is narrower than a label on a narrow chart, so a label that would overlap the one
 * before it is left out, and the first week's is always kept.
 */
export function xAxis(p: Palette, axis: TradingAxis, gridIndex = 0, labels = true) {
  const style = categoryAxisStyle(p);
  return {
    ...style,
    gridIndex,
    data: axis.categories,
    axisLabel: {
      ...style.axisLabel,
      show: labels,
      hideOverlap: true,
      showMinLabel: true,
      interval: (i: number) => axis.weekStarts[i] === true,
      formatter: (_value: string, i: number) => shortDate(axis.dates[i] ?? ""),
    },
    axisTick: { ...style.axisTick, interval: (i: number) => axis.sessionStarts[i] === true },
  };
}

/**
 * The category x-axis of a chart over years of sessions (the thesis's, T4-01): ticked and labelled
 * at each month's first session, `Mar 2026`, the labels thinned as they would overlap.
 */
export function monthAxis(p: Palette, axis: TradingAxis, gridIndex = 0, labels = true) {
  const style = categoryAxisStyle(p);
  const starts = axis.dates.map((d, i) =>
    i === 0 || d.slice(0, 7) !== (axis.dates[i - 1] ?? "").slice(0, 7));
  return {
    ...style,
    gridIndex,
    data: axis.categories,
    axisLabel: {
      ...style.axisLabel,
      show: labels,
      hideOverlap: true,
      interval: (i: number) => starts[i] === true,
      formatter: (value: string) => monthYear(value),
    },
    axisTick: { ...style.axisTick, interval: (i: number) => starts[i] === true },
  };
}
