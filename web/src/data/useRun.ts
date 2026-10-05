// A page's results files: a run found through the index by symbol and run ID, a symbol's or the
// universe's file by its key in the index, or `rules.json`, each loaded on demand and cached
// (ARCHITECTURE §13), and the manifests of several runs for a page that draws on them all. A
// file the index lacks is "missing", never an error.
import { useEffect, useState } from "react";

import type { Index, IndexRun } from "../types/generated/index";
import type { Rules } from "../types/generated/rules";
import type { Manifest, RunResult } from "../types/generated/run_result";
import { failure, useIndex } from "./IndexContext";
import { loadFile, loadRun } from "./loader";
import type { Loaded } from "./state";

export function findRun(index: Index, symbol: string, runId: string): IndexRun | undefined {
  return index.symbols.find((s) => s.symbol === symbol)?.runs.find((r) => r.run_id === runId);
}

/** A strategy's name as the index has it (`Quant PMCC`), else its ID. */
export function strategyName(index: Index, strategyId: string): string {
  const runs = index.symbols.flatMap((s) => s.runs);
  return runs.find((r) => r.run_id === strategyId)?.name ?? strategyId;
}

/** The file at the path `locate` finds in the index, or "missing" as `what` when it finds none. */
function useLoaded<T>(locate: (index: Index) => string | undefined, what: string,
                      load: (path: string) => Promise<T>): Loaded<T> {
  const index = useIndex();
  const path = index.kind === "ready" ? locate(index.value) : undefined;
  const [loaded, setLoaded] = useState<{ path: string; state: Loaded<T> } | null>(null);

  useEffect(() => {
    if (path === undefined) return;
    let live = true;
    load(path)
      .then((value) => live && setLoaded({ path, state: { kind: "ready", value } }))
      .catch((error: unknown) => live && setLoaded({ path, state: failure(error) }));
    return () => {
      live = false;
    };
  }, [path, load]);

  if (index.kind !== "ready") return index;
  if (path === undefined) return { kind: "missing", what };
  return loaded?.path === path ? loaded.state : { kind: "loading" };
}

export function useRun(symbol: string, runId: string): Loaded<RunResult> {
  return useLoaded((index) => findRun(index, symbol, runId)?.path, `${symbol} / ${runId}`,
                   loadRun);
}

/** The manifests of the runs a page's figures came from (the universe page's, which the universe
 * files don't carry), as they load. A run the index lacks, or that fails to load, is left out:
 * the footer shows what it can (UI-SPEC §2). */
export function useManifests(runs: readonly (readonly [symbol: string, runId: string])[]):
    Manifest[] {
  const index = useIndex();
  const paths = index.kind === "ready"
    ? runs.flatMap(([symbol, runId]) => findRun(index.value, symbol, runId)?.path ?? [])
    : [];
  const key = paths.join("\n");
  const [loaded, setLoaded] = useState<{ key: string; manifests: Manifest[] } | null>(null);

  useEffect(() => {
    if (key === "") return;
    let live = true;
    void Promise.allSettled(key.split("\n").map((path) => loadRun(path))).then((results) => {
      if (live) {
        setLoaded({ key, manifests: results.flatMap((r) => (
          r.status === "fulfilled" ? [r.value.manifest] : [])) });
      }
    });
    return () => {
      live = false;
    };
  }, [key]);

  return loaded?.key === key ? loaded.manifests : [];
}

/** One of a symbol's files (`robustness`, `coverage`, `fill_check`). */
export function useSymbolFile<T>(symbol: string, file: string): Loaded<T> {
  return useLoaded((index) => index.symbols.find((s) => s.symbol === symbol)?.files[file],
                   `${symbol} / ${file}`, loadFile<T>);
}

/** One of the universe's files (`pooled`, `headline`, `suitability`, `pooled_fill_check`). */
export function useUniverseFile<T>(file: string): Loaded<T> {
  return useLoaded((index) => index.universe[file], `the universe / ${file}`, loadFile<T>);
}

/** `rules.json`, the Trade rules page's source (DEC-52), which every export writes beside the
 * index. */
export function useRules(): Loaded<Rules> {
  return useLoaded(() => "rules.json", "the rules", loadFile<Rules>);
}
