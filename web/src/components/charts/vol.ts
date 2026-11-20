// The live page's volatility (UI-SPEC §6 › Live; L4-02; PO, LD-33). NVDA's ATM implied vol about
// 30 days out against its 20-day realized vol, a point a session, the gap between them shaded:
// the wheel sells premium, which pays when implied vol runs above what the stock then realizes.
// And the coming week's skew at the last close: each out-of-the-money strike's IV, the close a
// line, the open order's strike dashed (PO, LD-43), the expected move a band (PO, LD-41).
import { money } from "../../format/money";
import { iv, orDash, ratio } from "../../format/number";
import {
  bandSeries,
  baseOption,
  lineSeries,
  LINE,
  plotGrid,
  SINGLE_GRID,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import { SIZE_MARK } from "../../theme/tokens";
import type { SmileOut, VolPointOut } from "../../types/generated/live";
import { sessionAxis, shortDate, xAxis } from "./axis";
import { pointIndex, tipHtml, type TipRow } from "./tooltip";

export const VOL_SERIES = ["ATM IV, ~30 days", "RV20"] as const;
const GAP = { floor: "IV − RV20 floor", band: "IV − RV20 gap", stack: "iv-rv-gap" };
const MINUS = "−";

/** The band between IV and RV20: its floor, the lower of the two, and its height. A hole where
 * either is missing (UI-SPEC §4 rule 6). */
export function gapBand(points: readonly VolPointOut[]) {
  const both = points.map((p) => (p.atm_iv === null || p.rv20 === null ? null
    : [p.atm_iv, p.rv20] as const));
  return {
    floor: both.map((b) => (b === null ? null : Math.min(...b))),
    height: both.map((b) => (b === null ? null : Math.abs(b[0] - b[1]))),
  };
}

/** A gap between two vols in points: `+5.0 pts`. */
function volPoints(difference: number): string {
  const text = Math.abs(difference * 100).toFixed(1);
  return `${difference < 0 && Number(text) !== 0 ? MINUS : "+"}${text} pts`;
}

// Room above the highest point for the legend, which sits inside the plot, top left; the top
// rounded up to a whole 5%, so it is a tick of its own.
const HEADROOM = 0.25;
const TOP_STEP = 0.05;

/** The value axis's top: the data's, plus `HEADROOM` of its range, up to a whole `TOP_STEP`. */
export function withHeadroom(extent: { min: number; max: number }): number {
  const top = extent.max + (extent.max - extent.min) * HEADROOM;
  return Math.ceil(top / TOP_STEP - 1e-9) * TOP_STEP;
}

/** A vol tick: `50%`. */
function volTick(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function volTip(p: Palette, point: VolPointOut): string {
  const [ivName, rvName] = VOL_SERIES;
  const rows: TipRow[] = [
    [ivName, orDash(point.atm_iv, iv), p["iv-line"]],
    [rvName, orDash(point.rv20, iv), p["rv-line"]],
  ];
  if (point.atm_iv !== null && point.rv20 !== null) {
    rows.push(["IV − RV20", volPoints(point.atm_iv - point.rv20)]);
  }
  rows.push(point.strike === null
    ? ["ATM", "no strike had both sides quoted"]
    : ["ATM", `${shortDate(point.expiry)} expiry, ${money(point.strike)} strike`]);
  return tipHtml(`${point.session} close`, rows);
}

export function ivRvOption(p: Palette, points: readonly VolPointOut[]) {
  const base = baseOption(p);
  const axis = sessionAxis(points.map((pt) => pt.session));
  const [ivName, rvName] = VOL_SERIES;
  const band = gapBand(points);
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: xAxis(p, axis),
    yAxis: valueAxis(p, { max: withHeadroom,
                         axisLabel: { ...valueAxis(p).axisLabel, formatter: volTick } }),
    legend: { ...base.legend, data: [...VOL_SERIES] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const point = points[pointIndex(params)];
        return point ? volTip(p, point) : "";
      },
    },
    series: [
      ...bandSeries(GAP, band.floor, band.height, p["vol-gap-shade"]),
      lineSeries(ivName, points.map((pt) => pt.atm_iv), p["iv-line"], LINE.series),
      lineSeries(rvName, points.map((pt) => pt.rv20), p["rv-line"], LINE.series),
    ],
  };
}

/** The open order's option, when it expires on the skew's date: the trade the strategy has on
 * (PO, LD-43). */
export interface ChartOrder {
  strike: number;
  right: "put" | "call";
}

/** The close, a solid reference, and the open order's strike, dashed (UI-SPEC §4 rule 5). */
function smileMarks(p: Palette, smile: SmileOut, order: ChartOrder | null) {
  const mark = (x: number, color: string, type: "solid" | "dashed", text: string) => ({
    xAxis: x,
    lineStyle: { color, width: LINE.ruler, type },
    label: { formatter: text, position: "insideStartTop", color: p["text-muted"],
             fontFamily: p.fontMono },
  });
  const data = [mark(smile.close, p["spot-line"], "solid", "Close")];
  if (order !== null) data.push(mark(order.strike, p["strike-line"], "dashed", "Order"));
  return { silent: true, symbol: "none", data };
}

/** Where the order's strike sits against the close: its signed share of the close (above is
 * positive), and whether that puts the option in the money. */
function placed(smile: SmileOut, order: ChartOrder, low: number, high: number) {
  const inMoney = order.right === "put" ? order.strike > smile.close : order.strike < smile.close;
  return { ...order, distance: (order.strike - smile.close) / smile.close, inMoney,
           inside: order.strike >= low && order.strike <= high };
}

/** The market's expected move to expiry (PO, LD-41): the ATM straddle's price either side of
 * the close, as a share of the close, and where the open order's strike sits against it (PO,
 * LD-43). None without a straddle. */
export function expectedMove(smile: SmileOut, order: ChartOrder | null = null) {
  const s = smile.straddle;
  if (s === null) return null;
  const low = smile.close - s.price;
  const high = smile.close + s.price;
  return { move: s.price, share: s.price / smile.close, low, high, strike: s.strike,
           order: order === null ? null : placed(smile, order, low, high) };
}

/** The expected move, a neutral band across the strikes it spans (`--move-shade`). */
function moveBand(p: Palette, smile: SmileOut) {
  const move = expectedMove(smile);
  if (move === null) return undefined;
  return {
    silent: true,
    itemStyle: { color: p["move-shade"] },
    label: { formatter: "Expected move", position: "insideTop", color: p["text-muted"],
             fontFamily: p.fontMono },
    data: [[{ xAxis: move.low }, { xAxis: move.high }]],
  };
}

export function smileOption(p: Palette, smile: SmileOut, order: ChartOrder | null = null) {
  const base = baseOption(p);
  const name = "IV at the close";
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: valueAxis(p, { axisLabel: { ...valueAxis(p).axisLabel,
                                       formatter: (v: number) => `$${v}` } }),
    yAxis: valueAxis(p, { max: withHeadroom,
                         axisLabel: { ...valueAxis(p).axisLabel, formatter: volTick } }),
    legend: { ...base.legend, data: [name] },
    tooltip: {
      ...base.tooltip,
      trigger: "item",
      axisPointer: { type: "none" },
      formatter: (params: unknown) => {
        const point = smile.points[pointIndex(params)];
        if (!point) return "";
        const right = point.right === "put" ? "Put" : "Call";
        return tipHtml(`${right} ${money(point.strike)}`, [
          ["IV", iv(point.iv), p["iv-line"]],
          ["Delta", ratio(point.delta)],
        ]);
      },
    },
    series: [
      {
        ...lineSeries(name, [], p["iv-line"], LINE.series),
        data: smile.points.map((pt) => [pt.strike, pt.iv]),
        showSymbol: true,
        symbol: "circle",
        symbolSize: 2 * SIZE_MARK,
        markLine: smileMarks(p, smile, order),
        markArea: moveBand(p, smile),
      },
    ],
  };
}
