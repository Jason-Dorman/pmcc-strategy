// An axis tooltip's body (UI-SPEC §4 rule 7): the point's time in ET, then every series at that
// time, in mono. ECharts takes it as HTML; shell.css's .pm-tip styles it.
export type TipRow = readonly [label: string, value: string, swatch?: string];

const ESCAPES: Record<string, string> = {
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
};

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ESCAPES[c] ?? c);
}

export function tipHtml(time: string, rows: readonly TipRow[]): string {
  const body = rows
    .map(([label, value, swatch]) => {
      const key = swatch
        ? `<span class="pm-tip-swatch" style="color:${escapeHtml(swatch)}">■</span>`
        : `<span class="pm-tip-swatch"></span>`;
      return `<div class="pm-tip-row">${key}<span class="pm-tip-label">${escapeHtml(label)}</span>`
        + `<span class="pm-tip-value">${escapeHtml(value)}</span></div>`;
    })
    .join("");
  return `<div class="pm-tip-time">${escapeHtml(time)}</div>${body}`;
}

/** The data index an axis tooltip is showing. */
export function pointIndex(params: unknown): number {
  const first = (Array.isArray(params) ? params[0] : params) as { dataIndex?: number } | undefined;
  return first?.dataIndex ?? 0;
}
