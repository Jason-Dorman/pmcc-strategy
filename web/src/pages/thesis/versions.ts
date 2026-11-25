// The two exploratory versions in words (UI-SPEC §6 › Thesis; PO, TD-33), all of it from the file's
// own states, checks and counts. A condition met is never a trade, and missing data never a failure.
import { longDate } from "../../components/charts/axis";
import { count } from "../../format/number";
import { points } from "../../format/thesis";
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
  MET: "Conditions met", NOT_MET: "Conditions not met", UNKNOWN: "Cannot assess",
};

export function stateLabel(latest: ThesisVersionLatest | null): string {
  return latest === null ? "Cannot assess" : STATES[latest.state] ?? latest.state;
}

export function stateVerdict(latest: ThesisVersionLatest | null): Verdict {
  if (latest === null || latest.state === "UNKNOWN") return null;
  return latest.state === "MET";
}

const FAILS: Readonly<Record<string, string>> = {
  gap: "VIX is not far enough above our forecast",
  credit: "credit does not pass its stability checks",
  swings_below_long: "five-day volatility is not below 20-day volatility",
  swings_not_rising: "five-day volatility is higher than three sessions earlier",
};
const MISSING: Readonly<Record<string, string>> = {
  gap: "VIX or our forecast",
  credit: "usable credit data",
  swings_below_long: "five-day or 20-day volatility",
  swings_not_rising: "five-day volatility three sessions earlier",
};

/** `a`, `a, and b`, `a, b, and c`. */
function listed(items: readonly string[]): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")}, and ${items.at(-1) ?? ""}`;
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Why: the stretch it opened, the conditions that fail, or what is missing. */
export function reason(latest: ThesisVersionLatest | null): string {
  if (latest === null) return "No session is in the tracker yet.";
  const failed = latest.checks.filter((c) => c.met === false).map((c) => FAILS[c.key] ?? c.key);
  const missing = latest.checks.filter((c) => c.met === null).map((c) => MISSING[c.key] ?? c.key);
  if (latest.state === "NOT_MET") return `${capital(listed(failed))}.`;
  if (latest.state === "UNKNOWN") return `Required data is missing: ${listed(missing)}.`;
  return latest.stretch_start === null ? "Every condition holds at the latest session."
    : `Every condition holds. The current qualifying stretch began ${longDate(latest.stretch_start)}.`;
}

/** The home tile's line: `A: conditions not met · B: cannot assess`. */
export function tileStates(c: ThesisComparison | null): string {
  if (c === null) return "Version results not in this file yet";
  return c.versions.map((v) => `${v.key}: ${stateLabel(v.latest).toLowerCase()}`).join(" · ");
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
