// Each closing trade's P&L (PO, DEC-108): the blotter's Cash Δ is one row's cash, so a take
// profit, a buyback, reads negative though the round trip made money. Walking the blotter in
// order, each instrument's position is kept by its RIC with the engine's signs (BUY +1, SELL −1,
// EXPIRE and ASSIGN +1, as pmcc/accounting/book.py). A row that shrinks a position closes that
// share of it: its P&L is its own cash plus that share of the cash the position was opened for,
// fees included. An expiry or assignment closes a short call with no cash, so its P&L is the
// credit; X-S5's stock is its own position, closed by its cover. Sums run in $0.0001 units
// (DEC-44), so no float error reaches a cent.
import type { BlotterRow } from "../../types/generated/run_result";

const SIGN: Readonly<Record<string, number>> = { BUY: 1, SELL: -1, EXPIRE: 1, ASSIGN: 1 };
const UNITS = 10_000; // $0.0001 units per dollar

export interface TradeResult {
  /** The round trip's P&L for this close, net of fees. */
  pnl: number;
  /** The cash the closed share was opened for, and when that position was first opened. */
  opened: number;
  openedAt: string;
}

interface Position {
  qty: number; // signed: + long, − short
  cash: number; // the open quantity's opening cash, in units
  since: string;
}

const units = (dollars: number) => Math.round(dollars * UNITS);

/** The result of every row that closes some of a position, keyed by the row. */
export function tradeResults(blotter: readonly BlotterRow[]): Map<BlotterRow, TradeResult> {
  const open = new Map<string, Position>();
  const results = new Map<BlotterRow, TradeResult>();
  for (const row of blotter) {
    const signed = (SIGN[row.side] ?? 0) * row.qty;
    const key = row.instrument.ric;
    const held = open.get(key) ?? { qty: 0, cash: 0, since: row.time };
    const closing = held.qty !== 0 && Math.sign(signed) === -Math.sign(held.qty);
    if (!closing) {
      open.set(key, { qty: held.qty + signed, cash: held.cash + units(row.cash_delta),
                      since: held.qty === 0 ? row.time : held.since });
      continue;
    }
    const closed = Math.min(Math.abs(signed), Math.abs(held.qty));
    const share = Math.round((held.cash * closed) / Math.abs(held.qty));
    results.set(row, { pnl: (units(row.cash_delta) + share) / UNITS, opened: share / UNITS,
                       openedAt: held.since });
    const left = held.qty + Math.sign(signed) * closed;
    if (left === 0) open.delete(key);
    else open.set(key, { qty: left, cash: held.cash - share, since: held.since });
  }
  return results;
}
