// The Trade rules page's model (P7-03): sections by ID, the two strategies' rows, how they differ,
// ID spans, and each variant's changes in words.
import { describe, expect, it } from "vitest";

import { RULES } from "../../test/fixtures";
import type { RuleOut } from "../../types/generated/rules";
import {
  differences,
  pairOf,
  paramChanges,
  ruleRows,
  sectionOf,
  variantRows,
  versions,
  type Pair,
} from "./model";

function pair(): Pair {
  const found = pairOf(RULES);
  if (!found) throw new Error("fixture lacks a strategy");
  return found;
}

function rule(shown: Record<string, string>): RuleOut {
  return { id: "R-1", name: "R", kind: "r", params: {}, shown, title: "t", summary: "s",
           condition: "c", action: "a", rationale: "r" };
}

describe("sections and rows", () => {
  it("sorts a rule into its section by its ID's letter", () => {
    expect(["E-T1", "G-3", "X-S5", "Q-1"].map(sectionOf))
      .toEqual(["entry", "gate", "exit", undefined]);
  });

  it("lists each rule either strategy runs, a gate quant alone runs without a baseline", () => {
    const rows = ruleRows(pair(), "gate");
    expect(rows.map((r) => [r.id, r.baseline !== undefined, r.quant !== undefined])).toEqual([
      ["G-1", true, true], ["G-2", true, true], ["G-3", false, true], ["G-4", false, true],
      ["G-5", false, true]]);
  });

  it("keeps a rule only the baseline runs, at its section's end", () => {
    const { baseline, quant } = pair();
    const g9 = { ...rule({}), id: "G-9" };
    const rows = ruleRows({ quant, baseline: { ...baseline, rules: [...baseline.rules, g9] } });
    expect(rows.map((r) => r.id).slice(5, 11))
      .toEqual(["G-1", "G-2", "G-3", "G-4", "G-5", "G-9"]);
  });

  it("finds no strategy pair without both strategies", () => {
    expect(pairOf({ ...RULES, strategies: RULES.strategies.slice(0, 1) })).toBeUndefined();
  });

  it("shares a text both strategies have alike, and splits one they don't", () => {
    const [t1, , , s3] = ruleRows(pair(), "entry");
    if (!t1 || !s3) throw new Error("fixture lacks a rule");
    expect(versions(t1, (r) => r.rationale)).toEqual({ kind: "shared", text: "Liquidity decides." });
    expect(versions(s3, (r) => r.rationale)).toEqual({
      kind: "each", baseline: "The textbook short.", quant: "The expected-move short." });
  });
});

describe("how the strategies differ", () => {
  it("finds the selection rules and the gates only quant runs", () => {
    expect(differences(pair())).toEqual({
      selection: ["E-L2", "E-L3", "E-S3"], quantGates: ["G-3", "G-4", "G-5"], baselineGates: [],
      other: [] });
  });

  it("puts any other difference apart, an exit included", () => {
    const { baseline, quant } = pair();
    const changedExit = quant.rules.map((r) => (r.id === "X-S1" ? { ...r, action: "Hold" } : r));
    expect(differences({ baseline, quant: { ...quant, rules: changedExit } }).other)
      .toEqual(["X-S1"]);
  });
});

describe("a variant's changes", () => {
  it("names each moved value, a new one by its value alone", () => {
    expect(paramChanges(rule({ k: "1.0" }), rule({ k: "0.75" }))).toEqual(["k 1.0 → 0.75"]);
    expect(paramChanges(rule({ max_spread: "3%" }), rule({ bar: "1", max_spread: "3%" })))
      .toEqual(["bar 1"]);
    expect(paramChanges(rule({ min_dte: "90" }), rule({}))).toEqual(["min dte dropped"]);
  });

  it("lists a family's variants with their strategies, family by family", () => {
    expect(variantRows(RULES, ["grid", "ablation"]).map((v) => [v.variant.id, v.base.id]))
      .toEqual([["quant_pmcc--k075", "quant_pmcc"], ["quant_pmcc--a1", "quant_pmcc"],
                ["quant_pmcc--a3", "quant_pmcc"]]);
  });
});
