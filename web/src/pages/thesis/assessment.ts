// The latest assessment in words (UI-SPEC §6 › Thesis; PO, TD-30), all of it generated from the
// file. The backend's signal state is the assessment; each supporting observation's verdict is the
// tracker's own check of that session, never judged here. What the file doesn't hold is said to be
// missing, never read as failed or as zero.
import { longDate } from "../../components/charts/axis";
import { iv, orDash } from "../../format/number";
import { points } from "../../format/thesis";
import type { Thesis, ThesisCurrent, ThesisParameters, ThesisSignal } from "../../types/generated/thesis";

/** A check's reading: met, not met, or not assessable (missing data, or a file without it). */
export type Verdict = boolean | null;

export interface Observation {
  name: string;
  text: string;
  met: Verdict;
}

function day(date: string | null): string {
  return orDash(date, longDate);
}

// ---- the state, in a sentence or two ------------------------------------------------------------

const NOT_A_TRADE = "That is a research classification: no trade was placed, and profitability has "
  + "not been established.";

type Lead = (s: ThesisSignal) => string;

const LEADS: Readonly<Record<string, Lead>> = {
  NO_SHOCK: () => "No recent volatility spike is being assessed, so nothing can qualify today. The "
    + "readings below describe the latest session.",
  SEARCHING: (s) => `VIX spiked on ${day(s.shock_day)}. We look for a session that meets the `
    + `research conditions through ${day(s.window_end)}.`,
  NO_CANDIDATE: (s) => `VIX spiked on ${day(s.shock_day)}, and no session in its search window, `
    + `which ended ${day(s.window_end)}, met the research conditions.`,
  ELIGIBLE: (s) => `The session of ${day(s.candidate_day)}, after the spike of `
    + `${day(s.shock_day)}, met the research conditions at its own assessment, including stable `
    + `credit. ${NOT_A_TRADE}`,
  FILTERED_OUT: (s) => `The session of ${day(s.candidate_day)}, after the spike of `
    + `${day(s.shock_day)}, met the pricing and market-swing conditions, but credit did not meet `
    + "its rules at that assessment.",
  CREDIT_UNAVAILABLE: (s) => `The session of ${day(s.candidate_day)}, after the spike of `
    + `${day(s.shock_day)}, met the pricing and market-swing conditions, but there was no usable `
    + "credit data at that assessment. It is neither eligible nor ruled out.",
  INCOMPLETE_CANDIDATE_SEARCH: (s) => `VIX spiked on ${day(s.shock_day)}, but a missing observation `
    + "means we cannot tell whether a session qualified. That is not the same as none qualifying.",
};

export function lead(s: ThesisSignal): string {
  const sentence = LEADS[s.status]?.(s) ?? "The state of the latest session is not recognised.";
  return s.reason ? `${sentence} Reason recorded: ${s.reason}.` : sentence;
}

/** Whether the state is about a session that qualified earlier, not the latest one's readings. */
export function aboutACandidate(s: ThesisSignal): boolean {
  return s.candidate_day !== null;
}

// ---- the latest readings, in a sentence or two --------------------------------------------------

function pricing(c: ThesisCurrent): string {
  const gap = c.forecast_gap_vol;
  if (gap === null) return "Market pricing can't be compared with our forecast for this session.";
  if (gap <= 0) {
    return "The options market is pricing no more volatility than our model forecasts.";
  }
  const how = c.gap_ok === null ? "more" : c.gap_ok ? "substantially more" : "only slightly more";
  return `The options market is pricing ${how} volatility than our model forecasts.`;
}

/** Whether market swings have eased: RV5 under RV20 and no higher than three sessions before. */
export function swingsMet(c: ThesisCurrent): Verdict {
  const { swings_below_long: below, swings_not_rising: calmer } = c;
  if (below === false || calmer === false) return false;
  return below === null || calmer === null ? null : true;
}

/** Whether credit was stable at the latest decision: the tracker's status, never a blank as no. */
export function creditMet(c: ThesisCurrent): Verdict {
  return c.credit_status === "UNAVAILABLE" ? null : c.credit_status === "STABLE";
}

function creditClause(c: ThesisCurrent): string {
  if (creditMet(c) === null) return "credit conditions cannot be assessed for lack of usable data";
  if (c.credit_level_ok === false) {
    return "credit spreads are above the level our stability rule allows";
  }
  if (c.credit_change_short_ok === false || c.credit_change_long_ok === false) {
    return "credit spreads have risen faster than our stability rule allows";
  }
  return "credit conditions do not meet our stability rule";
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Two sentences on the latest session: pricing, then market swings and credit. */
export function readings(c: ThesisCurrent): string {
  const swings = swingsMet(c);
  const credit = creditMet(c);
  const good = [swings === true && "recent market swings have begun to ease",
                credit === true && "credit conditions are stable"].filter((x) => x !== false);
  const bad = [swings === false && "recent market swings have not yet settled",
               credit !== true && creditClause(c)].filter((x) => x !== false);
  const turn = c.gap_ok === true ? "However, " : "In addition, ";
  const sentences = [pricing(c)];
  if (bad.length > 0) sentences.push(`${turn}${bad.join(", and ")}.`);
  if (good.length > 0) sentences.push(`${capital(good.join(", and "))}.`);
  return sentences.join(" ");
}

// ---- the three supporting observations ----------------------------------------------------------

function pricingObservation(c: ThesisCurrent, p: ThesisParameters | null): Observation {
  const gap = c.forecast_gap_vol;
  const name = "Pricing gap";
  if (gap === null) {
    return { name, met: null,
             text: "The gap between VIX and our forecast is not available for this session." };
  }
  const side = gap < 0 ? "below" : "above";
  const needs = p === null ? "" : ` Our rule asks for at least ${points(p.minimum_forecast_gap)}.`;
  return { name, met: c.gap_ok, text: `VIX is ${points(Math.abs(gap))} volatility points ${side} `
    + `the model forecast.${needs}` };
}

function swingsText(c: ThesisCurrent): string {
  const { rv_short: short, rv_long: long } = c;
  if (short === null || long === null) {
    return "Five-day and 20-day volatility are not both available for this session.";
  }
  const side = short < long ? "is below" : "remains above";
  const levels = `Five-day volatility, ${iv(short)}, ${side} 20-day volatility, ${iv(long)}.`;
  return short < long && c.swings_not_rising === false
    ? `${levels} It has risen over the past three sessions, so swings are not easing.` : levels;
}

/** A change in a spread, in words: `rose 17 basis points`. */
export function moved(change: number): string {
  const size = Math.abs(change).toFixed(0);
  if (Number(size) === 0) return "did not change";
  return `${change > 0 ? "rose" : "fell"} ${size} basis ${size === "1" ? "point" : "points"}`;
}

function basis(value: number): string {
  return `${value.toFixed(0)} basis points`;
}

/** The first rule a spread breaks, in words, and its level against the limit it still meets. */
function broken(c: ThesisCurrent, p: ThesisParameters, level: number): string | undefined {
  if (c.credit_level_ok === false) {
    return `The spread is ${basis(level)}; the stability limit is ${p.credit_maximum_level_bps}.`;
  }
  const rises = [
    { ok: c.credit_change_short_ok, change: c.credit_change_short_bps, over: "five",
      limit: p.credit_maximum_change_short_bps },
    { ok: c.credit_change_long_ok, change: c.credit_change_long_bps, over: "twenty",
      limit: p.credit_maximum_change_long_bps },
  ];
  const failed = rises.find((r) => r.ok === false && r.change !== null);
  return failed && `The spread ${moved(failed.change ?? 0)} over ${failed.over} observations; the `
    + `stability limit is ${failed.limit}. Its level, ${basis(level)}, is within the `
    + `${p.credit_maximum_level_bps} limit, but a spread must also not rise too quickly.`;
}

/** Credit in words: the rule it breaks, or that it meets all three, or what isn't known. */
export function creditText(c: ThesisCurrent, p: ThesisParameters | null): string {
  const { credit_bps: level, credit_change_short_bps: short, credit_change_long_bps: long } = c;
  if (c.credit_status === "UNAVAILABLE" || level === null) {
    return ["Credit data can't be used for this session.",
            c.credit_note && `${capital(c.credit_note)}.`].filter(Boolean).join(" ");
  }
  if (p === null || short === null || long === null) {
    return `The spread is ${basis(level)}. The limits it was checked against are not in this file.`;
  }
  return broken(c, p, level)
    ?? `The spread is ${basis(level)}, and it ${moved(short)} over five observations and `
      + `${moved(long)} over twenty: within all three limits.`;
}

export function observations(t: Thesis): Observation[] {
  const c = t.current;
  if (c === null) return [];
  return [
    pricingObservation(c, t.parameters),
    { name: "Market swings", met: swingsMet(c), text: swingsText(c) },
    { name: "Credit conditions", met: creditMet(c), text: creditText(c, t.parameters) },
  ];
}
