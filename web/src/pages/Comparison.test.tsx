// The comparison page (P7-02, UI-SPEC §6.1) over the fixture runs: its readouts, the panels in
// order, the purpose's sentence on the result's main limit read from both runs' legs (DEC-109),
// the NAV comparison and its values, the headline, the pooled universe and the ablations, and
// the in-panel states when a file is missing.
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES, INDEX, run } from "../test/fixtures";
import { bodyRows, column, kv, panel, readout, renderComparison, rowAt } from "../test/page";
import type { LegAttribution, RunResult } from "../types/generated/run_result";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

const QUANT = "data/NVDA/quant_pmcc.json";
const BASELINE = "data/NVDA/baseline_pmcc.json";
const CI = { mean: 0.008852, low: -0.010061, high: 0.027401, level: 0.95, resamples: 10000,
             seed: 535, weeks: 2 };

function quant(change: (r: RunResult) => RunResult): RunResult {
  return change(run("quant_pmcc", ["gate_log", "greek_attribution"]));
}

function baseline(change: (r: RunResult) => RunResult): RunResult {
  return change(run("baseline_pmcc", []));
}

/** A run with its P&L and weekly CI set. */
function withPnl(pnl: number, weekly: typeof CI | null = null) {
  return (r: RunResult): RunResult => {
    const metrics = r.summary.metrics;
    if (!metrics) throw new Error("fixture has no metrics");
    return { ...r, summary: { ...r.summary, metrics: { ...metrics, pnl, weekly_return: weekly } } };
  };
}

/** A run whose leg attribution is changed as given. */
function withLegs(change: Partial<LegAttribution>) {
  return (r: RunResult): RunResult => {
    const attribution = r.attribution;
    if (!attribution) throw new Error("fixture has no attribution");
    return { ...r, attribution: { ...attribution, leg: { ...attribution.leg, ...change } } };
  };
}

/** The long leg made more than the P&L on a rising stock; the shorts lost. */
const RODE = withLegs({ long_pnl: 900, long_intrinsic: 1000, long_extrinsic: -100,
                        net_short_premium: -188 });

async function loaded() {
  await screen.findByRole("table", { name: "Ablations" });
  await screen.findByRole("table", { name: "Headline" });
  await screen.findByRole("table", { name: "Pooled universe" });
}

describe("readouts", () => {
  it("shows both P&Ls and the quant layer's difference", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(withPnl(412)) });
    await loaded();
    expect(readout("Quant P&L").value).toBe("+$412.00");
    expect(readout("Baseline P&L").value).toBe("+$712.00");
    expect(readout("Quant − Baseline").value).toBe("−$300.00");
  });

  it("shows quant's return on starting NAV, its annualized Sharpe and the weeks traded", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(withPnl(712, CI)) });
    await loaded();
    expect(readout("Quant return on starting NAV").value).toBe("4.7%");
    expect(readout("Quant return on starting NAV").hint).toContain("not annualized; over 2 weeks");
    expect(readout("Quant Sharpe (annualized)").value).toBe("1.23");
    expect(readout("Quant Sharpe (annualized)").hint).toContain("from 2 daily returns");
    expect(readout("Weeks traded (Q / B)").value).toBe("1 / 1");
    expect(readout("Weeks traded (Q / B)").hint).toContain("of 2");
  });

  it("shows quant's weekly-return CI, with its mean, weeks and resamples in the hint", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(withPnl(712, CI)) });
    await loaded();
    expect(readout("Quant weekly-return 95% CI").value).toBe("−1.0% to 2.7%");
    const hint = readout("Quant weekly-return 95% CI").hint;
    expect(hint).toContain("mean 0.9%");
    expect(hint).toContain("2 weeks, 10,000 resamples");
  });

  it("shows a dash where a run has no CI", async () => {
    renderComparison();
    await loaded();
    expect(readout("Quant weekly-return 95% CI").value).toBe("—");
  });
});

describe("the panels", () => {
  it("puts the purpose first, unnumbered, then numbers the four figure and table panels", async () => {
    renderComparison();
    await loaded();
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["Purpose", "NAV — baseline vs quant", "Headline", "Pooled universe",
                           "Ablations"]);
    expect(within(await panel("Purpose")).queryByText(/^\[\d+\]$/)).toBeNull();
    expect(within(await panel("Ablations")).getByText("[4]")).toBeDefined();
  });

  it("shows both runs' manifests in the footer", async () => {
    renderComparison();
    await loaded();
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("NVDA baseline_pmcc")).toBeDefined();
    expect(within(footer).getByText("NVDA quant_pmcc")).toBeDefined();
  });
});

describe("the purpose", () => {
  it("says the long call riding a rising stock made the result, with each run's legs", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(RODE), [BASELINE]: baseline(RODE) });
    await loaded();
    const text = (await panel("Purpose")).textContent ?? "";
    expect(text).toContain("mostly the long call riding a rising stock");
    expect(text).toContain("+$900.00 for Quant PMCC and +$900.00 for Baseline PMCC");
    expect(text).toContain("netted −$188.00 for Quant PMCC and −$188.00 for Baseline PMCC");
  });

  it("makes no such claim unless every run shows it", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(RODE) });
    await loaded();
    const text = (await panel("Purpose")).textContent ?? "";
    expect(text).not.toContain("riding a rising stock");
    expect(text).toContain("the long leg made +$900.00 for Quant PMCC and +$672.50 for Baseline");
    expect(text).toContain("netted −$188.00 for Quant PMCC and +$39.50 for Baseline PMCC");
  });

  it("makes no claim where the long's intrinsic value fell, though the shorts lost", async () => {
    const fell = withLegs({ long_pnl: 900, long_intrinsic: -50, net_short_premium: -188 });
    renderComparison({ ...FILES, [QUANT]: quant(fell), [BASELINE]: baseline(fell) });
    await loaded();
    expect((await panel("Purpose")).textContent).not.toContain("riding a rising stock");
  });

  it("counts a short open at the end and X-S5's stock with the shorts", async () => {
    const legs = withLegs({ net_short_premium: 39.5, short_open: 10, assignment_stock_pnl: 5 });
    renderComparison({ ...FILES, [QUANT]: quant(legs) });
    await loaded();
    expect((await panel("Purpose")).textContent).toContain("netted +$34.50 for Quant PMCC");
  });

  it("states what a PMCC is and what the quant layer tests, and links the rules", async () => {
    renderComparison();
    await loaded();
    const purpose = await panel("Purpose");
    expect(purpose.textContent).toContain("poor man's covered call");
    expect(purpose.textContent).toContain("side by side on NVDA");
    expect(within(purpose).getByRole("link", { name: "the rules" }).getAttribute("href"))
      .toBe("/rules");
  });
});

describe("the NAV comparison", () => {
  const ahead = quant((r) => ({ ...r, ledger: (r.ledger ?? []).map((b) => ({ ...b,
                                                                       nav: b.nav + 100 })) }));

  it("draws both NAVs, its values in a table of every bar with the difference", async () => {
    renderComparison({ ...FILES, [QUANT]: ahead });
    await loaded();
    const nav = await panel("NAV — baseline vs quant");
    expect(within(nav).getByRole("figure", { name: "Quant PMCC and Baseline PMCC NAV on every bar" }))
      .toBeDefined();
    expect(nav.querySelector("svg")).not.toBeNull();
    const table = within(nav).getByRole("table", { name: "NAV by bar" });
    expect(bodyRows(table)).toHaveLength(4);
    expect(column(table, 0)[0]).toBe("2026-03-30 10:00 ET");
    expect(column(table, 1)[0]).toBe("$15,100.00");
    expect(column(table, 2)[0]).toBe("$15,000.00");
    expect(column(table, 3)).toEqual(["+$100.00", "+$100.00", "+$100.00", "+$100.00"]);
  });

  it("says when a run's file doesn't keep its ledger", async () => {
    renderComparison({ ...FILES, [QUANT]: quant((r) => ({ ...r, ledger: null })) });
    await loaded();
    expect(within(await panel("NAV — baseline vs quant"))
      .getByText("A run's file doesn't keep its ledger.")).toBeDefined();
  });
});

describe("the headline", () => {
  it("has one row per strategy, quant first, with each figure formatted", async () => {
    renderComparison({ ...FILES, [QUANT]: quant(withPnl(412, CI)) });
    await loaded();
    const table = screen.getByRole("table", { name: "Headline" });
    expect(column(table, 0)).toEqual(["Quant PMCC", "Baseline PMCC"]);
    expect(column(table, 1)).toEqual(["+$412.00", "+$712.00"]);
    expect(column(table, 2)).toEqual(["4.7%", "4.7%"]);
    expect(column(table, 3)).toEqual(["$150.00 (1.0%)", "$150.00 (1.0%)"]);
    expect(column(table, 4)).toEqual(["1.23", "1.23"]);
    expect(column(table, 5)).toEqual(["35.60", "35.60"]);
    expect(column(table, 6)).toEqual(["0.9% (−1.0% to 2.7%)", "—"]);
  });
});

describe("the pooled universe", () => {
  it("lists quant first, each strategy's total and CI, and where quant beat the baseline", async () => {
    renderComparison();
    await loaded();
    const table = screen.getByRole("table", { name: "Pooled universe" });
    const values = kv(table);
    expect(values["Symbols pooled"]).toBe("NVDA");
    expect(values["Quant PMCC, total P&L"]).toBe("+$712.00");
    expect(values["Quant PMCC, mean weekly return (95% CI)"]).toBe("0.9% (−1.0% to 2.7%), 2 weeks");
    expect(values["Baseline PMCC, mean weekly return (95% CI)"]).toBe(
      "1.0% (−0.9% to 2.8%), 2 weeks");
    expect(values["Symbols where quant beat the baseline"]).toBe("none (0 of 1)");
    expect(rowAt(table, 1).textContent).toContain("Quant PMCC");
  });
});

describe("the ablations", () => {
  it("shows quant's row as the reference, then each ablation against it", async () => {
    renderComparison();
    await loaded();
    const table = screen.getByRole("table", { name: "Ablations" });
    expect(column(table, 0)).toEqual(["Quant PMCC", "A1: quant with the baseline long leg",
                                      "A4: quant without the VRP gate"]);
    expect(column(table, 1)).toEqual(["+$712.00", "+$1,006.00", "+$457.50"]);
    expect(column(table, 2)).toEqual(["reference", "+$294.00", "−$254.50"]);
    expect(column(table, 3)).toEqual(["$150.00", "$150.00", "$150.00"]);
    expect(column(table, 4)).toEqual(["35.60", "—", "2.10"]);
    expect(column(table, 5)[0]).toBe("2.4% (−1.0% to 5.7%)");
    expect(within(table).getByRole("columnheader", { name: /Δ vs quant/ })).toBeDefined();
  });
});

describe("missing files", () => {
  it("shows an in-panel state for a symbol without robustness or a universe without pooling",
     async () => {
    const index = { ...INDEX, universe: {},
                    symbols: INDEX.symbols.map((s) => ({ ...s, files: {} })) };
    renderComparison({ ...FILES, "data/index.json": index });
    await screen.findByRole("table", { name: "Headline" });
    expect(within(await panel("Ablations")).getByText("No results for NVDA / robustness."))
      .toBeDefined();
    expect(within(await panel("Pooled universe"))
      .getByText("No results for the universe / pooled.")).toBeDefined();
  });

  it("shows a missing run in its panels, dashes in the readouts and no limit sentence",
     async () => {
    const index = { ...INDEX, symbols: INDEX.symbols.map((s) => ({
      ...s, runs: s.runs.filter((r) => r.run_id !== "quant_pmcc") })) };
    renderComparison({ ...FILES, "data/index.json": index });
    await screen.findByRole("table", { name: "Ablations" });
    expect(await within(await panel("Headline")).findByText("No results for NVDA / quant_pmcc."))
      .toBeDefined();
    expect(readout("Quant P&L").value).toBe("—");
    expect((await panel("Purpose")).textContent).not.toContain("the long leg made");
  });
});
