// A data table (UI-SPEC §5): TanStack Table for sorting, TanStack Virtual for the long ones (the
// ledger, the blotter), at a fixed row height. Every column sorts. Each filter is a row of
// toggles above the table, one per value the rows have; a row passes when it offers a value
// toggled on, and with none on the filter is off. A row can open a detail under it (a rule's
// rationale), and the row a reader arrived for is scrolled to and outlined (the Trade rules page).
// The look is shell.css's: hairlines, a sticky header, mono numbers right-aligned.
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
import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

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

export interface TableDetail<T> {
  /** The toggle column's header. */
  header: string;
  /** The toggle's accessible name for a row: `Rationale for E-T1`. */
  label: (row: T) => string;
  /** What opens under a row; `undefined` for a row with nothing to open, which gets no toggle. */
  render: (row: T) => ReactNode;
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
  /** A detail each row can open under it, toggled from a leading column (not with `virtual`). */
  detail?: TableDetail<T> | undefined;
  /** The row ID a reader arrived for (`#/rules/X-S3`): scrolled into view and outlined, in
   * `--accent` (chrome, not data). Not with `virtual`, which may not render it. */
  target?: string | undefined;
  /** Cells wrap, top-aligned: a table of prose (the rules). */
  wrap?: boolean;
  /** As tall as its rows, without TABLE_MAX_HEIGHT's cap: the rule tables (PO, DEC-112). */
  grow?: boolean;
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

/** A row's detail toggle. */
function Toggle({ open, label, controls, onClick }: {
  open: boolean;
  label: string;
  controls: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className="pm-toggle" aria-expanded={open} aria-label={label}
            aria-controls={open ? controls : undefined} onClick={onClick}>
      {open ? "▾" : "▸"}
    </button>
  );
}

/** Scrolls the target row into view once it renders; the ref goes on that row. */
function useTarget(target: string | undefined, present: boolean) {
  const ref = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    if (present) ref.current?.scrollIntoView({ block: "center" });
  }, [target, present]);
  return ref;
}

export function DataTable<T extends RowData>({
  label, rows, columns, rowId, filters = NO_FILTERS, virtual = false, detail, target,
  wrap = false, grow = false,
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
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const targetRef = useTarget(target, visible.some((r) => r.id === target));
  const span = columns.length + (detail ? 1 : 0);
  const flip = (id: string) => setOpen((o) => {
    const next = new Set(o);
    if (!next.delete(id)) next.add(id);
    return next;
  });
  const classes = ["pm-table", virtual && "pm-table-fixed", wrap && "pm-table-wrap"];
  const numeric = new Set(columns.filter((c) => c.num).map((c) => c.id));
  const align = (id: string) => (numeric.has(id) ? "pm-num" : undefined);

  return (
    <>
      <Filters rows={rows} filters={filters} chosen={chosen}
               onChange={(id, values) => setChosen((c) => ({ ...c, [id]: values }))} />
      <div className={grow ? "pm-table-scroll pm-table-grow" : "pm-table-scroll"} ref={scroller}>
        <table className={classes.filter(Boolean).join(" ")} aria-label={label}>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {detail && <th className="pm-toggle-col">{detail.header}</th>}
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
            {shown.map((row) => {
              const more = detail?.render(row.original);
              const isOpen = more !== undefined && open.has(row.id);
              const detailId = `pm-detail-${label}-${row.id}`.replace(/[^\w-]+/g, "-");
              const isTarget = row.id === target;
              return (
                <Fragment key={row.id}>
                  <tr className={isTarget ? "pm-target" : undefined}
                      ref={isTarget ? targetRef : undefined}>
                    {detail && (
                      <td className="pm-toggle-col">
                        {more !== undefined && (
                          <Toggle open={isOpen} label={detail.label(row.original)}
                                  controls={detailId} onClick={() => flip(row.id)} />
                        )}
                      </td>
                    )}
                    {row.getAllCells().map((cell) => (
                      <td key={cell.id} className={align(cell.column.id)}>
                        <table.FlexRender cell={cell} />
                      </td>
                    ))}
                  </tr>
                  {isOpen && (
                    <tr className="pm-detail-row" id={detailId}>
                      <td colSpan={span}>{more}</td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
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
