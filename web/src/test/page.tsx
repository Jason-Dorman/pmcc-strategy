// Helpers for the page tests (strategy, comparison, rules, methodology, universe): render a page
// over a fake fetch, and read its readouts, panels and tables the way a reader sees them.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { Comparison } from "../pages/Comparison";
import { Methodology } from "../pages/Methodology";
import { Rules } from "../pages/Rules";
import { Strategy } from "../pages/Strategy";
import { Universe } from "../pages/Universe";
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

export function renderRules(path = "/rules", files: Record<string, unknown> = FILES) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch(files)));
  return render(
    <MemoryRouter initialEntries={[path]}>
      <IndexProvider>
        <Routes>
          <Route path="/rules/:ruleId?" element={<Rules />} />
        </Routes>
      </IndexProvider>
    </MemoryRouter>,
  );
}

export function renderMethodology(path = "/methodology/NVDA",
                                  files: Record<string, unknown> = FILES) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch(files)));
  return render(
    <MemoryRouter initialEntries={[path]}>
      <IndexProvider>
        <Routes>
          <Route path="/methodology/:symbol?" element={<Methodology />} />
        </Routes>
      </IndexProvider>
    </MemoryRouter>,
  );
}

export function renderUniverse(files: Record<string, unknown> = FILES) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch(files)));
  return render(
    <MemoryRouter initialEntries={["/universe"]}>
      <IndexProvider>
        <Routes>
          <Route path="/universe" element={<Universe />} />
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
  return withRun("quant_pmcc", ["gate_log", "greek_attribution", "position_greeks"], change);
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

/**
 * Click a column's header to sort it, and wait until the sort shows; returns the header.
 * TanStack Table (v9) subscribes to its state in an effect after the table first renders, so a
 * click that lands straight after the table appears is rendered a beat later. Asserting at once
 * then reads the unsorted rows: this failed in CI after P7-02 (DEC-106 saw it once in four runs).
 */
export async function sortBy(table: HTMLElement, name: string | RegExp): Promise<HTMLElement> {
  const header = within(table).getByRole("columnheader", { name });
  const before = header.getAttribute("aria-sort");
  fireEvent.click(within(header).getByRole("button"));
  await waitFor(() => expect(header.getAttribute("aria-sort")).not.toBe(before));
  return header;
}
