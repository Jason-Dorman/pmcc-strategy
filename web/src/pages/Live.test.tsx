// The live page (L4-01; UI-SPEC §6 › Live) over the fixture `live.json`: the readouts from the
// latest night, the algorithm, the open orders with LSEG's strikes, the rules last, Sanji's files
// before he writes them, and the run log, newest first, with each pick's quote (PO, LD-15).
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES } from "../test/fixtures";
import { LIVE, QUOTED } from "../test/liveFixtures";
import { bodyRows, column, panel, readout, renderLive, rowAt, sortBy } from "../test/page";
import { pickFor, strikeValue } from "./live/sections";

function cells(row: HTMLElement): string[] {
  return [...row.querySelectorAll("td")].map((td) => td.textContent ?? "");
}

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

describe("readouts", () => {
  it("read the latest night: a failed run names its rule and says no order was made", async () => {
    renderLive();
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("State").value).toBe("—");
    expect(readout("Next session").value).toBe("2026-11-18");
    expect(readout("Tonight's decision").value).toBe("Failed");
    expect(readout("Tonight's decision").hint).toMatch(/^L-B1: Sanji's prices end/);
    expect(readout("Last run").value).toBe("2026-11-17 22:00 ET");
    expect(readout("Last run").hint).toContain("it failed, so no new order");
  });

  it("go by the row's outcome: an order row without a pick still reads as an order", async () => {
    const row = { ...QUOTED, pick: null };
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, runs: [row] } });
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("Tonight's decision").value).toBe("Order");
    expect(readout("Tonight's decision").hint).toMatch(/^L-O1: sell 1 155.00 put/);
  });

  it("show an order night's option and its delta", async () => {
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, runs: [QUOTED] } });
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("State").value).toBe("Cash");
    expect(readout("Cash").value).toBe("$25,000.00");
    expect(readout("Cost basis").value).toBe("—");
    expect(readout("Tonight's decision").value).toBe("Sell 1 put");
    expect(readout("Tonight's decision").hint).toBe(
      "$155 put, 2026-11-20; delta −0.32 at the close");
  });
});

describe("the panels", () => {
  it("lead with the algorithm, unnumbered, then the orders, the volatility, Sanji's files, the "
     + "log, and the rules last", async () => {
    renderLive();
    await screen.findByRole("table", { name: "Nightly run log" });
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["The algorithm", "Open orders", "Implied against realized",
                           "This week's skew", "Positions", "Fills", "Nightly run log",
                           "The rules"]);
    expect(within(await panel("Open orders")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Nightly run log")).getByText("[6]")).toBeDefined();
    expect(within(await panel("The rules")).getByText("[7]")).toBeDefined();
  });

  it("chart IV against RV20 by session, its values newest first (L4-02)", async () => {
    renderLive();
    const vol = await panel("Implied against realized");
    expect(await within(vol).findByRole("figure",
      { name: "NVDA's ATM IV, ~30 days and RV20 at each close" })).toBeDefined();
    const table = within(vol).getByRole("table", { name: "Volatility by session" });
    expect(column(table, 0)).toEqual(["2026-11-17", "2026-11-16", "2026-11-13"]);
    expect(cells(rowAt(table, 0))).toEqual(["2026-11-17", "48.0%", "52.0%", "−4.0", "$155.46",
                                     "2026-12-18", "$155.00"]);
    expect(cells(rowAt(table, 1)).slice(1, 4)).toEqual(["—", "49.0%", "—"]);
  });

  it("chart the coming week's skew, its values by strike (L4-02)", async () => {
    renderLive();
    const smile = await panel("This week's skew");
    expect(await within(smile).findByRole("figure",
      { name: "IV by strike for the 2026-11-20 expiry at the 2026-11-17 close" })).toBeDefined();
    const table = within(smile).getByRole("table", { name: "The skew by strike" });
    expect(column(table, 0)).toEqual(["$145.00", "$147.50", "$160.00"]);
    expect(cells(rowAt(table, 1))).toEqual(["$147.50", "put", "58.0%", "−0.30"]);
  });

  it("say so before the volatility workflow's first run", async () => {
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, vol: [], smile: null } });
    expect(await within(await panel("Implied against realized"))
      .findByText("No volatility pulled yet.")).toBeDefined();
    expect(within(await panel("This week's skew")).getByText("No skew pulled yet."))
      .toBeDefined();
  });

  it("say why the wheel, from the backtest, and link to its review", async () => {
    renderLive();
    const algorithm = await panel("The algorithm");
    await within(algorithm).findByRole("link", { name: "my wheel backtest review" });
    expect(algorithm.textContent).toContain(
      "From March 30 through September 25, 2026, the strategy returned $4,171.50 (16.7%) on "
      + "$25,000 in starting capital");
    expect(algorithm.textContent).toContain(
      "annualized Sharpe ratio of 1.57 compared with 1.24 for my baseline PMCC strategy");
    const link = within(algorithm).getByRole("link", { name: "my wheel backtest review" });
    expect(link.getAttribute("href")).toBe("/wheel-review/NVDA");
    expect(within(algorithm).queryByRole("table")).toBeNull();
    const rules = within(await panel("The rules")).getByRole("table",
                                                             { name: "Forward test rules" });
    expect(column(rules, 0)).toEqual(["L-B1", "L-P3", "L-O1"]);
  });

  it("list the open orders as a table, and nothing else", async () => {
    renderLive();
    const orders = await screen.findByRole("table", { name: "Open orders" });
    const cells = [...rowAt(orders, 0).querySelectorAll("td")].map((c) => c.textContent);
    expect(cells).toEqual(["wheel-2026-11-16-P-155", "2026-11-16", "Sell to open (SHT)", "1",
                           "put", "2026-11-20", "$155, delta −0.32", "155", "Limit, mid",
                           "open"]);
    const panelBody = await panel("Open orders");
    expect(panelBody.querySelector("pre")).toBeNull();
    expect(panelBody.querySelector("details")).toBeNull();
  });

  it("say so when there are no open orders", async () => {
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, orders: [] } });
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("No open orders tonight.")).toBeDefined();
  });

  it("show Sanji's files as he writes them, and say so before he does", async () => {
    renderLive();
    expect(await within(await panel("Positions")).findByText("No positions yet.")).toBeDefined();
    expect(within(await panel("Fills")).getByText("No fills yet.")).toBeDefined();
    cleanup();
    clearRunCache();
    const text = '[{"symbol": "NVDA", "cash": 24876.123456789}]\n'; // his key order, his digits
    renderLive("/live/NVDA", { ...FILES, "data/live.json": {
      ...LIVE, fills: { path: "mkt/fills.json", text } } });
    const fills = await panel("Fills");
    const file = await within(fills).findByLabelText("mkt/fills.json");
    expect(file.textContent).toBe(text);
  });

  it("read a strike token's value: a number's, a percent's, none for the rest", () => {
    expect([strikeValue("155"), strikeValue("152.5"), strikeValue("pct:-5"),
            strikeValue("pct:+2"), strikeValue("atm"), strikeValue(null)])
      .toEqual([155, 152.5, -5, 2, undefined, undefined]);
  });

  it("sort strikes by value, not as text", async () => {
    const at = (strike: string) => ({ ...LIVE.orders[0], id: `o-${strike}`, strike });
    const orders = [at("155"), at("92.5"), at("1000")];
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, orders } });
    const table = await screen.findByRole("table", { name: "Open orders" });
    await sortBy(table, /Sent as/);
    expect(column(table, 7)).toEqual(["92.5", "155", "1000"]);
  });

  it("show beside each order the strike LSEG gave the run, matched by session and contract",
     async () => {
    const [order] = LIVE.orders;
    if (!order) throw new Error("no order");
    const resent = { ...order, id: "wheel-2026-11-16-P-pct-5", strike: "pct:-5" }; // LD-29
    const unmatched = { ...order, id: "wheel-2026-11-23-P-pct-4", for: "2026-11-23",
                        expiry: "2026-11-27", strike: "pct:-4" };
    expect(pickFor(resent, LIVE.runs)?.strike).toBe("155");
    expect(pickFor({ ...order, contract: "call" }, LIVE.runs)).toBeNull();
    expect(pickFor(order, [])).toBeNull();
    renderLive("/live/NVDA", { ...FILES, "data/live.json": {
      ...LIVE, orders: [resent, unmatched] } });
    const table = await screen.findByRole("table", { name: "Open orders" });
    expect(column(table, 6)).toEqual(["$155, delta −0.32", "—"]);
    expect(column(table, 7)).toEqual(["pct:-5", "pct:-4"]);
  });

  it("log every night, newest first, with each pick's quote and a dash before it was kept",
     async () => {
    renderLive();
    const log = await screen.findByRole("table", { name: "Nightly run log" });
    expect(bodyRows(log)).toHaveLength(3);
    expect(column(log, 4)).toEqual(["Failed", "Order", "Order"]);
    expect(column(log, 7)).toEqual(["", "$155 put, 2026-11-20", "$155 put, 2026-11-20"]);
    expect(column(log, 8)).toEqual(["", "pct:-5", "—"]); // the strike sent (LD-29)
    expect(column(log, 11)).toEqual(["", "$2.4100", "—"]); // bid
    expect(column(log, 13)).toEqual(["", "$2.4350", "—"]); // mid
    expect(column(log, 14)).toEqual(["", "2.1%", "—"]); // spread
  });

  it("say when the route's symbol isn't the one the live wheel trades", async () => {
    renderLive("/live/QQQ");
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("The wheel forward test trades NVDA, not QQQ.")).toBeDefined();
  });

  it("say when the export wrote no live file", async () => {
    const files = { ...FILES, "data/index.json": { ...(FILES["data/index.json"] as object),
                                                   live: null } };
    renderLive("/live/NVDA", files);
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("No results for the wheel forward test.")).toBeDefined();
  });
});
