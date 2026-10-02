// A figure (UI-SPEC §2, §4): an ECharts chart at a token height. Below its minimum width the
// panel body scrolls rather than squeezing it. The palette is read from tokens.css when the
// chart first renders.
import ReactEChartsCore from "echarts-for-react/esm/core";
import { useMemo } from "react";

import { echarts, readPalette, RENDERER, type Palette } from "../../theme/echarts";
import { HERO_FIGURE_HEIGHT, PANEL_FIGURE_HEIGHT } from "../../theme/tokens";

export interface ChartProps {
  /** Builds the chart's option from the palette. */
  build: (p: Palette) => object;
  /** The hero figure: the taller height and the wider minimum. */
  hero?: boolean;
  /** What the figure shows, for a screen reader. */
  label: string;
}

export function Chart({ build, hero = false, label }: ChartProps) {
  const option = useMemo(() => build(readPalette()), [build]);
  const height = hero ? HERO_FIGURE_HEIGHT : PANEL_FIGURE_HEIGHT;
  return (
    <div className={hero ? "pm-figure pm-figure-hero" : "pm-figure"} role="figure"
         aria-label={label}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        notMerge
        opts={{ renderer: RENDERER }}
        style={{ height }}
      />
    </div>
  );
}
