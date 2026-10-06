// The strategy page (P7-01, UI-SPEC §6.2) over the fixture runs: its readouts, each panel's
// figures, the record tables' cells, filters and links, the Reg T banner, and the sections a
// run's `report.sections` turns on.
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { bodyRows, kv, panel, readout, renderPage, rowAt, withQuant } from "../test/page";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

describe("readouts", () => {
  beforeEach(async () => {
    renderPage("quant");
    await screen.findByRole("table", { name: "Ledger" });
  });

  it("shows the run's ending NAV, P&L and returns", () => {
    expect(readout("Ending NAV").value).toBe("$15,712.00");
    expect(readout("P&L").value).toBe("+$712.00");
    expect(readout("Return on starting NAV").value).toBe("4.7%");
    expect(readout("Return on starting NAV").hint).toContain("not annualized");
    expect(readout("Sharpe (annualized)").value).toBe("1.23");
    expect(readout("Sharpe (annualized)").hint).toContain("× √252; from 2 daily returns");
  });

  it("shows drawdown, the lowest available funds and when, and the weeks", () => {
    expect(readout("Max drawdown").value).toBe("$150.00");
    expect(readout("Max drawdown").hint).toContain("1.0%");
    expect(readout("Min available funds").value).toBe("$9,100.00");
    expect(readout("Min available funds").hint).toContain("2026-03-30 16:00 ET");
    expect(readout("Weeks traded / skipped").value).toBe("1 / 1");
  });
});

describe("the panels", () => {
  it("numbers the quant page's nine panels in order", async () => {
    renderPage("quant");
    await screen.findByRole("table", { name: "Gate log" });
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["Account", "Reg T", "Cycle statistics", "Leg attribution", "Blotter",
                           "Gate log", "Ledger", "Position Greeks", "Greek attribution"]);
    expect(within(await panel("Position Greeks")).getByText("[8]")).toBeDefined();
    expect(within(await panel("Greek attribution")).getByText("[9]")).toBeDefined();
  });

  it("leaves the baseline's page without the gate log, renumbered (DEC-120)", async () => {
    renderPage("baseline");
    await screen.findByRole("table", { name: "Ledger" });
    expect(screen.queryByRole("region", { name: "Gate log" })).toBeNull();
    expect(within(await panel("Ledger")).getByText("[6]")).toBeDefined();
    expect(within(await panel("Position Greeks")).getByText("[7]")).toBeDefined();
    expect(within(await panel("Greek attribution")).getByText("[8]")).toBeDefined();
  });

  it("shows no position Greeks where a run's sections leave them out", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r, config: { ...r.config, strategy: { ...r.config.strategy,
        report: { detail: "full", sections: ["gate_log", "greek_attribution"] } } },
    })));
    await screen.findByRole("table", { name: "Gate log" });
    expect(screen.queryByRole("region", { name: "Position Greeks" })).toBeNull();
  });

  it("draws the account chart over the ledger's bars", async () => {
    renderPage("quant");
    const account = await panel("Account");
    expect(await within(account).findByRole("figure", {
      name: "NAV, initial and maintenance margin, available funds" })).toBeDefined();
    expect(within(account).getByText("4 hourly bars")).toBeDefined();
    expect(account.querySelector("svg")).not.toBeNull();
  });

  it("says when a run's file doesn't keep the ledger", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, ledger: null, blotter: null })));
    const blotter = await panel("Blotter");
    expect(await within(blotter).findByText("This run's file doesn't keep it.")).toBeDefined();
    expect(readout("Ending NAV").value).toBe("—");
  });
});

describe("Reg T", () => {
  it("shows the account at the last bar and its lowest funds", async () => {
    renderPage("quant");
    const values = kv(await screen.findByRole("table", { name: "Reg T" }));
    expect(values["Starting cash"]).toBe("$15,000.00");
    expect(values["NAV, at the end"]).toBe("$15,712.00");
    expect(values["Min available funds"]).toBe("$9,100.00, 2026-03-30 16:00 ET");
    expect(values["Bars with available funds below zero"]).toBe("0");
    expect(within(await panel("Reg T")).queryByRole("alert")).toBeNull();
  });

  it("warns that a breached position couldn't be held in a real Reg T account", async () => {
    renderPage("quant", withQuant((r) => ({
      ...r, summary: { ...r.summary, flag_counts: { funds_negative: 2 } } })));
    const alert = await within(await panel("Reg T")).findByRole("alert");
    expect(alert.textContent).toContain("below zero on 2 bars");
    expect(alert.textContent).toContain("couldn't have been held in a real Reg T account");
  });
});

describe("cycle statistics", () => {
  it("shows the cycle figures, the skips and exits linked to their rules", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Cycle statistics" });
    const values = kv(table);
    expect(values["Weeks traded / skipped"]).toBe("1 / 1, of 2");
    expect(values["Win rate, over 2 weeks a long was held"]).toBe("50.0%");
    expect(values["Payoff (average win ÷ |average loss|)"]).toBe("35.60");
    expect(values["Weekly credit, % of the long's cost"]).toBe("1.2%");
    expect(within(table).getByRole("link", { name: "Low vol premium" }).getAttribute("href"))
      .toBe("/rules/G-4");
    expect(within(table).getByRole("link", { name: "Take profit" }).getAttribute("href"))
      .toBe("/rules/X-S1");
    expect(values["Skips, by reason"]).toBe("Low vol premium 1");
    expect(table.textContent).not.toMatch(/[EXG]-[A-Z]?\d/); // no rule IDs (PO, DEC-107)
  });
});

describe("leg attribution", () => {
  it("adds the legs up to the P&L", async () => {
    renderPage("quant");
    const values = kv(await screen.findByRole("table", { name: "Leg attribution" }));
    expect(values["Short credits"]).toBe("+$69.50");
    expect(values["Short buybacks"]).toBe("−$30.00");
    expect(values["Net short premium"]).toBe("+$39.50");
    expect(values["Long-leg P&L"]).toBe("+$672.50");
    expect(values["P&L"]).toBe("+$712.00");
  });

  it("draws the two legs and lists their values by session", async () => {
    renderPage("quant");
    const legs = await panel("Leg attribution");
    expect(await within(legs).findByRole("figure")).toBeDefined();
    const table = within(legs).getByRole("table", { name: "Leg attribution by session" });
    expect(bodyRows(table)).toHaveLength(2);
  });
});

describe("the blotter", () => {
  it("shows each trade with its instrument, side, cash and rule", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Blotter" });
    const [buy, sell] = [rowAt(table, 0), rowAt(table, 1)];
    expect(buy.textContent).toContain("NVDAH212611500.U^H26");
    expect(buy.querySelector(".pm-subcell")?.textContent).toBe("NVDA  260821C00115000");
    expect(within(buy).getByText("BUY").className).toBe("pm-up");
    expect(within(buy).getByText("−$5,630.00").className).toBe("pm-down");
    expect(within(sell).getAllByText("$0.6950", { selector: "td" })).toHaveLength(2); // limit, fill
    expect(within(sell).getByRole("link", { name: "Sell short" }).getAttribute("href"))
      .toBe("/rules/E-S1");
  });

  it("filters by rule and by side", async () => {
    renderPage("quant");
    const blotter = await panel("Blotter");
    const table = await within(blotter).findByRole("table", { name: "Blotter" });
    const rules = within(blotter).getByRole("group", { name: "Filter by Trade" });
    fireEvent.click(within(rules).getByRole("button", { name: /Sell short/ }));
    expect(bodyRows(table)).toHaveLength(1);
    fireEvent.click(within(rules).getByRole("button", { name: /Sell short/ }));
    const sides = within(blotter).getByRole("group", { name: "Filter by Side" });
    fireEvent.click(within(sides).getByRole("button", { name: /BUY/ }));
    expect(bodyRows(table)).toHaveLength(2);
  });
});

describe("the gate log", () => {
  it("shows each gate's status and value, linked to its rule", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Gate log" });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Session", "Decision time", "Selected", "No quote", "Event week",
                             "Vol premium", "Min premium", "Outcome"]);
    const [sold, skipped] = [rowAt(table, 0), rowAt(table, 1)];
    expect(within(sold).getByText("pass 1.11").closest("a")?.getAttribute("href"))
      .toBe("/rules/G-3");
    expect(within(sold).getByText("pass $0.6950")).toBeDefined();
    expect(within(skipped).getByText("FIRE 0.95").className).toBe("pm-fire");
    expect(within(skipped).getByText("n/a")).toBeDefined();
    expect(within(skipped).getByText("—")).toBeDefined();
    expect(within(skipped).getByText("skipped").className).toBe("pm-skip");
    expect(within(skipped).getByRole("link", { name: "Low vol premium" })).toBeDefined();
  });

  it("filters by outcome", async () => {
    renderPage("quant");
    const gates = await panel("Gate log");
    const table = await within(gates).findByRole("table", { name: "Gate log" });
    const outcome = within(gates).getByRole("group", { name: "Filter by Outcome" });
    fireEvent.click(within(outcome).getByRole("button", { name: /skipped/ }));
    expect(bodyRows(table).map((r) => r.querySelector("td")?.textContent)).toEqual(["2026-04-06"]);
  });
});

describe("the ledger", () => {
  it("flags a stale mark and says what it means", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Ledger" });
    const stale = within(table).getByTitle("last valid mid carried; never filled");
    expect(stale.className).toBe("pm-flag");
    expect(stale.textContent).toBe("$0.5000");
  });

  it("filters by flag", async () => {
    renderPage("quant");
    const ledger = await panel("Ledger");
    const table = await within(ledger).findByRole("table", { name: "Ledger" });
    const flags = within(ledger).getByRole("group", { name: "Filter by Flags" });
    fireEvent.click(within(flags).getByRole("button", { name: /stale_short/ }));
    expect(bodyRows(table)).toHaveLength(1);
  });

  it("sorts by NAV", async () => {
    renderPage("quant");
    const table = await screen.findByRole("table", { name: "Ledger" });
    const nav = within(table).getByRole("columnheader", { name: "NAV" });
    fireEvent.click(within(nav).getByRole("button"));
    await waitFor(() => expect(bodyRows(table)[0]?.textContent).toContain("$14,850.00"));
  });
});

function cells(table: HTMLElement, index: number): string[] {
  return [...rowAt(table, index).querySelectorAll("td")].map((td) => td.textContent ?? "");
}

describe("position Greeks (DEC-120)", () => {
  it("shows each Greek's long, short and net mean in its units, against the textbook sign",
     async () => {
    renderPage("baseline");
    const position = await panel("Position Greeks");
    const table = within(position).getByRole("table", { name: "Position Greeks by leg" });
    const theta = cells(table, 2);
    expect(theta).toEqual(["θ theta", "$ a day", "−$9.10", "+$23.30", "+$14.20", "+", "100.0%",
                           "3"]);
    const delta = cells(table, 0);
    expect(delta.slice(2, 5)).toEqual(["89.4", "−31.2", "58.2"]);
    expect(cells(table, 1).slice(2, 6)).toEqual(["0.61", "−4.13", "−3.52", "−"]);
    expect(cells(table, 3)[6]).toBe("66.7%");
  });

  it("draws the net at every bar and lists its values", async () => {
    renderPage("quant");
    const position = await panel("Position Greeks");
    expect(await within(position).findByRole("figure", {
      name: "Net delta, gamma, theta and vega at every bar" })).toBeDefined();
    const values = within(position).getByRole("table", { name: "Position Greeks by bar" });
    expect(values.textContent).toContain("none");
    expect(values.textContent).toContain("open");
  });

  it("says when a run's file has none", async () => {
    renderPage("quant", withQuant((r) => ({ ...r, position_greeks: null })));
    const position = await panel("Position Greeks");
    expect(await within(position).findByText("This run's file has no position Greeks."))
      .toBeDefined();
  });
});

describe("Greek attribution", () => {
  it("shows each leg × component and the bars wholly residual", async () => {
    renderPage("quant");
    const greeks = await panel("Greek attribution");
    const rows = within(greeks).getByRole("table", { name: "Greek attribution by leg and component" });
    expect(rows.textContent).toContain("δ delta");
    expect(rows.textContent).toContain("112.0%");
    const legs = within(greeks).getByRole("table", { name: "Bars each leg was held" });
    expect(legs.textContent).toContain("1 of 4");
    expect(within(greeks).getByRole("figure")).toBeDefined();
  });
});
