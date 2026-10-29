// A figure (UI-SPEC §2, §4): an ECharts chart at a token height. Below its minimum width the
// panel body scrolls rather than squeezing it. The palette is read from tokens.css when the
// chart first renders.
import ReactEChartsCore from "echarts-for-react/esm/core";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { echarts, readPalette, RENDERER, type Palette } from "../../theme/echarts";
import { HERO_FIGURE_HEIGHT, PANEL_FIGURE_HEIGHT } from "../../theme/tokens";

export interface ChartProps {
  /** Builds the chart's option from the palette. */
  build: (p: Palette) => object;
  /** The hero figure: the taller height and the wider minimum. */
  hero?: boolean;
  /** What the figure shows, for a screen reader. */
  label: string;
  /** A click anywhere on a plot picks the category under it: its index on the time axis (the
   * wheel's portfolio at a bar, WD-22). */
  onPick?: ((index: number) => void) | undefined;
}

/** What a chart instance offers a click on its plot. */
interface Pickable {
  getZr(): { on(event: "click", handler: (e: { offsetX: number; offsetY: number }) => void): void };
  containPixel(finder: { gridIndex: number }, point: number[]): boolean;
  convertFromPixel(finder: { gridIndex: number }, point: number[]): number[] | number;
  getOption(): object;
}

/** The category index under a click, on whichever grid it landed in; none outside the plots. */
export function pickedIndex(chart: Pickable, x: number, y: number): number | undefined {
  const grids = (chart.getOption() as { grid?: unknown[] }).grid?.length ?? 0;
  for (let gridIndex = 0; gridIndex < grids; gridIndex++) {
    if (!chart.containPixel({ gridIndex }, [x, y])) continue;
    const at = chart.convertFromPixel({ gridIndex }, [x, y]);
    const index = Array.isArray(at) ? at[0] : at;
    return typeof index === "number" && Number.isFinite(index) ? Math.round(index) : undefined;
  }
  return undefined;
}

export function Chart({ build, hero = false, label, onPick }: ChartProps) {
  const option = useMemo(() => build(readPalette()), [build]);
  const height = hero ? HERO_FIGURE_HEIGHT : PANEL_FIGURE_HEIGHT;
  // The chart is ready once, so its click handler reads the latest onPick through a ref.
  const pick = useRef(onPick);
  useEffect(() => {
    pick.current = onPick;
  }, [onPick]);
  const ready = useCallback((chart: Pickable) => {
    chart.getZr().on("click", (e) => {
      const index = pickedIndex(chart, e.offsetX, e.offsetY);
      if (index !== undefined) pick.current?.(index);
    });
  }, []);
  return (
    <div className={hero ? "pm-figure pm-figure-hero" : "pm-figure"} role="figure"
         aria-label={label}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        notMerge
        opts={{ renderer: RENDERER }}
        style={{ height }}
        {...(onPick ? { onChartReady: ready } : {})}
      />
    </div>
  );
}
