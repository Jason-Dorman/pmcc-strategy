// The wheel review page (W4-01; PO, WD-22) over the fixture wheel and its friction run: the
// readouts, the thesis and each claim's verdict, the benchmark table, the fill model and the
// mid-vs-print evidence for puts and calls, the friction runs against the run at mid, and the
// rules, a linked rule outlined.
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES } from "../test/fixtures";
import { bodyRows, column, kv, panel, readout, renderWheelReview, rowAt } from "../test/page";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

describe("readouts", () => {
  it("shows the claims met and each claim's number against its benchmark", async () => {
    renderWheelReview();
    await screen.findByRole("table", { name: "Verdicts" });
    expect(readout("Claims met").value).toBe("2 of 3");
    expect(readout("P&L").value).toBe("+$502.50");
    expect(readout("Return on starting cash").value).toBe("2.0%");
    expect(readout("Return on starting cash").hint).toContain("the S&P 500's: 2.1%");
    expect(readout("Sharpe (annualized)").hint).toContain("the baseline PMCC's: 1.23");
    expect(readout("Prints inside the quote").value).toBe("66.7%");
    expect(readout("Prints inside the quote").hint).toContain("of 3 prints");
  });
});

describe("the panels", () => {
  it("leads with the thesis, unnumbered, then numbers the figures and tables", async () => {
    renderWheelReview();
    await screen.findByRole("table", { name: "Wheel rules" });
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["Thesis", "Verdicts", "Benchmarks", "Fill model",
                           "Mid vs print — puts", "Mid vs print — calls", "Friction runs",
                           "Rules"]);
    expect(within(await panel("Verdicts")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Rules")).getByText("[6]")).toBeDefined();
  });

  it("names no rule by its ID outside the rules' ID column (PO, WD-22)", async () => {
    renderWheelReview();
    const rules = await screen.findByRole("table", { name: "Wheel rules" });
    const text = [...screen.getAllByRole("region")]
      .filter((r) => r.getAttribute("aria-label") !== "Rules")
      .map((r) => r.textContent).join(" ");
    expect(text).not.toMatch(/W-[A-Z]\d/);
    expect(column(rules, 1)).toEqual(["W-T1", "W-P1", "W-C1", "W-X2", "W-X4"]);
  });

  it("says when the symbol has no wheel run", async () => {
    renderWheelReview("/wheel-review/QQQ");
    const thesis = await panel("Thesis");
    expect(await within(thesis).findByText("No results for QQQ / the wheel.")).toBeDefined();
  });

  it("says so when the index has friction runs but not the wheel's own", async () => {
    const index = structuredClone(FILES["data/index.json"]) as {
      symbols: { wheel: { run_id: string }[] }[];
    };
    const nvda = index.symbols[0];
    if (nvda) nvda.wheel = nvda.wheel.filter((r) => r.run_id !== "wheel");
    renderWheelReview("/wheel-review/NVDA", { ...FILES, "data/index.json": index });
    const verdicts = await panel("Verdicts");
    expect(await within(verdicts).findByText("No results for the wheel's own run."))
      .toBeDefined();
  });
});

describe("the thesis and its verdicts", () => {
  it("states the thesis as fixed, then how many claims the results meet", async () => {
    renderWheelReview();
    const thesis = await panel("Thesis");
    await within(thesis).findByText(/2 of 3 claims are met/);
    expect(thesis.textContent).toContain("volatility risk premium");
    expect(thesis.textContent).toContain("fixed on 2026-10-26, before the first run");
    expect(thesis.textContent).toContain("it beats the S&P 500 (not met)");
  });

  it("shows each claim's test, the wheel's number, its benchmark's and the verdict", async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Verdicts" });
    expect(rowAt(table, 0).textContent).toContain("It makes money");
    expect(rowAt(table, 0).textContent).toContain("+$502.50");
    expect(rowAt(table, 1).textContent).toContain("1.80");
    expect(rowAt(table, 1).textContent).not.toContain("break-even");
    expect(rowAt(table, 1).textContent).toContain("1.23");
    const third = rowAt(table, 2);
    expect(third.textContent).toContain("2.0%");
    expect(third.textContent).toContain("2.1%");
    expect(within(third).getByText("Not met").className).toBe("pm-flag");
  });

  it("names making money's bar as break-even, there being no outside benchmark (PO, WD-22)",
     async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Verdicts" });
    expect(within(rowAt(table, 0)).getAllByRole("cell")[4]?.textContent)
      .toBe("$0.00 (break-even)");
  });
});

describe("the benchmarks", () => {
  it("sets the wheel against the baseline PMCC and the S&P 500, each on its own cash",
     async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Benchmarks" });
    expect(column(table, 0)).toEqual(["Wheel", "Baseline PMCC", "S&P 500 (price)"]);
    expect(column(table, 1)).toEqual(["$25,000.00", "$15,000.00", "—"]);
    expect(column(table, 2)).toEqual(["2.0%", "4.8%", "2.1%"]);
    expect(column(table, 3)).toEqual(["1.80", "1.23", "—"]);
    const caption = (await panel("Benchmarks")).textContent;
    expect(caption).toContain("baseline_pmcc, config cccccccc");
    expect(caption).toContain("2026-03-27 close (6,368.85)");
  });
});

describe("the fill model and its evidence", () => {
  it("states the fill model the run used, and r", async () => {
    renderWheelReview();
    const f = kv(await screen.findByRole("table", { name: "Fill model" }));
    expect(f["Option fills"]).toBe("at the mid");
    expect(f["Spread capture, this run"]).toBe("0.00");
    expect(f["Fee per contract"]).toBe("$0.00");
    expect(f["Risk-free rate, r"]).toBe("3.71% (DGS3MO, as of 2026-03-27)");
    expect(f["Options sold, whose prints these are"]).toBe("2");
  });

  it("fits the puts' prints on their mids, the wheel's column alone, with the share inside",
     async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Mid vs print — puts fit" });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Print ≈ slope × mid + intercept", "NVDA"]);
    expect(kv(table)["Slope"]).toBe("1.0200");
    expect(kv(table)["Prints at or inside the quote"]).toBe("100.0%");
    expect((await panel("Mid vs print — puts")).querySelector("svg")).not.toBeNull();
  });

  it("shows a group without a fit as dashes", async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Mid vs print — calls fit" });
    expect(kv(table)["Slope"]).toBe("—");
    expect(kv(table)["Prints at or inside the quote"]).toBe("0.0%");
  });
});

describe("the friction runs", () => {
  it("lists each run by its spread capture against the run at mid, with its verdicts",
     async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Friction runs" });
    expect(column(table, 0)).toEqual(["0.00 (at mid, reported)", "0.50"]);
    expect(column(table, 1)).toEqual(["+$502.50", "+$497.50"]);
    expect(column(table, 2)).toEqual(["reference", "−$5.00"]);
    expect(column(table, 6)).toEqual(["1, 2 met · 3 not met", "1, 2 met · 3 not met"]);
  });
});

describe("the rules", () => {
  it("lists each rule's question and what happens, its reasoning under a toggle", async () => {
    renderWheelReview();
    const table = await screen.findByRole("table", { name: "Wheel rules" });
    expect(rowAt(table, 3).textContent).toContain("What if the put finishes in the money?");
    expect(rowAt(table, 3).textContent).toContain("We buy 100 shares at the strike.");
    fireEvent.click(within(table).getByRole("button", { name: "Rationale for W-X2" }));
    await waitFor(() => expect(table.textContent).toContain("Why put assigned."));
  });

  it("outlines the rule a link names", async () => {
    renderWheelReview("/wheel-review/NVDA/W-X2");
    const table = await screen.findByRole("table", { name: "Wheel rules" });
    const outlined = bodyRows(table).filter((r) => r.className === "pm-target");
    expect(outlined).toHaveLength(1);
    expect(outlined[0]?.textContent).toContain("W-X2");
  });

  it("says when a link names a rule the results lack", async () => {
    renderWheelReview("/wheel-review/NVDA/W-Z9");
    expect(await screen.findByText("The rule this link names isn't in these results."))
      .toBeDefined();
  });
});
