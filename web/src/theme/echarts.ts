// The ECharts theme (UI-SPEC §4, DEC-70): the modular core with only the pieces the site draws,
// and the base option every chart starts from. Colours and font stacks are read from tokens.css
// when a chart renders, so a palette change there reaches every chart; the sizes and insets
// below are the only chart literals in the site (the token lint keeps them here).
import { LineChart, ScatterChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";

import { color, type ColorToken, type RoleToken } from "./tokens";

echarts.use([
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  AriaComponent,
  SVGRenderer,
]);

export { echarts };

// SVG, not canvas: crisp hairlines at any zoom, and the chart is in the DOM for tests and tools.
export const RENDERER = "svg" as const;

/** What a chart reads from tokens.css. */
export type Palette = Record<ColorToken | RoleToken | "negative-shade", string> & {
  fontBody: string;
  fontMono: string;
};

const PALETTE_TOKENS = [
  "bg", "surface", "surface-alt", "border", "grid", "text", "text-muted", "text-inverse",
  "accent", "accent-dim", "mark", "trade", "trade-edge", "positive", "negative", "warn",
  "nav-line", "margin-im", "margin-mm", "fit-line", "identity-line", "long-leg", "short-leg",
  "strategy-quant", "strategy-baseline", "available-funds", "negative-shade",
] as const satisfies readonly (keyof Palette)[];

/** Every colour and font stack a chart uses, as the document has them now. */
export function readPalette(root: Element = document.documentElement): Palette {
  const read = (name: string) => getComputedStyle(root).getPropertyValue(`--${name}`).trim();
  const colours = Object.fromEntries(PALETTE_TOKENS.map((t) => [t, color(t, root)]));
  return { ...colours, fontBody: read("font-body"), fontMono: read("font-mono") } as Palette;
}

// Type sizes, as theme.py's figures set them.
export const CHART_FONT = { tick: 10, legend: 10.5, tooltip: 11 } as const;

// Plot insets. The band above the plot stays empty: the legend sits inside the plot, top left.
const INSET = { left: 64, right: 18, top: 10, bottom: 28 } as const;
const LEGEND_INSET = { left: 72, top: 14 } as const;

/** One grid filling the figure. */
export const SINGLE_GRID = [{ ...INSET, containLabel: false }];

/** Two grids sharing a time axis: the upper takes most of the height, the lower a pane. */
export const STACKED_GRIDS = [
  { left: INSET.left, right: INSET.right, top: INSET.top, height: "62%" },
  { left: INSET.left, right: INSET.right, top: "74%", bottom: INSET.bottom },
];

// A lower pane's value axis: few ticks, so its labels never crowd.
export const PANE_TICKS = 2;

/** Four equal panes sharing a time axis (the position Greeks, DEC-120). The band above each pane
 * holds its axis name. */
export const FOUR_PANES = [4, 28, 52, 76].map((top) => ({
  left: INSET.left, right: INSET.right, top: `${String(top)}%`, height: "17%",
}));

// A pane's axis name: set left, just above the pane.
export const PANE_NAME_GAP = 8;

// Line weights: a series is solid; a reference is thinner and dashed or dotted. The account
// chart's NAV, IM and MM are tokens.ts's ACCOUNT_LINES.
export const LINE = { series: 1.6, ruler: 1 } as const;

/** The option every chart starts from (UI-SPEC §4 rule 1). */
export function baseOption(p: Palette) {
  return {
    animation: false,
    backgroundColor: p.surface,
    textStyle: { fontFamily: p.fontBody, color: p["text-muted"] },
    aria: { enabled: true },
    legend: {
      ...LEGEND_INSET,
      orient: "horizontal",
      itemWidth: 18,
      itemHeight: 8,
      textStyle: { color: p.text, fontFamily: p.fontBody, fontSize: CHART_FONT.legend },
      backgroundColor: p["surface-alt"],
      inactiveColor: p["text-muted"],
    },
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: p.surface,
      borderColor: p.border,
      borderWidth: 1,
      padding: [6, 9],
      className: "pm-tip",
      textStyle: { color: p.text, fontFamily: p.fontMono, fontSize: CHART_FONT.tooltip },
      axisPointer: { type: "line", lineStyle: { color: p["text-muted"], width: 1 } },
    },
  };
}

/** A grid's plot interior is SURFACE_ALT, its gridlines GRID. */
export function plotGrid(p: Palette, grid: object) {
  return { ...grid, show: true, backgroundColor: p["surface-alt"], borderColor: p.border };
}

/** A value axis: mono ticks, GRID gridlines. */
export function valueAxis(p: Palette, extra: object = {}) {
  return {
    type: "value",
    scale: true,
    axisLabel: { color: p["text-muted"], fontFamily: p.fontMono, fontSize: CHART_FONT.tick },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: p.grid, width: 1 } },
    ...extra,
  };
}

/** The style of the category (trading-time) axis; its labels and ticks come from the chart. */
export function categoryAxisStyle(p: Palette) {
  return {
    type: "category",
    boundaryGap: false,
    axisLabel: { color: p["text-muted"], fontFamily: p.fontMono, fontSize: CHART_FONT.tick },
    axisLine: { lineStyle: { color: p.border } },
    axisTick: { lineStyle: { color: p.border } },
    splitLine: { show: false },
  };
}

type Dash = "solid" | "dashed" | "dotted";

/** A line series: no markers, holes left as holes (rule 6). */
export function lineSeries(name: string, data: readonly (number | null)[], stroke: string,
                           width: number, dash: Dash = "solid", extra: object = {}) {
  return {
    name,
    type: "line",
    data,
    showSymbol: false,
    symbol: "none",
    connectNulls: false,
    color: stroke,
    lineStyle: { color: stroke, width, type: dash },
    emphasis: { disabled: true },
    ...extra,
  };
}

/** A shaded region from a series down (or up) to zero, with no line and no legend entry. */
export function shadeSeries(name: string, data: readonly (number | null)[], fill: string,
                            extra: object = {}) {
  return {
    name,
    type: "line",
    data,
    showSymbol: false,
    symbol: "none",
    connectNulls: false,
    lineStyle: { width: 0, opacity: 0 },
    areaStyle: { color: fill, origin: 0, opacity: 1 }, // the token carries the strength
    emphasis: { disabled: true },
    tooltip: { show: false },
    silent: true,
    ...extra,
  };
}

/** A horizontal reference at a value: thin, dotted, never a series hue (rule 5). */
export function ruler(p: Palette, value: number) {
  return {
    silent: true,
    symbol: "none",
    label: { show: false },
    lineStyle: { color: p["identity-line"], width: LINE.ruler, type: "dotted" },
    data: [{ yAxis: value }],
  };
}
