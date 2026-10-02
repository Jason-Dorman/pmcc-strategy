// The comparison page's panels (UI-SPEC §6.1): the purpose, with its sentence on the result's main
// limit read from both runs' leg attribution (DEC-109); the NAV comparison and its values; the
// headline, one row per strategy; and the pooled universe.
import { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";

import { KeyValue } from "../../components/cells";
import { Chart } from "../../components/charts/Chart";
import { navCompareOption, navGap, navRows, type NavRow } from "../../components/charts/navCompare";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty, Note } from "../../components/Note";
import { money, moneySigned } from "../../format/money";
import { meanCI, orDash, pct, ratio } from "../../format/number";
import { timeET } from "../../format/time";
import type { Palette } from "../../theme/echarts";
import type { Pooled as PooledFile } from "../../types/generated/pooled";
import type { RunResult } from "../../types/generated/run_result";
import { headlineRow, legSplit, longRode, type HeadlineRow, type LegSplit } from "./figures";

// ---- purpose ----------------------------------------------------------------------------------

function legs(splits: readonly LegSplit[], part: (s: LegSplit) => number): string {
  return splits.map((s) => `${moneySigned(part(s))} for ${s.name}`).join(" and ");
}

/** The sentence on the result's main limit, its figures read from the runs (PO, DEC-109). It
 * says the long call riding a rising stock made the result only where every run shows it. */
export function LimitSentence({ splits }: { splits: readonly LegSplit[] }) {
  const long = legs(splits, (s) => s.long);
  const shorts = legs(splits, (s) => s.shorts);
  if (splits.length > 0 && splits.every(longRode)) {
    return (
      <p>
        <b>Over this window the result is mostly the long call riding a rising stock:</b> the long
        leg made {long}, more than the whole P&amp;L, while the shorts netted {shorts}.
        Each strategy page&apos;s leg attribution has the split.
      </p>
    );
  }
  return (
    <p>
      Over this window the long leg made {long}, and the shorts netted {shorts}. Each strategy
      page&apos;s leg attribution has the split.
    </p>
  );
}

export function Purpose({ symbol, runs }: { symbol: string; runs: readonly RunResult[] | null }) {
  const splits = (runs ?? []).flatMap((r) => legSplit(r) ?? []);
  return (
    <Note>
      <p>
        A <b>poor man&apos;s covered call</b> (PMCC) holds a deep in-the-money call with months to
        run as a stand-in for the stock, and sells a short-dated out-of-the-money call against it
        each week for income. The <b>baseline</b> picks both legs by fixed deltas; the{" "}
        <b>quant</b> strategy shares its engine, sizing and exits, but buys the long with the least
        extrinsic value per delta, sells the short at or beyond the expected move, and skips weeks
        its gates judge poorly paid or risky. This page sets the two side by side on {symbol}: the
        NAV chart and headline for the result, the pooled figures over every symbol run, and the
        ablations, each switching off one quant layer to show what it added or cost
        (<Link to="/rules">the rules</Link> define each).
      </p>
      {splits.length > 0 && <LimitSentence splits={splits} />}
    </Note>
  );
}

// ---- NAV comparison ---------------------------------------------------------------------------

function navColumns(quant: string, baseline: string): TableColumn<NavRow>[] {
  return [
    { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
    { id: "quant", header: quant, num: true, sort: (r) => r.quant ?? undefined,
      cell: (r) => orDash(r.quant, money) },
    { id: "baseline", header: baseline, num: true, sort: (r) => r.baseline ?? undefined,
      cell: (r) => orDash(r.baseline, money) },
    { id: "gap", header: `${quant} − ${baseline}`, num: true, sort: (r) => navGap(r) ?? undefined,
      cell: (r) => orDash(navGap(r), moneySigned) },
  ];
}

export function NavCompare({ quant, baseline }: { quant: RunResult; baseline: RunResult }) {
  const names = useMemo(() => ({ quant: quant.config.strategy.name,
                                 baseline: baseline.config.strategy.name }), [quant, baseline]);
  const rows = useMemo(() => navRows(quant.ledger ?? [], baseline.ledger ?? []),
                       [quant, baseline]);
  const columns = useMemo(() => navColumns(names.quant, names.baseline), [names]);
  const build = useCallback((p: Palette) => navCompareOption(p, rows, names), [rows, names]);
  if (!quant.ledger || !baseline.ledger) {
    return <Empty>A run&apos;s file doesn&apos;t keep its ledger.</Empty>;
  }
  return (
    <>
      <Chart build={build} hero label={`${names.quant} and ${names.baseline} NAV on every bar`} />
      <Details summary="Values at every bar" table>
        <DataTable label="NAV by bar" rows={rows} columns={columns} rowId={(r) => r.time}
                   virtual />
      </Details>
    </>
  );
}

// ---- headline ---------------------------------------------------------------------------------

const HEADLINE_COLUMNS: readonly TableColumn<HeadlineRow>[] = [
  { id: "strategy", header: "Strategy", sort: (r) => r.name,
    cell: (r) => <span className="pm-label">{r.name}</span> },
  { id: "pnl", header: "P&L", num: true, sort: (r) => r.pnl ?? undefined,
    cell: (r) => orDash(r.pnl, moneySigned) },
  { id: "roc", header: "Return on capital", num: true, sort: (r) => r.returnOnCapital ?? undefined,
    cell: (r) => orDash(r.returnOnCapital, pct) },
  { id: "drawdown", header: "Max drawdown", num: true, sort: (r) => r.maxDrawdown ?? undefined,
    cell: (r) => (r.maxDrawdown === null ? "—"
      : `${money(r.maxDrawdown)} (${orDash(r.maxDrawdownPct, pct)})`) },
  { id: "payoff", header: "Payoff", num: true, sort: (r) => r.payoff ?? undefined,
    cell: (r) => orDash(r.payoff, ratio) },
  { id: "weekly", header: "Mean weekly return (95% CI)", num: true,
    sort: (r) => r.weekly?.mean, cell: (r) => orDash(r.weekly, meanCI) },
];

export function Headline({ runs }: { runs: readonly RunResult[] }) {
  const rows = useMemo(() => runs.map(headlineRow), [runs]);
  return <DataTable label="Headline" rows={rows} columns={HEADLINE_COLUMNS} rowId={(r) => r.id} />;
}

// ---- pooled universe --------------------------------------------------------------------------

export function Pooled({ pooled, name, quantId }: {
  pooled: PooledFile;
  /** A strategy's name, from its ID. */
  name: (strategyId: string) => string;
  /** The strategy listed first. */
  quantId: string;
}) {
  const strategies = [...pooled.strategies].sort(
    (a, b) => Number(b.strategy_id === quantId) - Number(a.strategy_id === quantId));
  const beat = pooled.quant_beat_baseline;
  const symbols = pooled.symbols.length;
  return (
    <KeyValue
      label="Pooled universe"
      rows={[
        ["Symbols pooled", pooled.symbols.join(", ") || "none"],
        ...strategies.flatMap((s) => [
          [`${name(s.strategy_id)}, total P&L`, moneySigned(s.total_pnl)],
          [`${name(s.strategy_id)}, mean weekly return (95% CI)`,
           orDash(s.weekly_return, (ci) => `${meanCI(ci)}, ${ci.weeks} weeks`)],
        ] as const),
        ["Symbols where quant beat the baseline",
         `${beat.join(", ") || "none"} (${beat.length} of ${symbols})`],
      ]}
    />
  );
}
