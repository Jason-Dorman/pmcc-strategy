// The strategy page's regressions from P7-01's adversarial review (DEC-106): sections chosen by
// report.sections alone, the first bar of a tied minimum, readouts without metrics, the loading
// block, a breach in the ledger, panel notes, every leg and Greek field with its sign, and the
// record tables' cells, sorting and empty state.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { fakeFetch, GATE_LOG, LEDGER, run } from "../test/fixtures";
import {
  bodyRows,
  column,
  kv,
  panel,
  readout,
  renderPage,
  rowAt,
  sortBy,
  withQuant,
  withRun,
} from "../test/page";
import type { GateLogRowOut, LedgerRowOut } from "../types/generated/run_result";
import { Strategy } from "./Strategy";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

function at<T>(items: readonly T[], index: number): T {
  const item = items[index];
  if (item === undefined) throw new Error(`no item ${index}`);
  return item;
}

/** A week G-1 fired on: nothing selected, the later gates not evaluated (DEC-22). */
const G1_FIRED: GateLogRowOut = {
  session: "2026-04-13",
  decision_time: "2026-04-13T10:00:00-04:00",
  selected: null,
  gates: [
    { rule_id: "G-1", status: "fire", reason: "no quote", values: {} },
    { rule_id: "G-3", status: "not_evaluated", reason: "", values: {} },
    { rule_id: "G-4", status: "not_evaluated", reason: "", values: {} },
    { rule_id: "G-5", status: "not_evaluated", reason: "", values: {} },
  ],
  outcome: { kind: "skipped", rule_id: "G-1" },
  notes: "",
};

describe("sections come from report.sections, never the run's name (DEC-54)", () => {
  it("shows a quant run's gate log without Greeks when it lists only gate_log", async () => {
    renderPage("quant", withRun("quant_pmcc", ["gate_log"]));
    await screen.findByRole("table", { name: "Gate log" });
    expect(screen.queryByRole("region", { name: "Greek attribution" })).toBeNull();
  });

  it("shows a baseline run's Greek attribution when it lists greek_attribution", async () => {
    const greek = run("quant_pmcc", ["greek_attribution"]).attribution?.greek ?? null;
    renderPage("baseline", withRun("baseline_pmcc", ["greek_attribution"], (r) => ({
      ...r, attribution: r.attribution && { ...r.attribution, greek },
    })));
    await screen.findByRole("table", { name: "Bars each leg was held" });
    expect(screen.queryByRole("region", { name: "Gate log" })).toBeNull();
    expect(within(await panel("Greek attribution")).getByText("[7]")).toBeDefined();
  });
});

describe("readouts and Reg T", () => {
  it("dates the lowest available funds at the first bar that reaches it", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r,
      ledger: (r.ledger ?? []).map((row, i) => (i === 3 ? { ...row, available_funds: 9100 } : row)),
    })));
    await screen.findByRole("table", { name: "Ledger" });
    expect(readout("Min available funds").hint).toContain("2026-03-30 16:00 ET");
  });

  it("dashes each metric of a summary without metrics, and no other readout", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, summary: { ...r.summary, metrics: null } })));
    await screen.findByRole("table", { name: "Ledger" });
    for (const label of ["P&L", "Return on starting NAV", "Return on capital deployed",
                         "Max drawdown"]) {
      expect(readout(label).value).toBe("—");
    }
    expect(readout("Ending NAV").value).toBe("$15,712.00");
    expect(readout("Min available funds").value).toBe("$9,100.00");
    expect(readout("Weeks traded / skipped").value).toBe("1 / 1");
  });

  it("shows the flat loading block while the run loads", async () => {
    const index = fakeFetch();
    vi.stubGlobal("fetch", vi.fn((url: string) =>
      url.endsWith("index.json") ? index(url) : new Promise<Response>(() => undefined)));
    render(
      <MemoryRouter initialEntries={["/quant/NVDA"]}>
        <IndexProvider>
          <Routes><Route path="/:page/:symbol" element={<Strategy page="quant" />} /></Routes>
        </IndexProvider>
      </MemoryRouter>,
    );
    const account = await panel("Account");
    expect(await within(account).findByRole("status", { name: "Loading" })).toBeDefined();
    expect(readout("Ending NAV").value).toBe("—");
  });

  it("flags a breached bar's available funds in the ledger, and filters by its flag", async () => {
    const breach: LedgerRowOut = { ...at(LEDGER, 1), available_funds: -40,
                                   flags: ["funds_negative"] };
    renderPage("quant", withQuant((r) => ({
      ...r,
      ledger: (r.ledger ?? []).map((row, i) => (i === 1 ? breach : row)),
      summary: { ...r.summary, flag_counts: { funds_negative: 1 } },
    })));
    const ledger = await panel("Ledger");
    const table = await within(ledger).findByRole("table", { name: "Ledger" });
    expect(within(table).getByText("−$40.00").className).toBe("pm-flag");
    expect(within(table).getByText("$9,370.00", { selector: "span" }).className).toBe("");
    const flags = within(ledger).getByRole("group", { name: "Filter by Flags" });
    fireEvent.click(within(flags).getByRole("button", { name: /funds_negative/ }));
    expect(bodyRows(table)).toHaveLength(1);
    expect(within(await panel("Reg T")).getByRole("alert").textContent).toContain("1 bars");
  });

  it("leaves a panel's count off when the run's file doesn't keep the table", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, ledger: null, gate_log: null })));
    const account = await panel("Account");
    await within(account).findByText("This run's file doesn't keep it.");
    expect(account.querySelector(".pm-panel-note")).toBeNull();
    expect((await panel("Gate log")).querySelector(".pm-panel-note")).toBeNull();
    expect((await panel("Blotter")).querySelector(".pm-panel-note")?.textContent).toBe("3 trades");
  });
});

describe("cycle statistics, legs and Greeks read every field", () => {
  it("shows the average loss, premium captured and a zero exit", async () => {
    renderPage("quant");
    const values = kv(await screen.findByRole("table", { name: "Cycle statistics" }));
    expect(values["Average win / loss"]).toBe("$712.00 / −$20.00");
    expect(values["Premium captured (Σ(credit − buyback) ÷ Σ credit)"]).toBe("56.8%");
    expect(values["Exit mix"]).toBe("X-S1 1 · X-S2 0");
  });

  it("subtracts a short open at the end and adds X-S5's stock, each with its sign", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r,
      attribution: r.attribution && {
        ...r.attribution,
        leg: { ...r.attribution.leg, short_open: 12.5, assignment_stock_pnl: -50 },
      },
    })));
    const values = kv(await screen.findByRole("table", { name: "Leg attribution" }));
    expect(values["Short open at the end, at its mark"]).toBe("−$12.50");
    expect(values["Stock after X-S5"]).toBe("−$50.00");
    expect(values["Long leg, intrinsic change"]).toBe("+$900.00");
    expect(values["Long leg, extrinsic change"]).toBe("−$227.50");
  });

  it("lists each leg by session under its own heading", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Leg attribution by session" });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Session", "Long-leg P&L", "Net short premium"]);
    expect([...rowAt(table, 0).querySelectorAll("td")].map((td) => td.textContent))
      .toEqual(["2026-03-30", "−$150.00", "+$19.50"]);
  });

  it("dashes a share with no change to divide by, and keeps a residual's sign", async () => {
    renderPage("quant");
    const rows = await screen.findByRole("table",
                                         { name: "Greek attribution by leg and component" });
    const cells = bodyRows(rows).map((r) => [...r.querySelectorAll("td")].map((td) => td.textContent));
    expect(cells).toContainEqual(["long", "residual", "−$85.00", "−12.0%"]);
    expect(cells).toContainEqual(["short", "residual", "+$10.00", "—"]);
    const byBar = screen.getByRole("table", { name: "Cumulative residual by bar" });
    expect(column(byBar, 0)[0]).toBe("2026-03-30 10:00 ET");
  });
});

describe("the record tables", () => {
  it("shows a sale down, a gate's every value on hover, ET decision times and δ", async () => {
    renderPage("quant");
    const blotter = await screen.findByRole("table", { name: "Blotter" });
    expect(within(rowAt(blotter, 1)).getByText("SELL").className).toBe("pm-down");
    const gates = screen.getByRole("table", { name: "Gate log" });
    const sold = rowAt(gates, 0);
    expect(within(sold).getByText("pass 1.11").getAttribute("title")).toContain("ratio 1.105527");
    expect(within(sold).getByText("2026-03-30 10:00 ET")).toBeDefined();
    expect(within(sold).getByText("δ 0.19 · mid $0.6950")).toBeDefined();
    const ledger = screen.getByRole("table", { name: "Ledger" });
    const delta = within(ledger).getByRole("columnheader", { name: "L δ" });
    expect(delta.querySelector(".pm-greek")?.textContent).toBe("δ");
    expect(column(ledger, 4)[0]).toBe("0.90");
    expect(delta.getAttribute("aria-sort")).toBe("none");
  });

  it("sorts a gate not evaluated, and no option selected, last either way", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, gate_log: [...GATE_LOG, G1_FIRED] })));
    const table = await screen.findByRole("table", { name: "Gate log" });
    sortBy(table, "Selected");
    expect(column(table, 0).at(-1)).toBe("2026-04-13");
    sortBy(table, "G-3");
    const g3 = sortBy(table, "G-3");
    expect(g3.getAttribute("aria-sort")).toBe("descending");
    expect(column(table, 0).at(-1)).toBe("2026-04-13");
  });

  it("sorts a gate by status, then by the value it shows", async () => {
    const first = at(GATE_LOG, 0);
    const third: GateLogRowOut = {
      ...first,
      session: "2026-04-20",
      gates: first.gates.map((g) => (g.rule_id === "G-4"
        ? { ...g, values: { ratio: 1.2, min_ratio: 1 } } : g)),
    };
    renderPage("quant", withQuant((r) => ({ ...r, gate_log: [...GATE_LOG, third] })));
    const table = await screen.findByRole("table", { name: "Gate log" });
    sortBy(table, "G-4");
    expect(column(table, 5)).toEqual(["FIRE 0.95", "pass 1.20", "pass 1.40"]);
  });

  it("says so when the filters leave no rows", async () => {
    renderPage("quant");
    const blotter = await panel("Blotter");
    const table = await within(blotter).findByRole("table", { name: "Blotter" });
    const rules = within(blotter).getByRole("group", { name: "Filter by Rule" });
    fireEvent.click(within(rules).getByRole("button", { name: /E-S1/ }));
    const sides = within(blotter).getByRole("group", { name: "Filter by Side" });
    fireEvent.click(within(sides).getByRole("button", { name: /BUY/ }));
    expect(within(table).getByText("No rows.")).toBeDefined();
  });

  it("shows short stock with a true minus", async () => {
    const stock = {
      shares: -100, mark: 170.25, stale: false,
      instrument: { kind: "stock", ric: "NVDA.O", occ: null, expiry: null, strike: null },
    };
    renderPage("quant", withQuant((r) => ({
      ...r, ledger: (r.ledger ?? []).map((row, i) => (i === 3 ? { ...row, stock } : row)),
    })));
    const table = await screen.findByRole("table", { name: "Ledger" });
    expect(within(table).getByText("−100 sh")).toBeDefined();
  });
});
