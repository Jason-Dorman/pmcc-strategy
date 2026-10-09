// The strategy page's three record tables (UI-SPEC §5): the blotter, the gate log and the ledger,
// with the columns, cell classes and filters §5 gives each. Rule IDs link to their rules.
import type { ReactNode } from "react";

import { Instrument, RuleLink, Stacked } from "../../components/cells";
import type { TableColumn, TableFilter } from "../../components/DataTable";
import { money, moneySigned, price } from "../../format/money";
import { count, orDash, ratio } from "../../format/number";
import { gateName, ruleHint, ruleLabel } from "../../format/rule";
import { tradeResults, type TradeResult } from "./tradePnl";
import { timeET } from "../../format/time";
import type {
  BlotterRow,
  GateLogRowOut,
  GateOut,
  LedgerRowOut,
  LegOut,
  RunResult,
  StockOut,
} from "../../types/generated/run_result";

/** Up or down by the sign of a number (Cash Δ). */
function signClass(value: number): string | undefined {
  return value > 0 ? "pm-up" : value < 0 ? "pm-down" : undefined;
}

const SIDE_CLASS: Record<string, string> = { BUY: "pm-up", SELL: "pm-down" };

// ---- the blotter ------------------------------------------------------------------------------

/** A rule in plain words, linked to its rule, its condition → action on hover (PO, DEC-107). */
function Rule({ id, run, children }: { id: string; run: RunResult; children?: ReactNode }) {
  return (
    <RuleLink id={id} title={ruleHint(id, run.rule_text) || undefined}>
      {children ?? ruleLabel(id, run.config.strategy.rules)}
    </RuleLink>
  );
}

/** A closing row's round-trip P&L, with what it was opened for on hover (PO, DEC-108). */
function TradePnl({ result }: { result: TradeResult | undefined }) {
  if (!result) return null;
  const hint = `opened ${timeET(result.openedAt)} for ${moneySigned(result.opened)}`;
  return <span className={signClass(result.pnl)} title={hint}>{moneySigned(result.pnl)}</span>;
}

export function blotterColumns(run: RunResult): TableColumn<BlotterRow>[] {
  const label = (r: BlotterRow) => ruleLabel(r.rule_id, run.config.strategy.rules);
  const trades = tradeResults(run.blotter ?? []);
  return [
  { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
  { id: "instrument", header: "Instrument", sort: (r) => r.instrument.ric,
    cell: (r) => <Instrument instrument={r.instrument} /> },
  { id: "side", header: "Side", sort: (r) => r.side,
    cell: (r) => <span className={SIDE_CLASS[r.side]}>{r.side}</span> },
  { id: "qty", header: "Qty", num: true, sort: (r) => r.qty, cell: (r) => r.qty },
  { id: "limit", header: "Limit", num: true, sort: (r) => r.limit ?? undefined,
    cell: (r) => orDash(r.limit, price) },
  { id: "fill", header: "Fill", num: true, sort: (r) => r.fill ?? undefined,
    cell: (r) => orDash(r.fill, price) },
  { id: "cash", header: "Cash Δ", num: true, sort: (r) => r.cash_delta,
    cell: (r) => <span className={signClass(r.cash_delta)}>{money(r.cash_delta)}</span> },
  { id: "trade", header: "Trade P&L", num: true, sort: (r) => trades.get(r)?.pnl,
    cell: (r) => <TradePnl result={trades.get(r)} /> },
  { id: "rule", header: "Rule", sort: label, cell: (r) => <Rule id={r.rule_id} run={run} /> },
  { id: "notes", header: "Notes", sort: (r) => r.notes,
    cell: (r) => <div className="pm-notes" title={r.notes}>{r.notes}</div> },
  ];
}

// ---- the gate log -----------------------------------------------------------------------------

const STATUS_TEXT: Record<string, string> = { pass: "pass", fire: "FIRE", "n/a": "n/a" };

/** The one value a gate is judged on, where it has one: a ratio, or the premium's mid. */
function gateNumber(gate: GateOut): { value: number; isPrice: boolean } | undefined {
  const { ratio: r, mid } = gate.values;
  if (typeof r === "number") return { value: r, isPrice: false };
  if (typeof mid === "string" || typeof mid === "number") return { value: Number(mid), isPrice: true };
  return undefined;
}

/** That value as the cell shows it: a ratio to 2 dp, a mid as a price. */
export function gateValue(gate: GateOut): string {
  const found = gateNumber(gate);
  if (!found) return "";
  return found.isPrice ? price(found.value) : ratio(found.value);
}

/** `pass 1.11`, `FIRE 1.32`, `n/a`, or `—` when it wasn't evaluated (UI-SPEC §5). */
export function gateText(gate: GateOut | undefined): string {
  const status = gate ? STATUS_TEXT[gate.status] : undefined;
  if (!gate || status === undefined) return "—";
  const value = gate.status === "n/a" ? "" : gateValue(gate);
  return value ? `${status} ${value}` : status;
}

function gateTitle(gate: GateOut): string {
  const values = Object.entries(gate.values).map(([k, v]) => `${k} ${String(v)}`);
  return [gate.status, ...values, gate.reason].filter(Boolean).join(" · ");
}

function GateCell({ gate }: { gate: GateOut | undefined }) {
  const text = gateText(gate);
  if (!gate || text === "—") return <span className="pm-label">—</span>;
  return (
    <RuleLink id={gate.rule_id}>
      <span className={gate.status === "fire" ? "pm-fire" : undefined} title={gateTitle(gate)}>
        {text}
      </span>
    </RuleLink>
  );
}

function selected(row: GateLogRowOut): ReactNode {
  const s = row.selected;
  if (!s) return <span className="pm-label">none</span>;
  const delta = typeof s.delta === "number" ? `delta ${ratio(s.delta)}` : "";
  const mid = s.mid === undefined || s.mid === null ? "" : `mid ${price(Number(s.mid))}`;
  return <Stacked top={String(s.option ?? "")} sub={[delta, mid].filter(Boolean).join(" · ")} />;
}

const STATUS_RANK: Record<string, number> = { fire: 0, pass: 1, "n/a": 2 };
// A rank's band is wider than any value a gate is judged on (a ratio, a mid in dollars).
const RANK_BAND = 1e6;

/** A gate cell's sort key: fires, then passes, then n/a, each by its value; none when the gate
 * wasn't evaluated, so it sorts last either way (UI-SPEC §5). */
export function gateSortKey(gate: GateOut | undefined): number | undefined {
  const rank = gate ? STATUS_RANK[gate.status] : undefined;
  if (gate === undefined || rank === undefined) return undefined;
  return rank * RANK_BAND + (gateNumber(gate)?.value ?? 0);
}

/** The gate log's columns, one per gate the log has, in the order it has them, each headed by
 * what the gate checks (PO, DEC-107). */
export function gateLogColumns(rows: readonly GateLogRowOut[],
                               run: RunResult): TableColumn<GateLogRowOut>[] {
  const rules = run.config.strategy.rules;
  const gates = [...new Set(rows.flatMap((r) => r.gates.map((g) => g.rule_id)))];
  const find = (row: GateLogRowOut, id: string) => row.gates.find((g) => g.rule_id === id);
  return [
    { id: "session", header: "Session", sort: (r) => r.session, cell: (r) => r.session },
    { id: "decision", header: "Decision time", sort: (r) => r.decision_time ?? undefined,
      cell: (r) => orDash(r.decision_time, timeET) },
    { id: "selected", header: "Selected",
      sort: (r) => (r.selected?.option === undefined || r.selected.option === null
        ? undefined : String(r.selected.option)),
      cell: selected },
    ...gates.map((id): TableColumn<GateLogRowOut> => ({
      id,
      header: gateName(id, rules),
      sort: (r) => gateSortKey(find(r, id)),
      cell: (r) => <GateCell gate={find(r, id)} />,
    })),
    { id: "outcome", header: "Outcome",
      sort: (r) => `${r.outcome.kind} ${ruleLabel(r.outcome.rule_id, rules)}`,
      cell: (r) => <Outcome row={r} run={run} /> },
  ];
}

/** `sold`, linked to the rule that sold; or `skipped · Event week`, the reason linked. */
function Outcome({ row, run }: { row: GateLogRowOut; run: RunResult }) {
  const { kind, rule_id: id } = row.outcome;
  if (kind !== "skipped") return <Rule id={id} run={run}>{kind}</Rule>;
  return (
    <>
      <span className="pm-skip">{kind}</span> · <Rule id={id} run={run} />
    </>
  );
}

// ---- the ledger -------------------------------------------------------------------------------

const STALE = "last valid mid carried; never filled";

function legName(leg: LegOut | null): ReactNode {
  if (!leg) return <span className="pm-label">—</span>;
  const { ric, strike, expiry } = leg.instrument;
  return <Stacked top={ric} sub={`K ${strike ?? "—"} · ${expiry ?? "—"}`} />;
}

function mark(item: LegOut | StockOut | null): ReactNode {
  if (!item) return "—";
  return item.stale
    ? <span className="pm-flag" title={STALE}>{price(item.mark)}</span>
    : price(item.mark);
}

function stock(s: StockOut | null): ReactNode {
  if (!s) return <span className="pm-label">—</span>;
  return <Stacked top={`${count(s.shares)} sh`} sub={mark(s)} />;
}

function legColumns(side: "long" | "short", tag: string): TableColumn<LedgerRowOut>[] {
  const leg = (r: LedgerRowOut) => r[side];
  return [
    { id: side, header: side === "long" ? "Long" : "Short",
      sort: (r) => leg(r)?.instrument.ric, cell: (r) => legName(leg(r)) },
    { id: `${tag}qty`, header: `${tag} qty`, num: true, sort: (r) => leg(r)?.qty,
      cell: (r) => leg(r)?.qty ?? "—" },
    { id: `${tag}mark`, header: `${tag} mark`, num: true, sort: (r) => leg(r)?.mark,
      cell: (r) => mark(leg(r)) },
    { id: `${tag}delta`, header: `${tag} delta`, num: true, sort: (r) => leg(r)?.delta ?? undefined,
      cell: (r) => orDash(leg(r)?.delta, ratio) },
  ];
}

function moneyColumn(id: string, header: string,
                     value: (r: LedgerRowOut) => number): TableColumn<LedgerRowOut> {
  return { id, header, num: true, sort: value, cell: (r) => money(value(r)) };
}

export const LEDGER_COLUMNS: readonly TableColumn<LedgerRowOut>[] = [
  { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
  ...legColumns("long", "L"),
  ...legColumns("short", "S"),
  { id: "stock", header: "Stock", sort: (r) => r.stock?.shares, cell: (r) => stock(r.stock) },
  moneyColumn("cash", "Cash", (r) => r.cash),
  moneyColumn("nav", "NAV", (r) => r.nav),
  moneyColumn("im", "IM", (r) => r.im),
  moneyColumn("mm", "MM", (r) => r.mm),
  { id: "funds", header: "Avail. funds", num: true, sort: (r) => r.available_funds,
    cell: (r) => (
      <span className={r.available_funds < 0 ? "pm-flag" : undefined}>
        {money(r.available_funds)}
      </span>
    ) },
  moneyColumn("excess", "Excess eq.", (r) => r.excess_equity),
  { id: "flags", header: "Flags", sort: (r) => r.flags.join(" ") || undefined,
    cell: (r) => <span className="pm-flag">{r.flags.join(", ")}</span> },
];

// ---- the filters UI-SPEC §5 gives each table --------------------------------------------------

/** A filter over rule IDs whose buttons say what the rule did, the rule's text on hover
 * (PO, DEC-107): the IDs stay in the data and the Rule column. */
function ruleFilter<T>(id: string, name: string, offer: (row: T) => string,
                       run: RunResult): TableFilter<T> {
  const rules = run.config.strategy.rules;
  return {
    id,
    name,
    offer: (row) => [offer(row)],
    label: (value) => ruleLabel(value, rules),
    hint: (value) => ruleHint(value, run.rule_text),
  };
}

export function blotterFilters(run: RunResult): TableFilter<BlotterRow>[] {
  return [
    ruleFilter("rule", "Trade", (r: BlotterRow) => r.rule_id, run),
    { id: "side", name: "Side", offer: (r) => [r.side] },
  ];
}

export function gateLogFilters(run: RunResult): TableFilter<GateLogRowOut>[] {
  return [
    { id: "outcome", name: "Outcome", offer: (r) => [r.outcome.kind] },
    ruleFilter("rule", "Reason", (r: GateLogRowOut) => r.outcome.rule_id, run),
  ];
}

export const LEDGER_FILTERS: readonly TableFilter<LedgerRowOut>[] = [
  { id: "flags", name: "Flags", offer: (r) => r.flags },
];
