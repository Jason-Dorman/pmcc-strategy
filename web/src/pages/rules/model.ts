// The Trade rules page's model (UI-SPEC §6.3): rules.json's two strategies side by side, section
// by section, how they differ, and each variant's changes against its strategy, in words. Nothing
// here is typed in: every rule, value and change comes from rules.json (DEC-52).
import { STRATEGY_PAGES } from "../../app/pages";
import { ratio } from "../../format/number";
import type { Family, RuleChange, RuleOut, Rules, StrategyRules } from "../../types/generated/rules";

export type Section = "entry" | "gate" | "exit";

const SECTIONS: Readonly<Record<string, Section>> = { E: "entry", G: "gate", X: "exit" };

/** A rule's section by its ID's letter: E an entry, G a skip-week gate, X an exit. */
export function sectionOf(id: string): Section | undefined {
  return SECTIONS[id.charAt(0)];
}

/** The two strategies the page sets side by side. */
export interface Pair {
  baseline: StrategyRules;
  quant: StrategyRules;
}

export function pairOf(rules: Rules): Pair | undefined {
  const find = (id: string) => rules.strategies.find((s) => s.id === id);
  const baseline = find(STRATEGY_PAGES.baseline);
  const quant = find(STRATEGY_PAGES.quant);
  return baseline && quant ? { baseline, quant } : undefined;
}

/** A rule as each strategy runs it; a strategy that doesn't run it has none. */
export interface RuleRow {
  id: string;
  baseline: RuleOut | undefined;
  quant: RuleOut | undefined;
}

function find(strategy: StrategyRules, id: string): RuleOut | undefined {
  return strategy.rules.find((r) => r.id === id);
}

const SECTION_ORDER = "EGX";

/** Every rule either strategy runs, in their order: each lists its rules in the spec's, quant
 * every gate, so a rule only the baseline runs joins its section's end. */
export function ruleRows(pair: Pair, section?: Section): RuleRow[] {
  const ids = [...new Set([...pair.quant.rules, ...pair.baseline.rules].map((r) => r.id))];
  const letter = (id: string) => SECTION_ORDER.indexOf(id.charAt(0));
  return ids
    .filter((id) => section === undefined || sectionOf(id) === section)
    .sort((a, b) => letter(a) - letter(b)) // stable: each section keeps the strategies' order
    .map((id) => ({ id, baseline: find(pair.baseline, id), quant: find(pair.quant, id) }));
}

/** Two versions of a rule read the same: its name, its row (title and summary) and the rule
 * stated exactly (condition and action); its values show in them. */
export function sameRule(a: RuleOut, b: RuleOut): boolean {
  return a.name === b.name && a.title === b.title && a.summary === b.summary
    && a.condition === b.condition && a.action === b.action;
}

/** A rule's text both strategies share, or each one's. */
export type Versions =
  | { kind: "shared"; text: string }
  | { kind: "each"; baseline: string | undefined; quant: string | undefined };

/** One piece of a rule's text across the strategies: shared when every strategy running it has
 * the same, else each strategy's own (`undefined` where it doesn't run the rule). */
export function versions(row: RuleRow, text: (r: RuleOut) => string): Versions {
  const [b, q] = [row.baseline && text(row.baseline), row.quant && text(row.quant)];
  if (b === undefined || q === undefined || b === q) {
    return { kind: "shared", text: b ?? q ?? "" };
  }
  return { kind: "each", baseline: b, quant: q };
}

// ---- how the strategies differ ----------------------------------------------------------------

export interface Differences {
  /** Entry rules both run, differently: how each selects its contracts. */
  selection: string[];
  /** Gates one strategy runs and the other doesn't, by the strategy that runs them. */
  quantGates: string[];
  baselineGates: string[];
  /** Anything else that differs (none, by the spec: the exits are shared). */
  other: string[];
}

export function differences(pair: Pair): Differences {
  const found: Differences = { selection: [], quantGates: [], baselineGates: [], other: [] };
  for (const { id, baseline, quant } of ruleRows(pair)) {
    const section = sectionOf(id);
    if (baseline && quant) {
      if (sameRule(baseline, quant)) continue;
      (section === "entry" ? found.selection : found.other).push(id);
    } else if (section === "gate") {
      (quant ? found.quantGates : found.baselineGates).push(id);
    } else {
      found.other.push(id);
    }
  }
  return found;
}

// ---- the variants: ablations and sensitivity runs ---------------------------------------------

export interface VariantRow {
  variant: StrategyRules;
  base: StrategyRules;
  family: Family;
}

/** The variants of the given families, each with its strategy, family by family then by ID. */
export function variantRows(rules: Rules, families: readonly Family[]): VariantRow[] {
  const byId = new Map(rules.strategies.map((s) => [s.id, s]));
  return families.flatMap((family) => rules.strategies
    .filter((s) => s.family === family)
    .flatMap((variant) => {
      const base = byId.get(variant.strategy_id);
      return base ? [{ variant, base, family }] : [];
    }));
}

/** A rule a variant changed, as its strategy has it and as the variant does. */
export interface Changed {
  change: RuleChange;
  before: RuleOut | undefined;
  after: RuleOut | undefined;
}

export function changed(row: VariantRow): Changed[] {
  return row.variant.changes.map((change) => ({
    change,
    before: find(row.base, change.rule_id),
    after: find(row.variant, change.rule_id),
  }));
}

/** A param's name as words: `min_ratio` → `min ratio`. */
export function paramWords(name: string): string {
  return name.replaceAll("_", " ");
}

/** The params whose shown values moved: `k 1.0 → 0.75`, or `bar 1` for a param new to it. */
export function paramChanges(before: RuleOut | undefined, after: RuleOut | undefined): string[] {
  const was = before?.shown ?? {};
  const now = after?.shown ?? {};
  const names = [...new Set([...Object.keys(now), ...Object.keys(was)])];
  return names.flatMap((name) => {
    const [b, a] = [was[name], now[name]];
    if (b === a) return [];
    const words = paramWords(name);
    if (b === undefined) return [`${words} ${a ?? ""}`];
    return [a === undefined ? `${words} dropped` : `${words} ${b} → ${a}`];
  });
}

/** The fill model's changes: `spread capture 0.00 → 0.25`, a fee a contract. */
export function fillChanges(row: VariantRow, money: (dollars: number) => string): string[] {
  const { base, variant } = row;
  const found: string[] = [];
  if (base.spread_capture !== variant.spread_capture) {
    found.push(`spread capture ${ratio(base.spread_capture)} → ${ratio(variant.spread_capture)}`);
  }
  if (base.fee_per_contract !== variant.fee_per_contract) {
    found.push(`fee ${money(base.fee_per_contract)} → ${money(variant.fee_per_contract)} a contract`);
  }
  return found;
}

/** A family as the Sensitivity panel names its check. */
export const CHECK_NAMES: Readonly<Record<Family, string>> = {
  strategy: "Strategy",
  ablation: "Ablation",
  friction: "Friction",
  timing: "Timing",
  grid: "Grid",
};
