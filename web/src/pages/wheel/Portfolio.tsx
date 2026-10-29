// Wheel [2], the portfolio at a bar (Spec › Accounting, requirement 2; PO, WD-22): one ledger row
// read as a portfolio, cash (reserved and free), the shares, the short put and the short call,
// each with its mark, and NAV. The bar is picked by a click on the NAV chart or a ledger time, or
// here: a session, then a bar in it, or a step either way.
import type { ReactNode } from "react";

import { KeyValue } from "../../components/cells";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { money, price } from "../../format/money";
import { count, orDash, ratio } from "../../format/number";
import { timeET } from "../../format/time";
import { stateWords } from "../../format/wheel";
import type { LegOut, WheelLedgerRowOut, WheelResult } from "../../types/generated/wheel_result";
import { markCell } from "./tables";

const SHARES_PER_CONTRACT = 100;

/** A bar's ET session and clock time: `2026-06-05`, `16:00`. */
function when(row: WheelLedgerRowOut): { session: string; clock: string } {
  const shown = timeET(row.time);
  return { session: shown.slice(0, 10), clock: shown.slice(11, 16) };
}

/** Each session's first bar, in order. */
export function sessionStarts(ledger: readonly WheelLedgerRowOut[]): Map<string, number> {
  const starts = new Map<string, number>();
  ledger.forEach((row, i) => {
    const { session } = when(row);
    if (!starts.has(session)) starts.set(session, i);
  });
  return starts;
}

/** A short option: its RIC and OCC symbol, strike and expiry, mark and what it is worth to the
 * book (the mark × 100 per contract, owed), and its delta. */
function Leg({ leg }: { leg: LegOut | null }) {
  if (!leg) return <>none</>;
  const { ric, occ, strike, expiry } = leg.instrument;
  const owed = -leg.mark * SHARES_PER_CONTRACT * leg.qty;
  return (
    <div>
      <div>{count(leg.qty)} × {ric}</div>
      <div className="pm-subcell">{occ ?? ""}</div>
      <div className="pm-subcell">strike {orDash(strike, money)} · expires {expiry ?? "—"}</div>
      <div className="pm-subcell">
        mark {markCell(leg)} · value {money(owed)} · delta {orDash(leg.delta, ratio)}
      </div>
    </div>
  );
}

function shares(row: WheelLedgerRowOut): ReactNode {
  if (row.shares === 0) return "none";
  const mark = row.stock_mark;
  return mark === null ? `${count(row.shares)} sh`
    : `${count(row.shares)} sh × ${price(mark)} = ${money(row.shares * mark)}`;
}

function Picker({ ledger, index, onIndex }: {
  ledger: readonly WheelLedgerRowOut[];
  index: number;
  onIndex: (index: number) => void;
}) {
  const starts = sessionStarts(ledger);
  const row = ledger[index];
  const session = row ? when(row).session : "";
  const first = starts.get(session) ?? 0;
  const bars = ledger.map((r, i) => ({ i, ...when(r) })).filter((b) => b.session === session);
  return (
    <div className="pm-picker">
      <button type="button" className="pm-chip" aria-label="Previous bar"
              disabled={index <= 0} onClick={() => onIndex(index - 1)}>◀</button>
      <Select value={session} onValueChange={(s) => onIndex(starts.get(s) ?? first)}>
        <SelectTrigger aria-label="Session"><SelectValue /></SelectTrigger>
        <SelectContent className="pm-select-long">
          {[...starts.keys()].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
        </SelectContent>
      </Select>
      <Select value={String(index)} onValueChange={(v) => onIndex(Number(v))}>
        <SelectTrigger aria-label="Bar"><SelectValue /></SelectTrigger>
        <SelectContent>
          {bars.map((b) => <SelectItem key={b.i} value={String(b.i)}>{b.clock} ET</SelectItem>)}
        </SelectContent>
      </Select>
      <button type="button" className="pm-chip" aria-label="Next bar"
              disabled={index >= ledger.length - 1} onClick={() => onIndex(index + 1)}>▶</button>
    </div>
  );
}

export function Portfolio({ run, index, onIndex }: {
  run: WheelResult;
  index: number;
  onIndex: (index: number) => void;
}) {
  const row = run.ledger[index];
  if (!row) return <>No bars.</>;
  const flags = row.flags.length > 0
    ? <span className="pm-flag">{row.flags.join(", ")}</span> : "none";
  return (
    <div className="pm-stack">
      <Picker ledger={run.ledger} index={index} onIndex={onIndex} />
      <KeyValue
        label="Portfolio"
        rows={[
          ["Bar", timeET(row.time)],
          ["Holding", stateWords(row.state)],
          [`${run.manifest.symbol} last trade`, orDash(row.spot, price)],
          ["Cash", money(row.cash)],
          ["Reserved for the put (strike × 100)", money(row.reserved)],
          ["Free cash", money(row.free_cash)],
          ["Shares, at their mark", shares(row)],
          ["Short put", <Leg key="put" leg={row.put} />],
          ["Short call", <Leg key="call" leg={row.call} />],
          ["Cost basis, per share", orDash(row.cost_basis, price)],
          ["NAV", money(row.nav)],
          ["Flags", flags],
        ]}
      />
    </div>
  );
}
