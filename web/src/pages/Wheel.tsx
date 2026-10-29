// The wheel page (UI-SPEC §6; PO, WD-22): what the wheel did, bar by bar. Readouts, then the NAV
// chart, the portfolio at a chosen bar beside the cycle statistics, the blotter, the gate log and
// the ledger. The chosen bar is the URL's `?bar=` (UI-SPEC §7: the URL is the state), so a link
// opens the same portfolio; with none, the last bar. A click on the chart or a ledger time
// chooses it, as do the portfolio panel's controls.
import { useCallback, useMemo, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { WHEEL_RUN } from "../app/pages";
import { Chart } from "../components/charts/Chart";
import { wheelNavOption } from "../components/charts/wheelNav";
import { DataTable } from "../components/DataTable";
import { pending, PageFrame } from "../components/PageFrame";
import { useWheel } from "../data/useRun";
import { count } from "../format/number";
import type { Palette } from "../theme/echarts";
import { W_FULL, W_HERO, W_SIDECAR } from "../theme/tokens";
import type { WheelResult } from "../types/generated/wheel_result";
import { panel, whenLoaded } from "./placeholder";
import { Cycles } from "./wheel/Cycles";
import { READOUT_HINTS, readouts } from "./wheel/figures";
import { Portfolio } from "./wheel/Portfolio";
import {
  blotterColumns,
  blotterFilters,
  gateLogColumns,
  gateLogFilters,
  LEDGER_FILTERS,
  ledgerColumns,
} from "./wheel/tables";

const BAR = "bar";

/** The bar the URL names, as a ledger index; the last bar when it names none or one not there. */
function useBar(ledger: readonly { time: string }[]) {
  const [params, setParams] = useSearchParams();
  const named = params.get(BAR);
  const found = named === null ? -1 : ledger.findIndex((r) => r.time === named);
  const index = found >= 0 ? found : ledger.length - 1;
  const choose = useCallback((time: string) => {
    setParams((p) => {
      const next = new URLSearchParams(p);
      next.set(BAR, time);
      return next;
    }, { replace: true });
  }, [setParams]);
  return { index, choose };
}

/** A ledger index chosen: its bar's time into the URL. */
function usePick(ledger: readonly { time: string }[], choose: (time: string) => void) {
  return useCallback((i: number) => {
    const row = ledger[i];
    if (row) choose(row.time);
  }, [ledger, choose]);
}

function NavChart({ run }: { run: WheelResult }) {
  const ledger = run.ledger;
  const { index, choose } = useBar(ledger);
  const pick = usePick(ledger, choose);
  const build = useCallback((p: Palette) => wheelNavOption(p, ledger, index), [ledger, index]);
  return <Chart build={build} hero onPick={pick}
                label="NAV, with the stock, the held strike and the cost basis" />;
}

function PortfolioPanel({ run }: { run: WheelResult }) {
  const { index, choose } = useBar(run.ledger);
  return <Portfolio run={run} index={index} onIndex={usePick(run.ledger, choose)} />;
}

function Blotter({ run }: { run: WheelResult }) {
  const columns = useMemo(() => blotterColumns(run), [run]);
  const filters = useMemo(() => blotterFilters(run), [run]);
  return <DataTable label="Blotter" rows={run.blotter} columns={columns} filters={filters}
                    rowId={(r, i) => `${r.time}/${String(i)}`} virtual />;
}

function GateLog({ run }: { run: WheelResult }) {
  const columns = useMemo(() => gateLogColumns(run), [run]);
  const filters = useMemo(() => gateLogFilters(run), [run]);
  return <DataTable label="Gate log" rows={run.gate_log} columns={columns} filters={filters}
                    rowId={(r) => r.session} />;
}

function Ledger({ run }: { run: WheelResult }) {
  const { index, choose } = useBar(run.ledger);
  const columns = useMemo(() => ledgerColumns(choose), [choose]);
  return <DataTable label="Ledger" rows={run.ledger} columns={columns} filters={LEDGER_FILTERS}
                    rowId={(r) => r.time} virtual selected={run.ledger[index]?.time} />;
}

export function Wheel() {
  const { symbol = "" } = useParams();
  const state = useWheel(symbol, WHEEL_RUN);
  const run = state.kind === "ready" ? state.value : undefined;
  const body = (Part: (props: { run: WheelResult }) => ReactNode) =>
    whenLoaded(state, (r) => <Part run={r} />);
  const bars = run ? `${count(run.ledger.length)} hourly bars` : undefined;
  return (
    <PageFrame
      readouts={run ? readouts(run) : pending(READOUT_HINTS.map(([l, h]) => [l, h]))}
      panels={[
        { ...panel("nav", "NAV", W_FULL, body(NavChart)), ...(bars ? { note: bars } : {}),
          caption: <>NAV above, shaded where the wheel holds shares; below, the stock&apos;s last
            trade with the strike of the option held (dashed) and the shares&apos; cost basis
            (dotted). The amber rule is the bar the portfolio shows: click the chart to move
            it. Hover for a bar&apos;s book.</> },
        { ...panel("portfolio", "Portfolio at a bar", W_HERO, body(PortfolioPanel)),
          note: "click the chart or a ledger time",
          caption: <>NAV = cash + shares at their mark − each short option&apos;s mark × 100. A mark in the flag colour is
            stale: the last valid mid, carried, never filled. The URL keeps the bar, so a link
            opens this portfolio.</> },
        { ...panel("cycles", "Cycle statistics", W_SIDECAR, body(Cycles)),
          note: "a cycle: assigned, then called away" },
        { ...panel("blotter", "Blotter", W_FULL, body(Blotter)),
          ...(run ? { note: `${count(run.blotter.length)} trades` } : {}),
          caption: <>Trade P&amp;L is on the row that closes a position: an option&apos;s credit
            when it expires or is assigned, the shares&apos; sale less their purchase when they
            are called away. The rows sum to the realized P&amp;L. Each rule links to its
            row on the review page.</> },
        { ...panel("gates", "Gate log", W_FULL, body(GateLog)),
          ...(run ? { note: `${count(run.gate_log.length)} weeks` } : {}),
          caption: <>Each week&apos;s sale: the option picked, its delta against the target and
            its spread, and the outcome, or the rule that stopped it.</> },
        { ...panel("ledger", "Ledger", W_FULL, body(Ledger)),
          ...(run ? { note: `${count(run.ledger.length)} bars` } : {}),
          caption: <>One row per bar. Click a time to show that bar&apos;s portfolio above. A mark
            in the flag colour is stale.</> },
      ]}
    />
  );
}
