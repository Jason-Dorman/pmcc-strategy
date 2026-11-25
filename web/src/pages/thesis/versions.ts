// The two exploratory versions in words (UI-SPEC §6 › Thesis; PO, TD-33, TD-35), all of it from the
// file's own states and counts. A condition met is never a trade, and missing data never a failure.
import { longDate } from "../../components/charts/axis";
import { count } from "../../format/number";
import { points, volPoints } from "../../format/thesis";
import type { Thesis, ThesisComparison, ThesisVersion, ThesisVersionLatest, ThesisView } from "../../types/generated/thesis";
import type { Verdict } from "./assessment";

export const VERSION_NAMES: Readonly<Record<string, string>> = {
  A: "A — Pricing gap + stable credit",
  B: "B — Also wait for calmer markets",
};

export function versionName(v: ThesisVersion): string {
  return VERSION_NAMES[v.key] ?? `${v.key} — ${v.name}`;
}

const STATES: Readonly<Record<string, string>> = {
  MET: "Research conditions met", NOT_MET: "No qualifying setup",
  UNKNOWN: "Cannot assess — required data unavailable",
};

export function stateLabel(latest: ThesisVersionLatest | null): string {
  const state = latest?.state ?? "UNKNOWN";
  return STATES[state] ?? state;
}

export function stateVerdict(latest: ThesisVersionLatest | null): Verdict {
  if (latest === null || latest.state === "UNKNOWN") return null;
  return latest.state === "MET";
}

/** The qualifying stretch a met version is in; nothing otherwise: the readings say why. */
export function stretchNote(latest: ThesisVersionLatest | null): string | null {
  if (latest?.state !== "MET" || latest.stretch_start === null) return null;
  return `The current qualifying stretch began ${longDate(latest.stretch_start)}.`;
}

/** The home tile's line, each label short: `A: no qualifying setup · B: cannot assess`. */
export function tileStates(c: ThesisComparison | null): string {
  if (c === null) return "Version results not in this file yet";
  const short = (v: ThesisVersion) => stateLabel(v.latest).toLowerCase().replace(/ — .*/, "");
  return c.versions.map((v) => `${v.key}: ${short(v)}`).join(" · ");
}

export function viewOf(v: ThesisVersion, key: string): ThesisView | undefined {
  return v.views.find((w) => w.key === key);
}

export function viewName(key: string, c: ThesisComparison): string {
  if (key === "ten_session") return `At least ${c.spacing_sessions} sessions apart`;
  if (key === "thirty_day") return `At least ${c.spacing_calendar_days} calendar days apart`;
  return "All qualifying stretches";
}

export function period(c: ThesisComparison): string {
  if (c.analysis_start === null || c.analysis_end === null) return "no session yet";
  return `${longDate(c.analysis_start)} to ${longDate(c.analysis_end)}`;
}

/** How far the average gaps depend on the counting: every stretch, then spaced ones (TD-35). The
 * first figure carries the unit; a view without a completed outcome is said to have no average. */
export function countingSentence(c: ThesisComparison): string {
  let unit = " points";
  const averages = (key: string): string => c.versions.map((v) => {
    const mean = viewOf(v, key)?.mean_gap ?? null;
    if (mean === null) return `not available for ${v.key}`;
    const shown = `${volPoints(mean)}${unit} for ${v.key}`;
    unit = "";
    return shown;
  }).join(" and ");
  return `Counting every qualifying stretch, the average gap is ${averages("all")}. Keeping `
    + `observations at least ${c.spacing_calendar_days} calendar days apart, it is `
    + `${averages("thirty_day")}.`;
}

/** What a group of completed observations: its count and its average gap. */
export interface Gap {
  count: number;
  mean_vol_gap: number | null;
}

/** How market-priced volatility compared with what followed, by its sign; one observation is not
 * an average. None without a completed observation. */
export function gapPhrase(c: Gap): string | null {
  const gap = c.mean_vol_gap;
  if (c.count === 0 || gap === null) return null;
  if (points(gap) === "0.0") {
    return "market-priced volatility matched subsequent actual volatility"
      + (c.count === 1 ? "" : " on average");
  }
  const size = c.count === 1 ? points(gap) : `an average of ${points(gap)}`;
  return `market-priced volatility ${gap > 0 ? "exceeded" : "fell below"} subsequent actual `
    + `volatility by ${size} volatility points`;
}

/** A version's gap in one counting view, named with both. */
export function versionGap(t: Thesis, key: string, viewKey: string): string {
  const c = t.comparison;
  const version = c?.versions.find((v) => v.key === key);
  const view = version && viewOf(version, viewKey);
  if (!c || !view) return `Version ${key}: not in this data file yet.`;
  const label = `Version ${key}, ${viewName(viewKey, c).toLowerCase()}`;
  const phrase = gapPhrase({ count: view.completed, mean_vol_gap: view.mean_gap });
  if (phrase === null) return `${label}: no observation has completed yet.`;
  return `${label}: across ${count(view.completed)} completed `
    + `${view.completed === 1 ? "observation" : "observations"}, ${phrase}.`;
}
