// What a rule did, in plain words, wherever the site names a rule (PO, DEC-107): the filters,
// the blotter's Rule column, the gate log's outcomes and headers, cycle statistics. The rule IDs
// stay in the results, the links (to the Rules page) and the Rules page itself. A rule these maps
// don't know shows its name from the strategy YAML, then its ID.
import type { Rule, RuleTextOut } from "../types/generated/run_result";

const PLAIN: Readonly<Record<string, string>> = {
  // entries
  "E-L1": "Open long",
  "E-S1": "Sell short",
  // exits: the long
  "X-L1": "Reset long",
  "X-L2": "Roll long",
  // exits: the short
  "X-S1": "Take profit",
  "X-S2": "Defensive close",
  "X-S3": "Friday close",
  "X-S4": "Expired worthless",
  "X-S5": "Assigned",
  "X-E1": "End of backtest",
  // gates: why a week's short wasn't sold
  "G-1": "No quote",
  "G-2": "Structure fails",
  "G-3": "Event week",
  "G-4": "Low vol premium",
  "G-5": "Premium too small",
};

/** A rule ID as a reader would say it: its plain label, else its YAML name, else the ID. */
export function ruleLabel(id: string, rules: readonly Rule[] = []): string {
  return PLAIN[id] ?? rules.find((r) => r.id === id)?.name ?? id;
}

// A gate as a gate-log column is headed: what it checks, not why a week was skipped.
const GATES: Readonly<Record<string, string>> = {
  "G-1": "No quote",
  "G-2": "Structure",
  "G-3": "Event week",
  "G-4": "Vol premium",
  "G-5": "Min premium",
};

/** A gate as its gate-log column is headed. */
export function gateName(id: string, rules: readonly Rule[] = []): string {
  return GATES[id] ?? ruleLabel(id, rules);
}

/** The rule's condition and action, for a hover: `condition → action`. */
export function ruleHint(id: string, text: Readonly<Record<string, RuleTextOut>>): string {
  const rule = text[id];
  return rule ? `${rule.condition} → ${rule.action}` : "";
}
