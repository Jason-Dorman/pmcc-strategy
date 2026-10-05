// The universe page (P7-05, UI-SPEC §6.5) over the fixture files: the three panels in order, the
// suitability screen with each measure's weeks (DEC-66), the headline by symbol with quant first
// and each row linked to its symbol's comparison page (DEC-111), the pooled universe as the
// comparison page shows it, the runs' manifests in the footer, and the in-panel states when a
// universe file is missing.
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES, HEADLINE, INDEX, SUITABILITY } from "../test/fixtures";
import { column, kv, panel, renderUniverse, rowAt, sortBy } from "../test/page";
import type { HeadlineRow } from "../types/generated/headline";
import type { SuitabilityRow } from "../types/generated/suitability";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

async function loaded() {
  await screen.findByRole("table", { name: "Symbol suitability" });
  await screen.findByRole("table", { name: "Headline by symbol" });
  await screen.findByRole("table", { name: "Pooled universe" });
}

/** A cell's value and the muted line under it. */
function stacked(table: HTMLElement, row: number, col: number): [string, string] {
  const cell = rowAt(table, row).querySelectorAll("td")[col];
  const sub = cell?.querySelector(".pm-subcell")?.textContent ?? "";
  return [(cell?.textContent ?? "").slice(0, -sub.length || undefined), sub];
}

function withSuitability(change: Partial<SuitabilityRow>, more: SuitabilityRow[] = []) {
  const [nvda] = SUITABILITY.rows;
  if (!nvda) throw new Error("fixture has no suitability row");
  return { ...FILES, "data/universe/suitability.json": {
    ...SUITABILITY, rows: [{ ...nvda, ...change }, ...more] } };
}

describe("the panels", () => {
  it("shows the three panels in order, each numbered, with no readouts", async () => {
    renderUniverse();
    await loaded();
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["Symbol suitability", "Headline by symbol", "Pooled universe"]);
    expect(within(await panel("Symbol suitability")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Pooled universe")).getByText("[3]")).toBeDefined();
    expect(document.querySelector(".pm-readout")).toBeNull();
  });

  it("shows the manifests of the runs the headline came from", async () => {
    renderUniverse();
    await loaded();
    const footer = screen.getByRole("contentinfo");
    expect(await within(footer).findByText("NVDA quant_pmcc")).toBeDefined();
    expect(within(footer).getByText("NVDA baseline_pmcc")).toBeDefined();
  });
});

describe("symbol suitability", () => {
  it("shows each measure formatted, with the weeks it's over", async () => {
    renderUniverse();
    await loaded();
    const table = screen.getByRole("table", { name: "Symbol suitability" });
    expect(column(table, 0)).toEqual(["NVDA"]);
    expect(stacked(table, 0, 1)).toEqual(["3.0%", "26 weeks"]);
    expect(stacked(table, 0, 2)).toEqual(["2.5% / 2.1%", "26 / 26 weeks"]);
    expect(stacked(table, 0, 3)).toEqual(["1.7%", "26 weeks"]);
    expect(stacked(table, 0, 4)).toEqual(["1.12", "26 weeks"]);
    expect(stacked(table, 0, 5)).toEqual(["2 of 26 weeks", "ratio above 1.20"]);
  });

  it("gives each measure its own count of weeks", async () => {
    renderUniverse(withSuitability({ long_weeks: 25, short_weeks: 24, iv_rv20_weeks: 23,
                                     g3_weeks: 22 }));
    await loaded();
    const table = screen.getByRole("table", { name: "Symbol suitability" });
    expect(stacked(table, 0, 1)[1]).toBe("25 weeks");
    expect(stacked(table, 0, 2)[1]).toBe("25 / 24 weeks");
    expect(stacked(table, 0, 3)[1]).toBe("24 weeks");
    expect(stacked(table, 0, 4)[1]).toBe("23 weeks");
    expect(stacked(table, 0, 5)[0]).toBe("2 of 22 weeks");
  });

  it("shows a spread under 1% to 2 dp, and a dash for a measure never read", async () => {
    renderUniverse(withSuitability({ median_spread_short_pct: 0.0081, iv_over_rv20: null,
                                     iv_rv20_weeks: 0 }));
    await loaded();
    const table = screen.getByRole("table", { name: "Symbol suitability" });
    expect(stacked(table, 0, 2)[0]).toBe("2.5% / 0.81%");
    expect(stacked(table, 0, 4)).toEqual(["—", "0 weeks"]);
  });

  it("links the event-week count to its gate, and names no rule by its ID", async () => {
    renderUniverse();
    await loaded();
    const table = screen.getByRole("table", { name: "Symbol suitability" });
    const link = within(rowAt(table, 0)).getByRole("link", { name: "2 of 26 weeks" });
    expect(link.getAttribute("href")).toBe("/rules/G-3");
    expect(within(table).getByRole("columnheader", { name: /Event week/ })).toBeDefined();
    const text = (await panel("Symbol suitability")).textContent ?? "";
    expect(text).not.toMatch(/\b[EGX]-[A-Z]?\d\b/);
    expect(text).toContain("first bar of each week-open session");
  });

  it("sorts the symbols by a measure", async () => {
    const qqq = { ...SUITABILITY.rows[0], symbol: "QQQ",
                  long_extrinsic_per_delta_pct_spot: 0.01 } as SuitabilityRow;
    renderUniverse(withSuitability({}, [qqq]));
    await loaded();
    const table = screen.getByRole("table", { name: "Symbol suitability" });
    expect(column(table, 0)).toEqual(["NVDA", "QQQ"]);
    await sortBy(table, /Long extrinsic/);
    expect(column(table, 0)).toEqual(["QQQ", "NVDA"]);
  });
});

describe("the headline by symbol", () => {
  it("has a row per symbol and strategy, quant first, each figure formatted", async () => {
    renderUniverse();
    await loaded();
    const table = screen.getByRole("table", { name: "Headline by symbol" });
    expect(column(table, 0)).toEqual(["NVDA", "NVDA"]);
    expect(column(table, 1)).toEqual(["Quant PMCC", "Baseline PMCC"]);
    expect(column(table, 2)).toEqual(["+$3,303.50", "+$3,672.50"]);
    expect(column(table, 3)).toEqual(["22.0%", "24.5%"]);
    expect(column(table, 4)).toEqual(["$4,261.50", "$4,211.50"]);
    expect(column(table, 5)).toEqual(["1.11", "1.24"]);
    expect(column(table, 6)).toEqual(["0.88", "0.79"]);
    expect(column(table, 7)).toEqual(["0.9% (−1.0% to 2.7%)", "1.0% (−0.9% to 2.8%)"]);
  });

  it("links each row to its symbol's comparison page", async () => {
    renderUniverse();
    await loaded();
    const table = screen.getByRole("table", { name: "Headline by symbol" });
    for (const i of [0, 1]) {
      expect(within(rowAt(table, i)).getByRole("link", { name: "NVDA" }).getAttribute("href"))
        .toBe("/compare/NVDA");
    }
  });

  it("keeps the file's symbol order, quant first within each, and dashes what's missing",
     async () => {
    const qqq = (strategy_id: string): HeadlineRow => ({
      ...(HEADLINE.rows[0] as HeadlineRow), symbol: "QQQ", strategy_id, sharpe_annualized: null,
      payoff_ratio: null, weekly_return: null });
    const headline = { ...HEADLINE, rows: [...HEADLINE.rows, qqq("baseline_pmcc"),
                                           qqq("quant_pmcc")] };
    renderUniverse({ ...FILES, "data/universe/headline.json": headline });
    await loaded();
    const table = screen.getByRole("table", { name: "Headline by symbol" });
    expect(column(table, 0)).toEqual(["NVDA", "NVDA", "QQQ", "QQQ"]);
    expect(column(table, 1)).toEqual(["Quant PMCC", "Baseline PMCC", "Quant PMCC",
                                      "Baseline PMCC"]);
    expect(column(table, 5)[2]).toBe("—");
    expect(column(table, 7)[2]).toBe("—");
  });
});

describe("the pooled universe", () => {
  it("shows what the comparison page's pooled panel shows", async () => {
    renderUniverse();
    await loaded();
    const values = kv(screen.getByRole("table", { name: "Pooled universe" }));
    expect(values["Symbols pooled"]).toBe("NVDA");
    expect(values["Quant PMCC, total P&L"]).toBe("+$712.00");
    expect(values["Symbols where quant beat the baseline"]).toBe("none (0 of 1)");
    expect((await panel("Pooled universe")).textContent).toContain("resamples each week");
  });
});

describe("missing files", () => {
  it("shows an in-panel state for each universe file the index lacks", async () => {
    renderUniverse({ ...FILES, "data/index.json": { ...INDEX, universe: {} } });
    const panels: [name: string, file: string][] = [
      ["Symbol suitability", "suitability"], ["Headline by symbol", "headline"],
      ["Pooled universe", "pooled"]];
    for (const [name, file] of panels) {
      expect(await within(await panel(name)).findByText(`No results for the universe / ${file}.`))
        .toBeDefined();
    }
    expect(within(screen.getByRole("contentinfo")).getByText("No run is shown on this page."))
      .toBeDefined();
  });
});
