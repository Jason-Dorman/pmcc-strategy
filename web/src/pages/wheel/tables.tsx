// The wheel page's three record tables (UI-SPEC §5, Spec › Accounting): the blotter with each
// row's Trade P&L (WD-28), the gate log of each week's sale, and the ledger, one row per bar, whose
// time picks that bar for the portfolio panel (WD-22). Rules read in plain words, linked to their
// rows on the wheel review page.
import type { ReactNode } from "react";

import { Instrument, Stacked } from "../../components/cells";
import type { TableColumn, TableFilter } from "../../components/DataTable";
import { money, moneySigned, price } from "../../format/money";
import { count, orDash, ratio, spreadPct } from "../../format/number";
import { ruleHint, ruleLabel } from "../../format/rule";
import { timeET } from "../../format/time";
import { stateLabel } from "../../format/wheel";
import type {
  LegOut,
  WheelBlotterRow,
  WheelGateRowOut,
  WheelLedgerRowOut,
  WheelResult,
} from "../../types/generated/wheel_result";
import { WheelRule } from "./rule";

/** Up or down by the sign of a number (Cash Δ, Trade P&L). */
function signClass(value: number): string | undefined {
  return value > 0 ? "pm-up" : value < 0 ? "pm-down" : undefined;
}

const SIDE_CLASS: Record<string, string> = { BUY: "pm-up", SELL: "pm-down" };

export const STALE = "last valid mid carried; never filled";

function notes(text: string): ReactNode {
  return <div className="pm-notes" title={text}>{text}</div>;
}

// ---- the blotter ------------------------------------------------------------------------------

export function blotterColumns(run: WheelResult): TableColumn<WheelBlotterRow>[] {
  const label = (r: WheelBlotterRow) => ruleLabel(r.rule_id, run.config.wheel.rules);
  return [
    { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
    { id: "instrument", header: "Instrument", sort: (r) => r.instrument.ric,
      cell: (r) => <Instrument instrument={r.instrument} /> },
    { id: "side", header: "Side", sort: (r) => r.side,
      cell: (r) => <span className={SIDE_CLASS[r.side]}>{r.side}</span> },
    { id: "qty", header: "Qty", num: true, sort: (r) => r.qty, cell: (r) => count(r.qty) },
    { id: "limit", header: "Limit", num: true, sort: (r) => r.limit ?? undefined,
      cell: (r) => orDash(r.limit, price) },
    { id: "fill", header: "Fill", num: true, sort: (r) => r.fill ?? undefined,
      cell: (r) => orDash(r.fill, price) },
    { id: "cash", header: "Cash Δ", num: true, sort: (r) => r.cash_delta,
      cell: (r) => <span className={signClass(r.cash_delta)}>{money(r.cash_delta)}</span> },
    { id: "trade", header: "Trade P&L", num: true, sort: (r) => r.trade_pnl ?? undefined,
      cell: (r) => (r.trade_pnl === null ? null
        : <span className={signClass(r.trade_pnl)}>{moneySigned(r.trade_pnl)}</span>) },
    { id: "rule", header: "Rule", sort: label, cell: (r) => <WheelRule id={r.rule_id} run={run} /> },
    { id: "notes", header: "Notes", sort: (r) => r.notes, cell: (r) => notes(r.notes) },
  ];
}

// ---- the gate log -----------------------------------------------------------------------------

const SELLING: Record<string, string> = { cash: "Put", shares: "Call" };

function num(value: unknown): number | undefined {
  if (typeof value === "number") return value;
  return typeof value === "string" && value !== "" ? Number(value) : undefined;
}

/** The option picked: its delta against the target, its mid and spread. */
function selected(row: WheelGateRowOut): ReactNode {
  const s = row.selected;
  if (!s) return <span className="pm-label">none</span>;
  const [delta, target, mid, spread] = [s.delta, s.target_delta, s.mid, s.spread_pct].map(num);
  const top = delta === undefined ? "—"
    : `delta ${ratio(delta)}${target === undefined ? "" : ` (target ${ratio(target)})`}`;
  const sub = [mid === undefined ? "" : `mid ${price(mid)}`,
               spread === undefined ? "" : `spread ${spreadPct(spread)}`];
  return <Stacked top={top} sub={sub.filter(Boolean).join(" · ")} />;
}

/** `sold`, linked to the rule that sold; or `skipped · Cash short`, the reason linked. */
function Outcome({ row, run }: { row: WheelGateRowOut; run: WheelResult }) {
  const { kind, rule_id: id } = row.outcome;
  if (kind !== "skipped") return <WheelRule id={id} run={run}>{kind}</WheelRule>;
  return (
    <>
      <span className="pm-skip">{kind}</span> · <WheelRule id={id} run={run} />
    </>
  );
}

export function gateLogColumns(run: WheelResult): TableColumn<WheelGateRowOut>[] {
  const rules = run.config.wheel.rules;
  return [
    { id: "session", header: "Session", sort: (r) => r.session, cell: (r) => r.session },
    { id: "selling", header: "Selling", sort: (r) => SELLING[r.state] ?? r.state,
      cell: (r) => SELLING[r.state] ?? stateLabel(r.state) },
    { id: "decision", header: "Decision time", sort: (r) => r.decision_time ?? undefined,
      cell: (r) => orDash(r.decision_time, timeET) },
    { id: "selected", header: "Selected", sort: (r) => num(r.selected?.delta), cell: selected },
    { id: "outcome", header: "Outcome",
      sort: (r) => `${r.outcome.kind} ${ruleLabel(r.outcome.rule_id, rules)}`,
      cell: (r) => <Outcome row={r} run={run} /> },
    { id: "notes", header: "Notes", sort: (r) => r.notes, cell: (r) => notes(r.notes) },
  ];
}

// ---- the ledger -------------------------------------------------------------------------------

/** A leg's mark, in the flag colour when it is stale. */
export function markCell(leg: LegOut): ReactNode {
  return leg.stale
    ? <span className="pm-flag" title={STALE}>{price(leg.mark)}</span>
    : price(leg.mark);
}

function legName(leg: LegOut | null): ReactNode {
  if (!leg) return <span className="pm-label">—</span>;
  const { ric, strike, expiry } = leg.instrument;
  return <Stacked top={ric} sub={`K ${orDash(strike, money)} · ${expiry ?? "—"}`} />;
}

function legColumns(side: "put" | "call", tag: string): TableColumn<WheelLedgerRowOut>[] {
  const leg = (r: WheelLedgerRowOut) => r[side];
  return [
    { id: side, header: side === "put" ? "Short put" : "Short call",
      sort: (r) => leg(r)?.instrument.ric, cell: (r) => legName(leg(r)) },
    { id: `${tag}mark`, header: `${tag} mark`, num: true, sort: (r) => leg(r)?.mark,
      cell: (r) => { const l = leg(r); return l ? markCell(l) : "—"; } },
    { id: `${tag}delta`, header: `${tag} delta`, num: true, sort: (r) => leg(r)?.delta ?? undefined,
      cell: (r) => orDash(leg(r)?.delta, ratio) },
  ];
}

function moneyColumn(id: string, header: string,
                     value: (r: WheelLedgerRowOut) => number | null): TableColumn<WheelLedgerRowOut> {
  return { id, header, num: true, sort: (r) => value(r) ?? undefined,
           cell: (r) => orDash(value(r), money) };
}

/** The ledger's columns; a bar's time is a button showing that bar's portfolio. */
export function ledgerColumns(onPick: (time: string) => void): TableColumn<WheelLedgerRowOut>[] {
  return [
    { id: "time", header: "Time (ET)", sort: (r) => r.time,
      cell: (r) => (
        <button type="button" className="pm-pick" onClick={() => onPick(r.time)}
                title="Show the portfolio at this bar">
          {timeET(r.time)}
        </button>
      ) },
    { id: "state", header: "Holding", sort: (r) => stateLabel(r.state),
      cell: (r) => stateLabel(r.state) },
    { id: "spot", header: "Stock", num: true, sort: (r) => r.spot ?? undefined,
      cell: (r) => orDash(r.spot, price) },
    moneyColumn("cash", "Cash", (r) => r.cash),
    moneyColumn("reserved", "Reserved", (r) => r.reserved),
    moneyColumn("free", "Free cash", (r) => r.free_cash),
    { id: "shares", header: "Shares", num: true, sort: (r) => r.shares,
      cell: (r) => (r.shares === 0 ? "—"
        : <Stacked top={`${count(r.shares)} sh`} sub={orDash(r.stock_mark, price)} />) },
    ...legColumns("put", "P"),
    ...legColumns("call", "C"),
    { id: "basis", header: "Cost basis", num: true, sort: (r) => r.cost_basis ?? undefined,
      cell: (r) => orDash(r.cost_basis, price) },
    moneyColumn("nav", "NAV", (r) => r.nav),
    { id: "flags", header: "Flags", sort: (r) => r.flags.join(" ") || undefined,
      cell: (r) => <span className="pm-flag">{r.flags.join(", ")}</span> },
  ];
}

// ---- the filters UI-SPEC §5 gives each table --------------------------------------------------

/** A filter over rule IDs whose buttons say what the rule did, its text on hover (PO, WD-22). */
function ruleFilter<T>(id: string, name: string, offer: (row: T) => string,
                       run: WheelResult): TableFilter<T> {
  return {
    id,
    name,
    offer: (row) => [offer(row)],
    label: (value) => ruleLabel(value, run.config.wheel.rules),
    hint: (value) => ruleHint(value, run.rule_text),
  };
}

export function blotterFilters(run: WheelResult): TableFilter<WheelBlotterRow>[] {
  return [
    ruleFilter("rule", "Trade", (r: WheelBlotterRow) => r.rule_id, run),
    { id: "side", name: "Side", offer: (r) => [r.side] },
  ];
}

export function gateLogFilters(run: WheelResult): TableFilter<WheelGateRowOut>[] {
  return [
    { id: "outcome", name: "Outcome", offer: (r) => [r.outcome.kind] },
    ruleFilter("rule", "Rule", (r: WheelGateRowOut) => r.outcome.rule_id, run),
  ];
}

export const LEDGER_FILTERS: readonly TableFilter<WheelLedgerRowOut>[] = [
  { id: "state", name: "Holding", offer: (r) => [r.state], label: stateLabel },
  { id: "flags", name: "Flags", offer: (r) => r.flags },
];
