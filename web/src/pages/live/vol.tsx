// The live page's volatility panels (UI-SPEC §6 › Live; L4-02; PO, LD-33): ATM IV about 30 days
// out against RV20 by session, and the coming week's smile at the last close, each chart's values
// in a table under it. From `live/vol.jsonl` and `live/smile.json`, the volatility workflow's.
import { useCallback } from "react";

import { Chart } from "../../components/charts/Chart";
import { ivRvOption, smileOption, VOL_SERIES } from "../../components/charts/vol";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty } from "../../components/Note";
import { money } from "../../format/money";
import { iv, orDash, ratio } from "../../format/number";
import type { Palette } from "../../theme/echarts";
import type { Live, SmileOut, SmilePointOut, VolPointOut } from "../../types/generated/live";

const MINUS = "−";

/** IV less RV20 in points, `+4.2`; none where either is missing. */
export function gap(point: VolPointOut): number | null {
  return point.atm_iv === null || point.rv20 === null ? null : point.atm_iv - point.rv20;
}

function points(value: number): string {
  const text = Math.abs(value * 100).toFixed(1);
  return `${value < 0 && Number(text) !== 0 ? MINUS : "+"}${text}`;
}

const VOL_COLUMNS: readonly TableColumn<VolPointOut>[] = [
  { id: "session", header: "Session", sort: (r) => r.session, cell: (r) => r.session },
  { id: "iv", header: "ATM IV", num: true, sort: (r) => r.atm_iv ?? undefined,
    cell: (r) => orDash(r.atm_iv, iv) },
  { id: "rv", header: "RV20", num: true, sort: (r) => r.rv20 ?? undefined,
    cell: (r) => orDash(r.rv20, iv) },
  { id: "gap", header: "IV − RV20 (pts)", num: true, sort: (r) => gap(r) ?? undefined,
    cell: (r) => orDash(gap(r), points) },
  { id: "close", header: "Close", num: true, sort: (r) => r.close, cell: (r) => money(r.close) },
  { id: "expiry", header: "Expiry", sort: (r) => r.expiry, cell: (r) => r.expiry },
  { id: "strike", header: "ATM strike", num: true, sort: (r) => r.strike ?? undefined,
    cell: (r) => orDash(r.strike, money) },
];

/** ATM IV about 30 days out against RV20, a point a session. */
export function IvRv({ live }: { live: Live }) {
  const build = useCallback((p: Palette) => ivRvOption(p, live.vol), [live.vol]);
  if (live.vol.length === 0) return <Empty>No volatility pulled yet.</Empty>;
  const [ivName, rvName] = VOL_SERIES;
  return (
    <>
      <Chart build={build} label={`${live.symbol}'s ${ivName} and ${rvName} at each close`} />
      <Details summary="The values" table>
        <DataTable label="Volatility by session" rows={[...live.vol].reverse()}
                   columns={VOL_COLUMNS} rowId={(r) => r.session} />
      </Details>
    </>
  );
}

const SMILE_COLUMNS: readonly TableColumn<SmilePointOut>[] = [
  { id: "strike", header: "Strike", num: true, sort: (r) => r.strike,
    cell: (r) => money(r.strike) },
  { id: "right", header: "Right", sort: (r) => r.right, cell: (r) => r.right },
  { id: "iv", header: "IV", num: true, sort: (r) => r.iv, cell: (r) => iv(r.iv) },
  { id: "delta", header: "Delta", num: true, sort: (r) => r.delta, cell: (r) => ratio(r.delta) },
];

function smileLabel(smile: SmileOut): string {
  return `IV by strike for the ${smile.expiry} expiry at the ${smile.session} close`;
}

/** The coming week's out-of-the-money IVs at the last close. */
export function Smile({ live }: { live: Live }) {
  const smile = live.smile;
  const build = useCallback((p: Palette) => (smile ? smileOption(p, smile) : {}), [smile]);
  if (smile === null || smile.points.length === 0) {
    return <Empty>No smile pulled yet.</Empty>;
  }
  return (
    <>
      <Chart build={build} label={smileLabel(smile)} />
      <Details summary="The values" table>
        <DataTable label="The smile by strike" rows={smile.points} columns={SMILE_COLUMNS}
                   rowId={(r) => `${r.right}-${r.strike}`} />
      </Details>
    </>
  );
}
