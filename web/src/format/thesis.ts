// The volatility thesis's words and units (UI-SPEC §6 › Thesis; PO, TD-23, TD-25, TD-30): a vol
// difference in volatility points, a spread in basis points, a premium in variance, and each
// status as a reader would say it. The file's own codes never show on the page.
import type { Thesis } from "../types/generated/thesis";

const MINUS = "−";

function signed(value: number, digits: number): string {
  const text = Math.abs(value).toFixed(digits);
  if (Number(text) === 0) return text;
  return `${value < 0 ? MINUS : "+"}${text}`;
}

/** The size of a vol difference in volatility points, unsigned: `11.9`. */
export function points(difference: number): string {
  return (Math.abs(difference) * 100).toFixed(1);
}

/** A difference of two decimal vols, in volatility points, signed: `+11.9`. */
export function volPoints(difference: number): string {
  return signed(difference * 100, 1);
}

/** The same with its unit: `+11.9 pts`. */
export function volPts(difference: number): string {
  return `${volPoints(difference)} pts`;
}

/** A spread in basis points: `347 bps`. */
export function bps(value: number): string {
  return `${value.toFixed(0)} bps`;
}

/** A change in a spread, signed: `+17 bps`. */
export function bpsChange(value: number): string {
  return `${signed(value, 0)} bps`;
}

/** A realized variance premium, 30-day total variance, signed: `+0.0019`. */
export function variance(value: number): string {
  return signed(value, 4);
}

/** A share, signed: `+38.8%`. */
export function shareSigned(value: number): string {
  return `${signed(value * 100, 1)}%`;
}

/** An index level or VIX, to two places. */
export function level(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** `5 completed observations`, `1 completed observation`. */
export function completed(count: number): string {
  return `${count.toLocaleString("en-US")} completed ${count === 1 ? "observation" : "observations"}`;
}

/** The backend's signal state, the PO's words (TD-30): the assessment's headline, and the home
 * tile's line. */
const SIGNALS: Readonly<Record<string, string>> = {
  NO_SHOCK: "No qualifying volatility spike to monitor",
  SEARCHING: "Watching a recent volatility spike",
  NO_CANDIDATE: "No qualifying observation in this search window",
  ELIGIBLE: "Research conditions met",
  FILTERED_OUT: "Candidate did not meet the credit rules",
  CREDIT_UNAVAILABLE: "Credit data needed to assess eligibility",
  INCOMPLETE_CANDIDATE_SEARCH: "Missing observations prevent assessment",
};

export function signalLabel(status: string): string {
  return SIGNALS[status] ?? status;
}

/** Whether the next night's file is overdue, so this one is stale whatever it says of itself
 * (THESIS-SPEC §9: never a falsely fresh chart). Nothing to do with how much evidence there is. */
export function isStale(thesis: Thesis, now: number = Date.now()): boolean {
  if (thesis.data_status !== "CURRENT") return true;
  return thesis.expected_by !== null && now > Date.parse(thesis.expected_by);
}

const ELIGIBILITY: Readonly<Record<string, string>> = {
  ELIGIBLE: "Credit stable",
  FILTERED_OUT: "Credit not stable",
  CREDIT_UNAVAILABLE: "Credit data unavailable",
};

/** A qualifying observation's credit at its own assessment. */
export function eligibilityLabel(eligibility: string): string {
  return ELIGIBILITY[eligibility] ?? eligibility;
}

const EPISODES: Readonly<Record<string, string>> = {
  CANDIDATE: "Qualifying observation found",
  NO_CANDIDATE: "None qualified",
  SEARCHING: "Search open",
  INCOMPLETE_CANDIDATE_SEARCH: "Missing observations",
};

export function episodeLabel(status: string): string {
  return EPISODES[status] ?? status;
}

const OUTCOMES: Readonly<Record<string, string>> = {
  MATURED: "Completed",
  PENDING: "Pending",
  INCOMPLETE: "Incomplete",
  UNAVAILABLE: "Unavailable",
};

export function outcomeLabel(outcome: string): string {
  return OUTCOMES[outcome] ?? outcome;
}

const CREDIT: Readonly<Record<string, string>> = {
  STABLE: "Stable",
  UNSTABLE: "Not stable",
  UNAVAILABLE: "Unavailable",
};

export function creditLabel(status: string): string {
  return CREDIT[status] ?? status;
}
