// The data table (UI-SPEC §5): every column sorts, with missing values last; a filter's toggles
// narrow the rows, none on meaning no filter; a virtualized table renders only a window of rows
// with spacers for the rest.
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { TABLE_MAX_HEIGHT, TABLE_OVERSCAN, TABLE_ROW_HEIGHT } from "../theme/tokens";
import {
  applyFilters,
  DataTable,
  filterOptions,
  HeaderText,
  type TableColumn,
  type TableFilter,
} from "./DataTable";

interface Row {
  id: string;
  rule: string;
  side: string;
  cash: number | undefined;
  flags: string[];
}

const ROWS: Row[] = [
  { id: "a", rule: "E-L1", side: "BUY", cash: -5630, flags: [] },
  { id: "b", rule: "E-S1", side: "SELL", cash: 69.5, flags: ["stale_short"] },
  { id: "c", rule: "X-S1", side: "BUY", cash: undefined, flags: ["stale_short", "funds_negative"] },
];

const COLUMNS: TableColumn<Row>[] = [
  { id: "id", header: "Id", sort: (r) => r.id, cell: (r) => r.id },
  { id: "cash", header: "Cash", num: true, sort: (r) => r.cash, cell: (r) => String(r.cash ?? "—") },
];

const FILTERS: TableFilter<Row>[] = [
  { id: "rule", name: "Rule", offer: (r) => [r.rule] },
  { id: "side", name: "Side", offer: (r) => [r.side] },
  { id: "flags", name: "Flags", offer: (r) => r.flags },
];

afterEach(cleanup);

function ids(): string[] {
  const body = screen.getByRole("table").querySelector("tbody");
  return [...(body?.querySelectorAll("tr:not(.pm-spacer)") ?? [])].map(
    (tr) => tr.querySelector("td")?.textContent ?? "");
}

describe("filters", () => {
  it("counts each value the rows offer", () => {
    expect(filterOptions(ROWS, (r) => r.flags)).toEqual([["funds_negative", 1], ["stale_short", 2]]);
  });

  it("passes every row with nothing toggled", () => {
    expect(applyFilters(ROWS, FILTERS, {})).toHaveLength(3);
    expect(applyFilters(ROWS, FILTERS, { rule: [] })).toHaveLength(3);
  });

  it("passes a row offering any value toggled on, across every active filter", () => {
    expect(applyFilters(ROWS, FILTERS, { rule: ["E-L1", "X-S1"] }).map((r) => r.id)).toEqual(["a", "c"]);
    expect(applyFilters(ROWS, FILTERS, { rule: ["E-L1", "X-S1"], side: ["SELL"] })).toEqual([]);
    expect(applyFilters(ROWS, FILTERS, { flags: ["funds_negative"] }).map((r) => r.id)).toEqual(["c"]);
  });

  it("toggles narrow the table and widen it again", () => {
    render(<DataTable label="T" rows={ROWS} columns={COLUMNS} filters={FILTERS} rowId={(r) => r.id} />);
    const side = screen.getByRole("group", { name: "Filter by Side" });
    const buy = within(side).getByRole("button", { name: /BUY/ });
    fireEvent.click(buy);
    expect(buy.getAttribute("aria-pressed")).toBe("true");
    expect(ids()).toEqual(["a", "c"]);
    fireEvent.click(buy);
    expect(ids()).toEqual(["a", "b", "c"]);
  });

  it("says when a filter has nothing to offer", () => {
    const clean = ROWS.map((r) => ({ ...r, flags: [] }));
    render(<DataTable label="T" rows={clean} columns={COLUMNS} filters={FILTERS} rowId={(r) => r.id} />);
    expect(within(screen.getByRole("group", { name: "Filter by Flags" })).getByText("none"))
      .toBeDefined();
  });
});

describe("sorting", () => {
  it("sorts on a header click, missing values last either way", () => {
    render(<DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id} />);
    const header = screen.getByRole("columnheader", { name: /Cash/ });
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("ascending");
    expect(ids()).toEqual(["a", "b", "c"]);
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("descending");
    expect(ids()).toEqual(["b", "a", "c"]);
  });

  it("right-aligns number columns", () => {
    render(<DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id} />);
    expect(screen.getByRole("columnheader", { name: /Cash/ }).className).toBe("pm-num");
  });
});

describe("sorting numbers", () => {
  it("sorts numbers by value, not as text", () => {
    const rows: Row[] = [-13.5, 9, -5630, 10].map((cash, i) => ({
      id: String(i), rule: "E-S1", side: "SELL", cash, flags: [],
    }));
    render(<DataTable label="T" rows={rows} columns={COLUMNS} rowId={(r) => r.id} />);
    fireEvent.click(within(screen.getByRole("columnheader", { name: /Cash/ })).getByRole("button"));
    expect(ids()).toEqual(["2", "0", "1", "3"]); // -5630, -13.5, 9, 10
  });
});

describe("headers", () => {
  it("keeps a Greek letter's case out of the header's capitals", () => {
    render(<HeaderText text="L δ" />);
    expect(screen.getByText("δ").className).toBe("pm-greek");
  });
});

describe("virtualization", () => {
  const many: Row[] = Array.from({ length: 500 }, (_, i) => ({
    id: String(i).padStart(3, "0"), rule: "E-S1", side: "SELL", cash: i, flags: [],
  }));

  it("renders a window of rows and a spacer for the rest", () => {
    render(<DataTable label="T" rows={many} columns={COLUMNS} rowId={(r) => r.id} virtual />);
    const table = screen.getByRole("table");
    expect(table.className).toContain("pm-table-fixed");
    const rendered = ids();
    expect(rendered.length).toBeGreaterThan(0);
    expect(rendered.length).toBeLessThanOrEqual(TABLE_OVERSCAN);
    expect(rendered[0]).toBe("000");
    const spacer = table.querySelector<HTMLElement>("tr.pm-spacer");
    expect(spacer?.style.height).toBe(`${(500 - rendered.length) * TABLE_ROW_HEIGHT}px`);
  });

  describe("on a scroller with a size", () => {
    // jsdom lays nothing out: give every element the table's maximum height, as a browser would
    // give the scroller (P7-01 review: the windowing itself was untested).
    const saved = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight");
    beforeEach(() => {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight",
                            { configurable: true, get: () => TABLE_MAX_HEIGHT });
    });
    afterEach(() => {
      if (saved) Object.defineProperty(HTMLElement.prototype, "offsetHeight", saved);
    });

    const VISIBLE = TABLE_MAX_HEIGHT / TABLE_ROW_HEIGHT;

    function spacers() {
      const [above, below] = ["first-child", "last-child"].map((at) =>
        screen.getByRole("table").querySelector<HTMLElement>(`tbody tr.pm-spacer:${at}`));
      return { above: above?.style.height ?? "0px", below: below?.style.height ?? "0px" };
    }

    async function scrollTo(top: number) {
      const scroller = screen.getByRole("table").parentElement as HTMLElement;
      scroller.scrollTop = top;
      await act(async () => {
        fireEvent.scroll(scroller);
        await new Promise((resolve) => setTimeout(resolve, 20));
      });
    }

    it("renders the rows in view and the overscan, and spacers for the rest", () => {
      render(<DataTable label="T" rows={many} columns={COLUMNS} rowId={(r) => r.id} virtual />);
      const shown = ids();
      expect(shown).toHaveLength(VISIBLE + TABLE_OVERSCAN);
      expect(shown[0]).toBe("000");
      expect(spacers().below).toBe(`${(500 - shown.length) * TABLE_ROW_HEIGHT}px`);
    });

    it("renders the rows around the scroll position, contiguous", async () => {
      render(<DataTable label="T" rows={many} columns={COLUMNS} rowId={(r) => r.id} virtual />);
      await scrollTo(100 * TABLE_ROW_HEIGHT);
      const first = 100 - TABLE_OVERSCAN;
      const last = 100 + VISIBLE + TABLE_OVERSCAN - 1;
      expect(ids()).toEqual(Array.from({ length: last - first + 1 },
                                        (_, i) => String(first + i).padStart(3, "0")));
      expect(spacers()).toEqual({ above: `${first * TABLE_ROW_HEIGHT}px`,
                                  below: `${(499 - last) * TABLE_ROW_HEIGHT}px` });
    });

    it("windows the sorted rows, not the rows as given", async () => {
      render(<DataTable label="T" rows={many} columns={COLUMNS} rowId={(r) => r.id} virtual />);
      const header = screen.getByRole("columnheader", { name: /Cash/ });
      fireEvent.click(within(header).getByRole("button"));
      fireEvent.click(within(header).getByRole("button")); // descending
      await scrollTo(100 * TABLE_ROW_HEIGHT);
      expect(ids()[0]).toBe(String(499 - (100 - TABLE_OVERSCAN)).padStart(3, "0"));
    });
  });

  it("renders every row when not virtual", () => {
    render(<DataTable label="T" rows={many} columns={COLUMNS} rowId={(r) => r.id} />);
    expect(ids()).toHaveLength(500);
  });
});

// ---- a row's detail and the row a reader arrived for (the Trade rules page, P7-03) -----------

describe("a row's detail", () => {
  const detail = {
    header: "Why",
    label: (r: Row) => `Why ${r.id}`,
    render: (r: Row) => (r.id === "c" ? undefined : `because ${r.rule}`),
  };

  function table() {
    return render(<DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id}
                             detail={detail} />);
  }

  it("opens under its row on its toggle, and closes again", () => {
    table();
    const toggle = screen.getByRole("button", { name: "Why a" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("because E-L1")).toBeNull();

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    const opened = screen.getByText("because E-L1").closest("tr");
    expect(opened?.previousElementSibling?.textContent).toContain("a");
    expect(opened?.querySelector("td")?.colSpan).toBe(COLUMNS.length + 1);

    fireEvent.click(toggle);
    expect(screen.queryByText("because E-L1")).toBeNull();
  });

  it("gives a row with nothing to open no toggle", () => {
    table();
    expect(screen.queryByRole("button", { name: "Why c" })).toBeNull();
    expect(screen.getByRole("button", { name: "Why b" })).toBeTruthy();
  });

  it("travels with its row when the table sorts", () => {
    table();
    fireEvent.click(screen.getByRole("button", { name: "Why b" }));
    fireEvent.click(within(screen.getByRole("columnheader", { name: "Cash" })).getByRole("button"));
    const opened = screen.getByText("because E-S1").closest("tr");
    expect(opened?.previousElementSibling?.textContent).toContain("b");
  });
});

describe("the row a reader arrived for", () => {
  it("is outlined and scrolled into view", () => {
    const scrolled: Element[] = [];
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (this: Element) {
      scrolled.push(this);
    };
    try {
      render(<DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id}
                        target="b" />);
      const rows = screen.getAllByRole("row").slice(1);
      expect(rows.map((r) => r.classList.contains("pm-target"))).toEqual([false, true, false]);
      expect(scrolled).toEqual([rows[1]]);
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it("outlines nothing when the target isn't a row", () => {
    const { container } = render(
      <DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id} target="zz" />);
    expect(container.querySelector(".pm-target")).toBeNull();
  });
});

describe("height", () => {
  it("caps a table at TABLE_MAX_HEIGHT unless it grows to its rows (PO, DEC-112)", () => {
    const { container, rerender } = render(
      <DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id} />);
    const scroller = () => container.querySelector(".pm-table-scroll");
    expect(scroller()?.classList.contains("pm-table-grow")).toBe(false);
    rerender(<DataTable label="T" rows={ROWS} columns={COLUMNS} rowId={(r) => r.id} grow />);
    expect(scroller()?.classList.contains("pm-table-grow")).toBe(true);
  });
});
