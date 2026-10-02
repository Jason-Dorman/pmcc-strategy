// A data table (UI-SPEC §5): TanStack Table for sorting, TanStack Virtual for the long ones (the
// ledger, the blotter), at a fixed row height. Every column sorts. Each filter is a row of
// toggles above the table, one per value the rows have; a row passes when it offers a value
// toggled on, and with none on the filter is off. The look is shell.css's: hairlines, a sticky
// header, mono numbers right-aligned.
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type RowData,
  type SortFn,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useMemo, useRef, useState, type ReactNode } from "react";

import { TABLE_OVERSCAN, TABLE_ROW_HEIGHT } from "../theme/tokens";

export type SortValue = number | string | undefined;

export interface TableColumn<T> {
  id: string;
  header: string;
  /** What the column sorts by; `undefined` (no value) sorts last either way. */
  sort: (row: T) => SortValue;
  cell: (row: T) => ReactNode;
  /** A number: right-aligned, tabular figures. */
  num?: boolean;
}

export interface TableFilter<T> {
  id: string;
  name: string;
  /** The values a row offers the filter: its rule ID, its side, its flags. */
  offer: (row: T) => readonly string[];
  /** What a value's button says, when the value itself means nothing to a reader (a rule ID). */
  label?: (value: string) => string;
  /** The button's hover text. */
  hint?: (value: string) => string;
}

export interface DataTableProps<T> {
  /** The table's accessible name. */
  label: string;
  rows: readonly T[];
  columns: readonly TableColumn<T>[];
  rowId: (row: T, index: number) => string;
  filters?: readonly TableFilter<T>[];
  /** Render only the rows in view, each TABLE_ROW_HEIGHT tall. */
  virtual?: boolean;
}

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
});

type Features = typeof features;

function compare(a: SortValue, b: SortValue): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b));
}

// Headers are set in capitals (shell.css), which would turn a Greek δ into Δ, the sign the site
// uses for a change: a lowercase Greek letter keeps its case.
const GREEK = /([α-ω])/;

export function HeaderText({ text }: { text: string }) {
  return (
    <>
      {text.split(GREEK).map((part, i) =>
        GREEK.test(part) ? <span className="pm-greek" key={i}>{part}</span> : part)}
    </>
  );
}

function useColumns<T extends RowData>(columns: readonly TableColumn<T>[]) {
  return useMemo(() => {
    const helper = createColumnHelper<Features, T>();
    const sortFn: SortFn<Features, T> = (a, b, id) =>
      compare(a.getValue<SortValue>(id), b.getValue<SortValue>(id));
    return helper.columns(columns.map((c) =>
      helper.accessor((row: T) => c.sort(row), {
        id: c.id,
        header: () => <HeaderText text={c.header} />,
        cell: (info) => c.cell(info.row.original),
        sortFn,
        sortUndefined: "last",
        sortDescFirst: false, // every column sorts ascending first, numbers included
      })),
    );
  }, [columns]);
}

// ---- filters ----------------------------------------------------------------------------------

export type Chosen = Readonly<Record<string, readonly string[]>>;

/** A filter's values that occur in the rows, each with how many rows offer it. */
export function filterOptions<T>(rows: readonly T[], offer: (row: T) => readonly string[]) {
  const counts = new Map<string, number>();
  for (const row of rows) {
    for (const value of new Set(offer(row))) counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** The rows that pass every filter with a value toggled on. */
export function applyFilters<T>(rows: readonly T[], filters: readonly TableFilter<T>[],
                                chosen: Chosen): T[] {
  const active = filters.filter((f) => (chosen[f.id] ?? []).length > 0);
  return rows.filter((row) =>
    active.every((f) => f.offer(row).some((v) => chosen[f.id]?.includes(v))));
}

function Filters<T>({ rows, filters, chosen, onChange }: {
  rows: readonly T[];
  filters: readonly TableFilter<T>[];
  chosen: Chosen;
  onChange: (id: string, values: string[]) => void;
}) {
  if (filters.length === 0) return null;
  return (
    <div className="pm-filters">
      {filters.map((f) => {
        const on = chosen[f.id] ?? [];
        const toggle = (value: string) =>
          onChange(f.id, on.includes(value) ? on.filter((v) => v !== value) : [...on, value]);
        const options = filterOptions(rows, f.offer);
        return (
          <div className="pm-filter" role="group" aria-label={`Filter by ${f.name}`} key={f.id}>
            <span className="pm-filter-name">{f.name}</span>
            {options.length === 0 && <span className="pm-filter-none">none</span>}
            {options.map(([value, n]) => (
              <button type="button" key={value} aria-pressed={on.includes(value)}
                      className="pm-chip" title={f.hint?.(value) || undefined}
                      onClick={() => toggle(value)}>
                {f.label?.(value) ?? value} <span className="pm-chip-n">{n}</span>
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}

// ---- the table --------------------------------------------------------------------------------

const NO_FILTERS: readonly never[] = [];

function ariaSort(sorted: false | "asc" | "desc") {
  return sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none";
}

/** A spacer standing in for the rows a virtualized table doesn't render. */
function Spacer({ height, span }: { height: number; span: number }) {
  if (height <= 0) return null;
  return <tr className="pm-spacer" style={{ height }} aria-hidden="true"><td colSpan={span} /></tr>;
}

function useWindow<R>(rows: readonly R[], virtual: boolean) {
  const scroller = useRef<HTMLDivElement>(null);
  // The virtualizer hands back fresh functions each render, so the compiler leaves this hook
  // unmemoized; the table re-renders on scroll as TanStack Virtual expects.
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => TABLE_ROW_HEIGHT,
    overscan: TABLE_OVERSCAN,
    enabled: virtual,
  });
  if (!virtual) return { scroller, shown: rows, above: 0, below: 0 };
  const items = virtualizer.getVirtualItems();
  if (items.length === 0) {
    // The scroller has no size yet (a closed disclosure, the first paint): the first rows stand
    // in until it's measured, so the table is never empty while it has rows.
    const shown = rows.slice(0, TABLE_OVERSCAN);
    return { scroller, shown, above: 0, below: (rows.length - shown.length) * TABLE_ROW_HEIGHT };
  }
  const shown = items.map((item) => rows[item.index]).filter((r): r is R => r !== undefined);
  const above = items[0]?.start ?? 0;
  const below = virtualizer.getTotalSize() - (items.at(-1)?.end ?? 0);
  return { scroller, shown, above, below };
}

export function DataTable<T extends RowData>({
  label, rows, columns, rowId, filters = NO_FILTERS, virtual = false,
}: DataTableProps<T>) {
  const defs = useColumns(columns);
  const [chosen, setChosen] = useState<Chosen>({});
  const data = useMemo(() => applyFilters(rows, filters, chosen), [rows, filters, chosen]);
  const table = useTable({
    features,
    columns: defs,
    data,
    getRowId: (row, index) => rowId(row, index),
    enableSortingRemoval: false,
  });
  const visible = table.getRowModel().rows;
  const { scroller, shown, above, below } = useWindow(visible, virtual);
  const span = columns.length;
  const numeric = new Set(columns.filter((c) => c.num).map((c) => c.id));
  const align = (id: string) => (numeric.has(id) ? "pm-num" : undefined);

  return (
    <>
      <Filters rows={rows} filters={filters} chosen={chosen}
               onChange={(id, values) => setChosen((c) => ({ ...c, [id]: values }))} />
      <div className="pm-table-scroll" ref={scroller}>
        <table className={virtual ? "pm-table pm-table-fixed" : "pm-table"} aria-label={label}>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} className={align(header.column.id)}
                      aria-sort={ariaSort(header.column.getIsSorted())}>
                    <button type="button" className="pm-sort"
                            onClick={header.column.getToggleSortingHandler()}>
                      <table.FlexRender header={header} />
                      <span className="pm-sort-mark" aria-hidden="true" />
                    </button>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            <Spacer height={above} span={span} />
            {shown.map((row) => (
              <tr key={row.id}>
                {row.getAllCells().map((cell) => (
                  <td key={cell.id} className={align(cell.column.id)}>
                    <table.FlexRender cell={cell} />
                  </td>
                ))}
              </tr>
            ))}
            <Spacer height={below} span={span} />
            {visible.length === 0 && (
              <tr><td colSpan={span} className="pm-label">No rows.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
