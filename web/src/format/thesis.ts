// The volatility thesis's words and units (UI-SPEC §6 › Thesis; PO, TD-23, TD-25, TD-28): a
// vol difference in points, a spread in basis points, a premium in variance, and each status as a
// reader would say it. The file's own codes never show on the page.
import type { Thesis, ThesisSignal } from "../types/generated/thesis";
import { longDate } from "../components/charts/axis";

const MINUS = "−";

function signed(value: number, digits: number): string {
  const text = Math.abs(value).toFixed(digits);
  if (Number(text) === 0) return text;
  return `${value < 0 ? MINUS : "+"}${text}`;
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

/** The signal in a few words (the home tile, the readout). The two blocked states are the PO's
 * (TD-25), cut to their first half here; `signalDetail` gives each whole. */
const SIGNALS: Readonly<Record<string, string>> = {
  NO_SHOCK: "No qualifying episode today",
  SEARCHING: "Monitoring a recent volatility spike",
  NO_CANDIDATE: "Recent spike, no candidate qualified",
  ELIGIBLE: "Candidate found, credit stable",
  FILTERED_OUT: "Candidate found, credit not stable",
  CREDIT_UNAVAILABLE: "Credit data unavailable",
  INCOMPLETE_CANDIDATE_SEARCH: "Incomplete observation window",
};

export function signalLabel(status: string): string {
  return SIGNALS[status] ?? status;
}

function blockedDetail(s: ThesisSignal): string | undefined {
  if (s.status === "CREDIT_UNAVAILABLE") {
    return "Credit data unavailable — eligibility cannot be assessed.";
  }
  if (s.status === "INCOMPLETE_CANDIDATE_SEARCH") {
    return "Incomplete observation window — candidate assessment unavailable.";
  }
  return undefined;
}

/** The signal in a sentence or two: its episode's dates, and a blocked assessment's reason. */
export function signalDetail(s: ThesisSignal): string {
  if (s.shock_day === null || s.window_end === null) {
    return "No VIX spike has a search open.";
  }
  const spike = `VIX spiked on ${longDate(s.shock_day)}`;
  const blocked = blockedDetail(s);
  if (blocked !== undefined) return `${blocked} ${spike}. ${s.reason}`.trim();
  const until = `${spike}; the search for a candidate runs through ${longDate(s.window_end)}.`;
  if (s.candidate_day === null) {
    return s.status === "NO_CANDIDATE"
      ? `${spike}; no session of its search window qualified.` : until;
  }
  return `${spike}; the candidate is ${longDate(s.candidate_day)}.`;
}

/** Whether the next night's file is overdue, so this one is stale whatever it says of itself
 * (THESIS-SPEC §9: never a falsely fresh chart). */
export function isStale(thesis: Thesis, now: number = Date.now()): boolean {
  if (thesis.data_status !== "CURRENT") return true;
  return thesis.expected_by !== null && now > Date.parse(thesis.expected_by);
}

const ELIGIBILITY: Readonly<Record<string, string>> = {
  ELIGIBLE: "Eligible",
  FILTERED_OUT: "Filtered out",
  CREDIT_UNAVAILABLE: "Credit data unavailable",
};

export function eligibilityLabel(eligibility: string): string {
  return ELIGIBILITY[eligibility] ?? eligibility;
}

const EPISODES: Readonly<Record<string, string>> = {
  CANDIDATE: "Candidate found",
  NO_CANDIDATE: "No candidate",
  SEARCHING: "Searching",
  INCOMPLETE_CANDIDATE_SEARCH: "Incomplete observation window",
};

export function episodeLabel(status: string): string {
  return EPISODES[status] ?? status;
}

const OUTCOMES: Readonly<Record<string, string>> = {
  MATURED: "Matured",
  PENDING: "Pending",
  INCOMPLETE: "Incomplete",
  UNAVAILABLE: "Unavailable",
};

export function outcomeLabel(outcome: string): string {
  return OUTCOMES[outcome] ?? outcome;
}

const CREDIT: Readonly<Record<string, string>> = {
  STABLE: "Stable",
  UNSTABLE: "Unstable",
  UNAVAILABLE: "Unavailable",
};

export function creditLabel(status: string): string {
  return CREDIT[status] ?? status;
}

const CONDITIONS: Readonly<Record<string, string>> = {
  PASS: "Not triggered",
  FAIL: "Triggered",
  INSUFFICIENT_DATA: "Insufficient data",
  NOT_EVALUATED: "Not yet evaluated",
};

export function conditionLabel(status: string): string {
  return CONDITIONS[status] ?? status;
}

const THESIS: Readonly<Record<string, string>> = {
  PROVISIONAL: "Provisional",
  PAUSED: "Paused",
  ACTIVE: "Active",
};

export function thesisLabel(status: string): string {
  return THESIS[status] ?? status;
}

/** `INSUFFICIENT_EVIDENCE` → `Insufficient`: the only value this milestone has (TD-23). */
export function evidenceLabel(status: string): string {
  return status === "INSUFFICIENT_EVIDENCE" ? "Insufficient" : status;
}
