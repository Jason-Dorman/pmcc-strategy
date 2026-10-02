// Each closing trade's P&L (PO, DEC-108), worked by hand: a close's own cash plus the share of
// the cash its position was opened for, fees included, per instrument.
import { describe, expect, it } from "vitest";

import { LONG, SHORT } from "../../test/fixtures";
import type { BlotterRow, InstrumentOut } from "../../types/generated/run_result";
import { tradeResults } from "./tradePnl";

const STOCK: InstrumentOut = { kind: "stock", ric: "NVDA.O", occ: null, expiry: null, strike: null };

function row(time: string, instrument: InstrumentOut, side: string, qty: number, cash: number,
             rule = "E-S1"): BlotterRow {
  return { time: `2026-04-${time}:00-04:00`, instrument, side, qty, cash_delta: cash, fee: 0,
           fill: null, limit: null, rule_id: rule, notes: "", audit: {} };
}

function pnl(rows: BlotterRow[]): (number | undefined)[] {
  const results = tradeResults(rows);
  return rows.map((r) => results.get(r)?.pnl);
}

describe("trade P&L", () => {
  it("credits a take profit with the sale it closes", () => {
    // sold at $1.26 (+$126.00), bought back at $0.165 (−$16.50): +$109.50
    const rows = [row("20T10:00", SHORT, "SELL", 1, 126), row("23T14:00", SHORT, "BUY", 1, -16.5, "X-S1")];
    expect(pnl(rows)).toEqual([undefined, 109.5]);
    const result = tradeResults(rows).get(rows[1] as BlotterRow);
    expect(result?.opened).toBe(126);
    expect(result?.openedAt).toBe("2026-04-20T10:00:00-04:00");
  });

  it("shows a defensive buyback above the credit as a loss", () => {
    expect(pnl([row("06T10:00", SHORT, "SELL", 1, 141),
                row("08T10:00", SHORT, "BUY", 1, -387.5, "X-S2")])).toEqual([undefined, -246.5]);
  });

  it("gives an expiry, which has no cash, the whole credit", () => {
    expect(pnl([row("06T10:00", SHORT, "SELL", 1, 85.5),
                row("10T16:00", SHORT, "EXPIRE", 1, 0, "X-S4")])).toEqual([undefined, 85.5]);
  });

  it("closes an assigned call at its credit, and the stock by its cover", () => {
    const rows = [
      row("06T10:00", SHORT, "SELL", 1, 90),
      row("10T16:00", SHORT, "ASSIGN", 1, 0, "X-S5"),
      row("10T16:00", STOCK, "SELL", 100, 17250, "X-S5"),
      row("13T10:00", STOCK, "BUY", 100, -17610, "X-S5"),
    ];
    expect(pnl(rows)).toEqual([undefined, 90, undefined, -360]);
  });

  it("nets a long's sale against what it cost, fees included", () => {
    expect(pnl([row("01T10:00", LONG, "BUY", 1, -5630.65, "E-L1"),
                row("27T10:00", LONG, "SELL", 1, 6260.35, "X-L2")])).toEqual([undefined, 629.7]);
  });

  it("closes a share of a larger position at its share of the opening cash", () => {
    const rows = [row("06T10:00", SHORT, "SELL", 2, 250), row("07T10:00", SHORT, "BUY", 1, -40),
                  row("08T10:00", SHORT, "BUY", 1, -60)];
    expect(pnl(rows)).toEqual([undefined, 85, 65]);
  });

  it("keeps each instrument apart, and starts afresh once a position is closed", () => {
    const other: InstrumentOut = { ...SHORT, ric: "NVDAD102618000.U^D26" };
    const rows = [
      row("06T10:00", SHORT, "SELL", 1, 100), row("06T10:00", LONG, "BUY", 1, -5000, "E-L1"),
      row("07T10:00", SHORT, "BUY", 1, -20, "X-S1"), row("13T10:00", SHORT, "SELL", 1, 80),
      row("13T10:00", other, "SELL", 1, 55), row("14T10:00", SHORT, "BUY", 1, -100, "X-S2"),
    ];
    expect(pnl(rows)).toEqual([undefined, undefined, 80, undefined, undefined, -20]);
  });

  it("sums in $0.0001 units, so no float error reaches a cent", () => {
    expect(pnl([row("06T10:00", SHORT, "SELL", 1, 0.1),
                row("07T10:00", SHORT, "BUY", 1, 0.2)])).toEqual([undefined, 0.3]);
  });
});
