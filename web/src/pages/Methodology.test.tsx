// The methodology page (P7-04, UI-SPEC §6.4) over the fixture files: the panels in order, the
// Discovery first (PO, DEC-116, DEC-120), every figure read from the results (DEC-109), the
// fill check's scatters with the pooled fit and every pair, the grid and entry timing with its
// dispersion and fragility (PO, DEC-67), the fill model's sentence on the look-ahead guard and r,
// and no bar-timing, friction, stated-assumptions panel or footer (PO, DEC-121), with no rule ID
// in the prose (DEC-113).
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES, ROBUSTNESS, run, TIMING } from "../test/fixtures";
import { bodyRows, column, kv, panel, renderMethodology } from "../test/page";
import type { RobustnessRow } from "../types/generated/robustness";
import type { LegAttribution, MeanCI, RunResult } from "../types/generated/run_result";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

const QUANT = "data/NVDA/quant_pmcc.json";
const BASELINE = "data/NVDA/baseline_pmcc.json";

function ci(mean: number, low: number, high: number): MeanCI {
  return { mean, low, high, level: 0.95, resamples: 10000, seed: 535, weeks: 26 };
}

function quant(change: (r: RunResult) => RunResult): RunResult {
  return change(run("quant_pmcc", ["gate_log", "greek_attribution", "position_greeks"]));
}

function baseline(change: (r: RunResult) => RunResult): RunResult {
  return change(run("baseline_pmcc", ["greek_attribution", "position_greeks"]));
}

function withLegs(change: Partial<LegAttribution>) {
  return (r: RunResult): RunResult => {
    const attribution = r.attribution;
    if (!attribution?.leg) throw new Error("fixture has no leg attribution");
    return { ...r, attribution: { ...attribution, leg: { ...attribution.leg, ...change } } };
  };
}

function withWeekly(weekly: MeanCI) {
  return (r: RunResult): RunResult => {
    const metrics = r.summary.metrics;
    if (!metrics) throw new Error("fixture has no metrics");
    return { ...r, summary: { ...r.summary, metrics: { ...metrics, weekly_return: weekly } } };
  };
}

async function loaded() {
  await screen.findByRole("table", { name: "Parameter grid" });
  await screen.findByRole("table", { name: "Entry timing" });
  await screen.findByText(/look-ahead is impossible by construction/);
  await screen.findByText("One symbol, one window.");
}

describe("the panels", () => {
  it("leads with discovery, the grid under the scatters, numbering only figures and tables",
     async () => {
    renderMethodology();
    await loaded();
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual([
      "Discovery", "Fill model", "Mid vs print — weekly shorts",
      "Mid vs print — long-dated longs", "Parameter grid", "Entry timing",
    ]);
    expect(within(await panel("Mid vs print — weekly shorts")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Parameter grid")).getByText("[3]")).toBeDefined();
    expect(within(await panel("Entry timing")).getByText("[4]")).toBeDefined();
    expect(screen.queryByRole("contentinfo")).toBeNull();
    for (const prose of ["Discovery", "Fill model"]) {
      expect(within(await panel(prose)).queryByText(/^\[\d+\]$/)).toBeNull();
    }
  });

  it("shows the index's first symbol when the route names none", async () => {
    renderMethodology("/methodology");
    await loaded();
    expect(column(screen.getByRole("table", { name: "Parameter grid" }), 0))
      .toEqual(["Quant PMCC", "Grid: quant with k = 0.75"]);
  });

  it("names no rule by its ID in the prose", async () => {
    renderMethodology();
    await loaded();
    const ID = /\b[EGX]-[A-Z]?\d\b/;
    for (const prose of ["Discovery", "Fill model"]) {
      expect((await panel(prose)).textContent).not.toMatch(ID);
    }
  });
});

describe("mid vs print", () => {
  it("draws the scatter and states the symbol's fit beside the pooled one", async () => {
    renderMethodology();
    await loaded();
    const shorts = await panel("Mid vs print — weekly shorts");
    expect(within(shorts).getByRole("figure").getAttribute("aria-label"))
      .toBe("Mid vs print — weekly shorts: print against mid, 3 pairs");
    const fit = within(shorts).getByRole("table", { name: "Mid vs print — weekly shorts fit" });
    const rows = Object.fromEntries(bodyRows(fit).map((tr) => {
      const [k, a, b] = [...tr.querySelectorAll("td")].map((td) => td.textContent);
      return [k, [a, b]];
    }));
    expect(rows.Slope).toEqual(["0.9998", "0.9900"]);
    expect(rows.Intercept).toEqual(["$0.0023", "$0.0100"]);
    expect(rows["R²"]).toEqual(["0.9992", "0.9800"]);
    expect(rows["N (pairs)"]).toEqual(["3", "3"]);
    expect(rows["Median |print − mid|, of the spread"]).toEqual(["50.0%", "50.0%"]);
    expect(rows["Locked quotes, left out of the median"]).toEqual(["1", "1"]);
  });

  it("shows a dash where the universe has no pooled fit", async () => {
    renderMethodology();
    await loaded();
    const longs = await panel("Mid vs print — long-dated longs");
    const fit = within(longs).getByRole("table", { name: "Mid vs print — long-dated longs fit" });
    expect(bodyRows(fit)[0]?.textContent).toBe("Slope1.0003—");
  });

  it("builds every pair's table only once its disclosure is opened", async () => {
    renderMethodology();
    await loaded();
    const shorts = await panel("Mid vs print — weekly shorts");
    expect(within(shorts).queryByRole("table", { name: "Mid vs print — weekly shorts pairs" }))
      .toBeNull();
    const details = within(shorts).getByText("Values for every pair").closest("details");
    if (!details) throw new Error("no disclosure");
    details.open = true;
    fireEvent(details, new Event("toggle"));
    expect(await within(shorts).findByRole("table", { name: "Mid vs print — weekly shorts pairs" }))
      .toBeDefined();
  });
});

describe("the robustness tables", () => {
  it("publishes every grid run against quant", async () => {
    renderMethodology();
    await loaded();
    const table = screen.getByRole("table", { name: "Parameter grid" });
    expect(column(table, 0)).toEqual(["Quant PMCC", "Grid: quant with k = 0.75"]);
    expect(column(table, 2)).toEqual(["reference", "+$88.00"]);
  });

  it("states the timing dispersion over the fixed bars and calls it not fragile", async () => {
    renderMethodology();
    await loaded();
    const rows = kv(screen.getByRole("table", { name: "Timing dispersion" }));
    expect(rows).toEqual({
      "Fixed-bar runs": "2",
      "P&L range over them": "$212.00",
      "Sample standard deviation of P&L": "$149.91",
      "Mean weekly return over them": "0.8% to 1.0%",
      "The baseline's mean weekly return (95% CI)": "1.0% (−1.0% to 3.0%)",
      "Fragility": "Not fragile: every fixed bar inside the baseline's CI",
    });
  });

  it("flags timing as fragile when a fixed bar's mean leaves the baseline's CI", async () => {
    const [reference, t1, t2] = TIMING as [RobustnessRow, RobustnessRow, RobustnessRow];
    const out = { ...t2, weekly_return: ci(0.035, 0.01, 0.06) };
    renderMethodology("/methodology/NVDA", {
      ...FILES, "data/NVDA/robustness.json": { ...ROBUSTNESS, timing: [reference, t1, out] },
    });
    const table = await screen.findByRole("table", { name: "Timing dispersion" });
    const verdict = kv(table).Fragility;
    expect(verdict).toBe("Fragile: Timing: baseline, short decided on bar 2 (11:00) outside the "
      + "baseline's CI");
    expect(within(table).getByText(/^Fragile/).className).toBe("pm-flag");
  });
});

describe("the stated assumptions", () => {
  it("states the look-ahead guard and r from the index in one sentence (DEC-121)", async () => {
    renderMethodology();
    await loaded();
    expect((await panel("Fill model")).textContent).toContain("Every decision uses only data "
      + "stamped at or before its bar's end, and the engine refuses any request for later data, "
      + "so look-ahead is impossible by construction; implied volatilities and Greeks use a "
      + "risk-free rate of 3.71%.");
  });
});

describe("the prose's figures", () => {
  it("reads the fill model's captures and fee from rules.json", async () => {
    renderMethodology();
    await loaded();
    const rows = kv(screen.getByRole("table", { name: "Fill model" }));
    expect(rows["Spread capture, both strategies"]).toBe("0.00");
    expect(rows["Spread capture, the friction runs"]).toBeUndefined();
    expect(rows["Fee per contract"]).toBe("$0.00");
  });

  it("states each strategy's legs, and that the long made more than the P&L only if so",
     async () => {
    renderMethodology();
    await loaded();
    const limits = await panel("Discovery");
    expect(limits.textContent).toContain("Quant PMCC's long leg made +$672.50 (+$900.00 "
      + "intrinsic, −$227.50 extrinsic), its shorts +$39.50, for a P&L of +$712.00.");
    expect(limits.textContent).not.toContain("the long made more than the whole P&L");
    expect(limits.textContent).toContain("a window in which the stock rose under every long");
  });

  it("claims the long made the result where every run bears it out", async () => {
    const rode = withLegs({ long_pnl: 900, long_intrinsic: 1000, long_extrinsic: -100,
                            net_short_premium: -188 });
    renderMethodology("/methodology/NVDA",
                      { ...FILES, [QUANT]: quant(rode), [BASELINE]: baseline(rode) });
    expect(await screen.findByText(/In each, the long made more than the whole P&L\./))
      .toBeDefined();
  });

  it("states how much more quant's long made, and nothing of the ablations (DEC-116)",
     async () => {
    renderMethodology("/methodology/NVDA",
                      { ...FILES, [QUANT]: quant(withLegs({ long_pnl: 900 })) });
    const limits = await panel("Discovery");
    await within(limits).findByText(/Rolls book the gain/);
    expect(limits.textContent).toContain("Quant PMCC's long leg made +$227.50 more than Baseline "
      + "PMCC's.");
    expect(limits.textContent).not.toContain("A1");
    expect(limits.textContent).not.toContain("long selection");
  });

  it("says whether the strategies' weekly-return CIs overlap", async () => {
    renderMethodology("/methodology/NVDA", {
      ...FILES,
      [QUANT]: quant(withWeekly(ci(0.0089, -0.0101, 0.0274))),
      [BASELINE]: baseline(withWeekly(ci(0.0095, -0.0089, 0.0276))),
    });
    expect(await screen.findByText("The two can't be told apart.")).toBeDefined();
    expect((await panel("Discovery")).textContent)
      .toContain("95% CIs over 26 weeks that overlap.");
  });

  it("weighs each strategy's short theta against its long's (DEC-120)", async () => {
    renderMethodology();
    await loaded();
    const discovery = await panel("Discovery");
    await within(discovery).findByText("The weekly rent didn't cover the long's decay.");
    expect(discovery.textContent).toContain("Quant PMCC's shorts earned +$30.00 of theta while "
      + "its long paid −$40.00.");
    expect(discovery.textContent).toContain("A short is held at most from Monday to Friday, and "
      + "none in a skipped week, while the long decays every calendar day, weekends included.");
  });

  it("says when the rent covered the decay in one strategy only", async () => {
    const covered = (r: RunResult): RunResult => {
      const greek = r.attribution?.greek;
      if (!r.attribution || !greek) throw new Error("fixture has no Greek attribution");
      const rows = greek.rows.map((x) => (x.leg === "long" && x.component === "theta"
        ? { ...x, dollars: -10 } : x));
      return { ...r, attribution: { ...r.attribution, greek: { ...greek, rows } } };
    };
    renderMethodology("/methodology/NVDA", { ...FILES, [QUANT]: quant(covered) });
    expect(await screen.findByText("The weekly rent covered the long's decay in one strategy "
      + "only.")).toBeDefined();
  });

  it("leaves theta out where no run has a Greek attribution", async () => {
    const none = (r: RunResult): RunResult => (r.attribution
      ? { ...r, attribution: { ...r.attribution, greek: null } } : r);
    renderMethodology("/methodology/NVDA",
                      { ...FILES, [QUANT]: quant(none), [BASELINE]: baseline(none) });
    await loaded();
    expect((await panel("Discovery")).textContent).not.toContain("weekly rent");
  });
});
