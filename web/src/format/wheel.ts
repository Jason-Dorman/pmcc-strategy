// The wheel's states in words (WD-22): what the book holds, never the state's code. A short form
// for table cells and filters, a long one for the portfolio at a bar.
import type { State } from "../types/generated/wheel_result";

const SHORT: Readonly<Record<State, string>> = {
  cash: "Cash",
  put: "Short put",
  shares: "Shares",
  call: "Covered call",
};

const LONG: Readonly<Record<State, string>> = {
  cash: "Cash only, no position",
  put: "A short put, secured by cash",
  shares: "Shares, no call sold yet",
  call: "Shares, with a covered call",
};

/** `Short put`: a state as a table cell names it. */
export function stateLabel(state: string): string {
  return SHORT[state as State] ?? state;
}

/** `A short put, secured by cash`: a state as the portfolio states it. */
export function stateWords(state: string): string {
  return LONG[state as State] ?? state;
}

/** The book holds shares in this state (alone, or under a call). */
export function holdsShares(state: string): boolean {
  return state === "shares" || state === "call";
}
