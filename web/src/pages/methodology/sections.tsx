// The methodology page's data panels (UI-SPEC §6.4): the two mid-vs-print scatters with their
// fits and the pooled fit beside them (`fill_check.json`, `universe/pooled_fill_check.json`;
// DEC-64), and entry timing with its dispersion and fragility (PO, DEC-67). The stated
// assumptions panel was dropped (PO, DEC-121).
import { useCallback, useMemo } from "react";

import { KeyValue } from "../../components/cells";
import { Chart } from "../../components/charts/Chart";
import { scatterOption } from "../../components/charts/scatter";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty } from "../../components/Note";
import { RobustnessTable } from "../../components/RobustnessTable";
import { money, price } from "../../format/money";
import { count, meanCI, orDash, pct } from "../../format/number";
import type { Palette } from "../../theme/echarts";
import type { Fit, FillGroup } from "../../types/generated/fill_check";
import type { PooledFillGroup } from "../../types/generated/pooled_fill_check";
import type { Robustness } from "../../types/generated/robustness";
import { fillPairs, gapOfSpread, timing, type FillPair } from "./figures";

// ---- mid vs print ---------------------------------------------------------------------

const PAIR_COLUMNS: readonly TableColumn<FillPair>[] = [
  { id: "mid", header: "Mid", num: true, sort: (r) => r.mid, cell: (r) => price(r.mid) },
  { id: "trade", header: "Print", num: true, sort: (r) => r.trade, cell: (r) => price(r.trade) },
  { id: "gap", header: "Print − mid", num: true, sort: (r) => r.trade - r.mid,
    cell: (r) => price(r.trade - r.mid) },
  { id: "spread", header: "Spread", num: true, sort: (r) => r.spread,
    cell: (r) => price(r.spread) },
  { id: "share", header: "|Print − mid| ÷ spread", num: true,
    sort: (r) => gapOfSpread(r) ?? undefined, cell: (r) => orDash(gapOfSpread(r), pct) },
];

type FitRow = readonly [label: string, show: (fit: Fit) => string];

// A fit's measures (DEC-64): the line, its R² and N, and the median gap.
const FIT_ROWS: readonly FitRow[] = [
  ["Slope", (f) => f.slope.toFixed(4)],
  ["Intercept", (f) => price(f.intercept)],
  ["R²", (f) => orDash(f.r2, (r) => r.toFixed(4))],
  ["N (pairs)", (f) => count(f.n)],
  ["Median |print − mid|, of the spread", (f) => orDash(f.median_abs_gap_pct_spread, pct)],
  ["Locked quotes, left out of the median", (f) => count(f.locked)],
];

/** A fit's measures, the symbol's beside the pooled universe's. */
export function FitTable({ label, symbol, fit, pooled }: {
  label: string;
  symbol: string;
  fit: Fit | null;
  pooled: Fit | null;
}) {
  return (
    <table className="pm-table pm-table-kv" aria-label={label}>
      <thead>
        <tr>
          <th>Print ≈ slope × mid + intercept</th>
          <th className="pm-num">{symbol}</th>
          <th className="pm-num">Pooled</th>
        </tr>
      </thead>
      <tbody>
        {FIT_ROWS.map(([name, show]) => (
          <tr key={name}>
            <td>{name}</td>
            <td className="pm-num">{fit ? show(fit) : "—"}</td>
            <td className="pm-num">{pooled ? show(pooled) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function MidVsPrint({ symbol, group, pooled, label }: {
  symbol: string;
  group: FillGroup;
  /** The same group's fit over every symbol, where the universe has one. */
  pooled: PooledFillGroup | undefined;
  label: string;
}) {
  const { points, fit } = group;
  const build = useCallback((p: Palette) => scatterOption(p, points, fit), [points, fit]);
  const rows = useMemo(() => fillPairs(points), [points]);
  if (rows.length === 0) return <Empty>No bar had both a print and a valid quote.</Empty>;
  return (
    <>
      <Chart build={build} label={`${label}: print against mid, ${count(rows.length)} pairs`} />
      <FitTable label={`${label} fit`} symbol={symbol} fit={fit} pooled={pooled?.fit ?? null} />
      <Details summary="Values for every pair" table lazy>
        <DataTable label={`${label} pairs`} rows={rows} columns={PAIR_COLUMNS}
                   rowId={(r) => String(r.i)} virtual />
      </Details>
    </>
  );
}

/** The scatter's caption: what a point is, and the caveat on its age. */
export function scatterCaption(what: string) {
  return (
    <>
      Each point is one {what}&apos;s session bar with a trade: x its mid at the bar&apos;s end, y
      the bar&apos;s last trade (TRDPRC_1). The solid line is the least-squares fit, the dashed one
      y = x. A gap of 50% of the spread is a print at the bid or the ask. A print can be up to an
      hour older than the end-of-bar quote it is set against.
    </>
  );
}

// ---- entry timing --------------------------------------------------------------------------

export function TimingPanel({ robustness }: { robustness: Robustness }) {
  const t = timing(robustness.timing);
  const d = robustness.timing_dispersion;
  if (!t) return <Empty>No timing runs.</Empty>;
  const ci = t.reference.weekly_return;
  const verdict = !ci || !t.means ? "—"
    : t.outside.length > 0
      ? <span className="pm-flag">Fragile: {t.outside.map((r) => r.label).join("; ")} outside
          the baseline&apos;s CI</span>
      : `Not fragile: every fixed bar inside the baseline's CI`;
  return (
    <div className="pm-stack">
      <RobustnessTable label="Entry timing" rows={robustness.timing} against="baseline" />
      <KeyValue
        label="Timing dispersion"
        rows={[
          ["Fixed-bar runs", count(t.fixed.length)],
          ["P&L range over them", orDash(d?.range, money)],
          ["Sample standard deviation of P&L", orDash(d?.std, money)],
          ["Mean weekly return over them",
           t.means ? `${pct(t.means.low)} to ${pct(t.means.high)}` : "—"],
          ["The baseline's mean weekly return (95% CI)", orDash(ci, meanCI)],
          ["Fragility", verdict],
        ]}
      />
    </div>
  );
}
