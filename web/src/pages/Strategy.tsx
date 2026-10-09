// The strategy page (UI-SPEC §6.2): one component tree for both strategies. The optional sections
// come from the run's `report.sections` (DEC-54); the page never checks a strategy's name, and
// the panel grid renumbers whatever it shows.
import { useCallback, useMemo, type ReactNode } from "react";
import { useParams } from "react-router-dom";

import { STRATEGY_PAGES } from "../app/pages";
import { accountOption } from "../components/charts/account";
import { Chart } from "../components/charts/Chart";
import { DataTable } from "../components/DataTable";
import { Empty } from "../components/Note";
import { pending, PageFrame } from "../components/PageFrame";
import type { PanelSpec } from "../components/PanelGrid";
import { useRun } from "../data/useRun";
import { count } from "../format/number";
import type { Palette } from "../theme/echarts";
import { W_FULL, W_HALF, type PanelWidth } from "../theme/tokens";
import type { RunResult, Section } from "../types/generated/run_result";
import { Cycles } from "./strategy/Cycles";
import { READOUT_HINTS, readouts } from "./strategy/figures";
import { Greeks } from "./strategy/Greeks";
import { Legs } from "./strategy/Legs";
import { PositionGreeks } from "./strategy/PositionGreeks";
import { RegT } from "./strategy/RegT";
import {
  blotterColumns,
  blotterFilters,
  gateLogFilters,
  gateLogColumns,
  LEDGER_COLUMNS,
  LEDGER_FILTERS,
} from "./strategy/tables";
import { whenLoaded } from "./placeholder";

const NO_FILE = <Empty>This run&apos;s file doesn&apos;t keep it.</Empty>;

function Account({ run }: { run: RunResult }) {
  const ledger = run.ledger;
  const build = useCallback((p: Palette) => accountOption(p, ledger ?? []), [ledger]);
  if (!ledger) return NO_FILE;
  return <Chart build={build} hero label="NAV, initial and maintenance margin, available funds" />;
}

function Blotter({ run }: { run: RunResult }) {
  const filters = useMemo(() => blotterFilters(run), [run]);
  const columns = useMemo(() => blotterColumns(run), [run]);
  if (!run.blotter) return NO_FILE;
  return <DataTable label="Blotter" rows={run.blotter} columns={columns}
                    filters={filters} rowId={(r, i) => `${r.time}/${i}`} virtual />;
}

function GateLog({ run }: { run: RunResult }) {
  const rows = run.gate_log;
  const columns = useMemo(() => gateLogColumns(rows ?? [], run), [rows, run]);
  const filters = useMemo(() => gateLogFilters(run), [run]);
  if (!rows) return NO_FILE;
  return <DataTable label="Gate log" rows={rows} columns={columns}
                    filters={filters} rowId={(r) => r.session} />;
}

function Ledger({ run }: { run: RunResult }) {
  if (!run.ledger) return NO_FILE;
  return <DataTable label="Ledger" rows={run.ledger} columns={LEDGER_COLUMNS}
                    filters={LEDGER_FILTERS} rowId={(r) => r.time} virtual />;
}

function counted(rows: readonly unknown[] | null, what: string): string | undefined {
  return rows ? `${count(rows.length)} ${what}` : undefined;
}

interface PanelDef {
  key: string;
  name: string;
  width: PanelWidth;
  /** Shown only when the run's `report.sections` lists it. */
  section?: Section;
  body: (run: RunResult) => ReactNode;
  /** The header's note; none when the run's file doesn't keep what it counts. */
  note?: (run: RunResult) => string | undefined;
  caption?: ReactNode;
}

const SECTIONS: readonly PanelDef[] = [
  { key: "account", name: "Account", width: W_FULL, body: (r) => <Account run={r} />,
    note: (r) => counted(r.ledger, "hourly bars"),
    caption: <>NAV (solid) with initial margin (dashed) and maintenance margin (dotted); below,
      available funds, shaded where they fall under zero. Hover for a bar&apos;s account; the
      ledger below lists every bar.</> },
  { key: "regt", name: "Reg T", width: W_HALF, body: (r) => <RegT run={r} />,
    note: () => "the account at the last bar",
    caption: <>Available funds are NAV less initial margin; excess equity is NAV less
      maintenance margin.</> },
  { key: "cycles", name: "Cycle statistics", width: W_HALF, body: (r) => <Cycles run={r} />,
    note: () => "one cycle is one week",
    caption: <>A win or loss is a week&apos;s change in NAV, both legs included. Skips and
      exits link to their rules.</> },
  { key: "legs", name: "Leg attribution", width: W_FULL, body: (r) => <Legs run={r} />,
    note: () => "net of fees",
    caption: <>Long-leg P&amp;L + net short premium − a short open at the end + the stock after
      a missed assignment = P&amp;L. The chart shows both legs so far at each session&apos;s
      close.</> },
  { key: "blotter", name: "Blotter", width: W_FULL, body: (r) => <Blotter run={r} />,
    note: (r) => counted(r.blotter, "trades") },
  { key: "gates", name: "Gate log", width: W_FULL, section: "gate_log",
    body: (r) => <GateLog run={r} />, note: (r) => counted(r.gate_log, "weeks"),
    caption: <>Each gate shows its status and the value it was judged on; hover for every
      value. A gate not evaluated shows —.</> },
  { key: "ledger", name: "Ledger", width: W_FULL, body: (r) => <Ledger run={r} />,
    note: (r) => counted(r.ledger, "bars"),
    caption: <>A mark in the flag colour is stale: the last valid mid, carried, never
      filled.</> },
  { key: "position", name: "Position Greeks", width: W_FULL, section: "position_greeks",
    body: (r) => <PositionGreeks run={r} />, note: () => "the short signed as held",
    caption: <>The table averages each Greek over the bars ending with both legs held; net is
      long plus short (and, for delta, any assigned stock). The textbook PMCC is long delta,
      short gamma, long theta and long vega. The chart shows the net at every bar: where no short
      is open (a skipped week, or after the short is closed) it is the long alone. Delta in
      shares, gamma in shares per $1 move, theta in $ a calendar day, vega in $ a vol point.</> },
  { key: "greeks", name: "Greek attribution", width: W_FULL, section: "greek_attribution",
    body: (r) => <Greeks run={r} />,
    note: () => "delta, gamma, theta and vega terms, per bar",
    caption: <>Each held bar is priced from the previous bar&apos;s Greeks; the residual is the
      rest. A bar with a stale mark, no IV or no fill is residual whole.</> },
];

function noteOf(run: RunResult | undefined, s: PanelDef): { note?: string } {
  const note = run && s.note ? s.note(run) : undefined;
  return note === undefined ? {} : { note };
}

function panels(run: RunResult | undefined, body: (render: (r: RunResult) => ReactNode) => ReactNode):
    PanelSpec[] {
  const sections: readonly Section[] = run?.config.strategy.report.sections ?? [];
  return SECTIONS.filter((s) => s.section === undefined || sections.includes(s.section)).map(
    (s) => ({
      key: s.key,
      name: s.name,
      width: s.width,
      numbered: true,
      body: body(s.body),
      ...noteOf(run, s),
      ...(s.caption ? { caption: s.caption } : {}),
    }),
  );
}

export function Strategy({ page }: { page: keyof typeof STRATEGY_PAGES }) {
  const { symbol = "" } = useParams();
  const state = useRun(symbol, STRATEGY_PAGES[page]);
  const run = state.kind === "ready" ? state.value : undefined;
  const body = (render: (r: RunResult) => ReactNode) => whenLoaded(state, render);
  return (
    <PageFrame
      readouts={run ? readouts(run) : pending(READOUT_HINTS.map(([l, h]) => [l, h]))}
      panels={panels(run, body)}
    />
  );
}
