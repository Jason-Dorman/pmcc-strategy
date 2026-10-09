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
    for (const label of ["P&L", "Return on starting NAV", "Sharpe (annualized)",
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
    expect(values["Exit mix"]).toBe("Take profit 1 · Defensive close 0");
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
    expect(values["Stock after a missed assignment"]).toBe("−$50.00");
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
  it("shows a sale down, a gate's every value on hover, ET decision times and delta in words",
     async () => {
    renderPage("quant");
    const blotter = await screen.findByRole("table", { name: "Blotter" });
    expect(within(rowAt(blotter, 1)).getByText("SELL").className).toBe("pm-down");
    const gates = screen.getByRole("table", { name: "Gate log" });
    const sold = rowAt(gates, 0);
    expect(within(sold).getByText("pass 1.11").getAttribute("title")).toContain("ratio 1.105527");
    expect(within(sold).getByText("2026-03-30 10:00 ET")).toBeDefined();
    expect(within(sold).getByText("delta 0.19 · mid $0.6950")).toBeDefined();
    const ledger = screen.getByRole("table", { name: "Ledger" });
    const delta = within(ledger).getByRole("columnheader", { name: "L delta" });
    expect(delta.querySelector(".pm-greek")).toBeNull();
    expect(column(ledger, 4)[0]).toBe("0.90");
    expect(delta.getAttribute("aria-sort")).toBe("none");
  });

  it("sorts a gate not evaluated, and no option selected, last either way", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, gate_log: [...GATE_LOG, G1_FIRED] })));
    const table = await screen.findByRole("table", { name: "Gate log" });
    await sortBy(table, "Selected");
    expect(column(table, 0).at(-1)).toBe("2026-04-13");
    await sortBy(table, "Event week");
    const g3 = await sortBy(table, "Event week");
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
    await sortBy(table, "Vol premium");
    expect(column(table, 5)).toEqual(["FIRE 0.95", "pass 1.20", "pass 1.40"]);
  });

  it("says so when the filters leave no rows", async () => {
    renderPage("quant");
    const blotter = await panel("Blotter");
    const table = await within(blotter).findByRole("table", { name: "Blotter" });
    const rules = within(blotter).getByRole("group", { name: "Filter by Trade" });
    fireEvent.click(within(rules).getByRole("button", { name: /Sell short/ }));
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

describe("filter buttons say what the trade was, not its rule ID (PO, DEC-107)", () => {
  it("names each trade in the blotter's filter, the rule's text on hover", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r,
      rule_text: { "X-S1": { title: "", summary: "", condition: "Short mid ≤ 25% of the credit",
                             action: "Buy to close at mid", rationale: "" } },
    })));
    const blotter = await panel("Blotter");
    await within(blotter).findByRole("table", { name: "Blotter" });
    const trades = within(blotter).getByRole("group", { name: "Filter by Trade" });
    const buttons = within(trades).getAllByRole("button").map((b) => b.textContent);
    expect(buttons).toEqual(["Open long 1", "Sell short 1", "Take profit 1"]);
    expect(buttons.join(" ")).not.toMatch(/[EXG]-[A-Z]?\d/);
    expect(within(trades).getByRole("button", { name: /Take profit/ }).getAttribute("title"))
      .toBe("Short mid ≤ 25% of the credit → Buy to close at mid");
  });

  it("names why a week was skipped in the gate log's filter", async () => {
    renderPage("quant");
    const gates = await panel("Gate log");
    await within(gates).findByRole("table", { name: "Gate log" });
    const reasons = within(gates).getByRole("group", { name: "Filter by Reason" });
    expect(within(reasons).getAllByRole("button").map((b) => b.textContent))
      .toEqual(["Sell short 1", "Low vol premium 1"]);
  });

  it("names each trade's rule in the blotter, linked to the rule, its text on hover", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r,
      rule_text: { "E-L1": { title: "", summary: "", condition: "No long call is held",
                             action: "Buy the selection", rationale: "" } },
    })));
    const table = await screen.findByRole("table", { name: "Blotter" });
    const open = within(rowAt(table, 0)).getByRole("link", { name: "Open long" });
    expect(open.getAttribute("href")).toBe("/rules/E-L1");
    expect(open.getAttribute("title")).toBe("No long call is held → Buy the selection");
    expect(column(table, 8)).toEqual(["Open long", "Sell short", "Take profit"]);
  });

  it("names the gate log's gates and outcomes, each still linked to its rule", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Gate log" });
    expect(column(table, 7)).toEqual(["sold", "skipped · Low vol premium"]);
    expect(within(rowAt(table, 0)).getByRole("link", { name: "sold" }).getAttribute("href"))
      .toBe("/rules/E-S1");
    expect(within(rowAt(table, 1)).getByRole("link", { name: "Low vol premium" })
      .getAttribute("href")).toBe("/rules/G-4");
    for (const name of ["Blotter", "Gate log"]) {
      const shown = screen.getByRole("table", { name });
      const text = [...shown.querySelectorAll("th, td")].map((c) => c.textContent).join(" ");
      expect(text, name).not.toMatch(/\b[EXG]-[A-Z]?\d\b/);
    }
  });

  it("falls back to the rule's YAML name for a rule it has no plain label for", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r,
      blotter: (r.blotter ?? []).map((row, i) => (i === 2 ? { ...row, rule_id: "X-Z9" } : row)),
      config: { ...r.config, strategy: { ...r.config.strategy, rules: [
        { id: "X-Z9", name: "Some new exit", kind: "k", params: {}, title: "", summary: "",
          condition: "", action: "", rationale: "" },
      ] } },
    })));
    const blotter = await panel("Blotter");
    await within(blotter).findByRole("table", { name: "Blotter" });
    const trades = within(blotter).getByRole("group", { name: "Filter by Trade" });
    expect(within(trades).getByRole("button", { name: /Some new exit/ })).toBeDefined();
  });
});

describe("the blotter's Trade P&L (PO, DEC-108)", () => {
  it("shows a closing trade's round trip, and nothing on the rows that open", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Blotter" });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers[7]).toBe("Trade P&L");
    // sold at +$69.50, bought back for −$30.00
    expect(column(table, 7)).toEqual(["", "", "+$39.50"]);
    const close = within(rowAt(table, 2)).getByText("+$39.50");
    expect(close.className).toBe("pm-up");
    expect(close.getAttribute("title")).toBe("opened 2026-03-30 10:00 ET for +$69.50");
  });
});
