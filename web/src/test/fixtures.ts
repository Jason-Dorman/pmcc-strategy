// A small index and two runs, shaped as `pmcc export` writes them, for the route and loader tests.
import type { Index } from "../types/generated/index";
import type { Manifest, RunResult, Section } from "../types/generated/run_result";
import { SCHEMA_VERSION } from "../types/generated/version";

export const INDEX: Index = {
  schema_version: SCHEMA_VERSION,
  pmcc_version: "0.1.0",
  window: { start: "2026-03-30", end: "2026-09-25" },
  risk_free_rate: {
    value: 0.0371,
    quoted_pct: 3.73,
    series: "DGS3MO",
    as_of: "2026-03-27",
    source: "FRED",
  },
  starting_cash: 15000,
  universe: {},
  symbols: [
    {
      symbol: "NVDA",
      files: {},
      runs: [
        {
          run_id: "baseline_pmcc",
          strategy_id: "baseline_pmcc",
          name: "Baseline PMCC",
          detail: "full",
          sections: [],
          path: "NVDA/baseline_pmcc.json",
          data_source: "lseg",
          config_hash: "c".repeat(64),
          git_sha: "a".repeat(40),
        },
        {
          run_id: "quant_pmcc",
          strategy_id: "quant_pmcc",
          name: "Quant PMCC",
          detail: "full",
          sections: ["gate_log", "greek_attribution"],
          path: "NVDA/quant_pmcc.json",
          data_source: "lseg",
          config_hash: "d".repeat(64),
          git_sha: "a".repeat(40),
        },
      ],
    },
    { symbol: "QQQ", files: {}, runs: [] },
  ],
};

function manifest(runId: string): Manifest {
  return {
    run_id: runId,
    symbol: "NVDA",
    strategy_id: runId,
    git_sha: "a".repeat(40),
    git_dirty: false,
    config_hash: "c".repeat(64),
    data_manifest_hash: "e".repeat(64),
    lock_hash: "f".repeat(64),
    run_timestamp: "2026-09-30T14:42:28-04:00",
    data_source: "lseg",
    pmcc_version: "0.1.0",
  };
}

/** Only the fields the pages read; the rest of a result isn't needed here. */
export function run(runId: string, sections: Section[]): RunResult {
  return {
    schema_version: SCHEMA_VERSION,
    manifest: manifest(runId),
    config: { strategy: { report: { detail: "full", sections } } },
    blotter: [{}, {}],
    ledger: [{}, {}, {}],
    gate_log: [{}],
  } as unknown as RunResult;
}

export const FILES: Record<string, unknown> = {
  "data/index.json": INDEX,
  "data/NVDA/baseline_pmcc.json": run("baseline_pmcc", []),
  "data/NVDA/quant_pmcc.json": run("quant_pmcc", ["gate_log", "greek_attribution"]),
};

/** A fetch over `files`, answering 404 for anything else. */
export function fakeFetch(files: Record<string, unknown> = FILES) {
  return (url: string): Promise<Response> => {
    const body = files[url];
    return Promise.resolve(
      body === undefined
        ? new Response("not found", { status: 404 })
        : new Response(JSON.stringify(body), { status: 200 }),
    );
  };
}
