// Helpers for the page tests (strategy, comparison): render a page over a fake fetch, and read its
// readouts, panels and tables the way a reader sees them.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { Comparison } from "../pages/Comparison";
import { Strategy } from "../pages/Strategy";
import type { RunResult, Section } from "../types/generated/run_result";
import { fakeFetch, FILES, run } from "./fixtures";

export function renderPage(page: "baseline" | "quant", files: Record<string, unknown> = FILES) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch(files)));
  return render(
    <MemoryRouter initialEntries={[`/${page}/NVDA`]}>
      <IndexProvider>
        <Routes>
          <Route path="/:page/:symbol" element={<Strategy page={page} />} />
        </Routes>
      </IndexProvider>
    </MemoryRouter>,
  );
}

export function renderComparison(files: Record<string, unknown> = FILES) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch(files)));
  return render(
    <MemoryRouter initialEntries={["/compare/NVDA"]}>
      <IndexProvider>
        <Routes>
          <Route path="/compare/:symbol" element={<Comparison />} />
        </Routes>
      </IndexProvider>
    </MemoryRouter>,
  );
}

/** The fixture files with one run replaced: its sections as given, then `change` applied. */
export function withRun(id: "baseline_pmcc" | "quant_pmcc", sections: Section[],
                        change: (r: RunResult) => RunResult = (r) => r) {
  return { ...FILES, [`data/NVDA/${id}.json`]: change(run(id, sections)) };
}

export function withQuant(change: (r: RunResult) => RunResult) {
  return withRun("quant_pmcc", ["gate_log", "greek_attribution"], change);
}

export async function panel(name: string): Promise<HTMLElement> {
  return screen.findByRole("region", { name });
}

export function readout(label: string): { value: string; hint: string } {
  const box = screen.getByText(label, { selector: ".pm-readout-label" }).parentElement;
  return {
    value: box?.querySelector(".pm-readout-value")?.textContent ?? "",
    hint: box?.querySelector(".pm-readout-hint")?.textContent ?? "",
  };
}

/** A key/value table as a record of label → value. */
export function kv(table: HTMLElement): Record<string, string> {
  return Object.fromEntries([...table.querySelectorAll("tr")].map((tr) => {
    const [k, v] = tr.querySelectorAll("td");
    return [k?.textContent ?? "", v?.textContent ?? ""];
  }));
}

export function bodyRows(table: HTMLElement): HTMLElement[] {
  return [...table.querySelectorAll<HTMLElement>("tbody tr:not(.pm-spacer)")];
}

/** The table body's row at an index; a missing row fails the test. */
export function rowAt(table: HTMLElement, index: number): HTMLElement {
  const row = bodyRows(table)[index];
  if (!row) throw new Error(`no row ${index}`);
  return row;
}

/** One column's cell texts, top to bottom. */
export function column(table: HTMLElement, index: number): string[] {
  return bodyRows(table).map((r) => r.querySelectorAll("td")[index]?.textContent ?? "");
}

/** Click a column's header to sort it; returns the header. */
export function sortBy(table: HTMLElement, name: string | RegExp): HTMLElement {
  const header = within(table).getByRole("columnheader", { name });
  fireEvent.click(within(header).getByRole("button"));
  return header;
}
