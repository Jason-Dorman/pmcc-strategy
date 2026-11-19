// The live page (L4-01; UI-SPEC §6 › Live; PO, LD-10, LD-16): the live wheel as tonight's run and
// Sanji last left it. Readouts from the latest run-log row, then the algorithm in words with its
// rules, the open orders, Sanji's positions and fills, and the nightly run log, all from
// `live.json`.
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import { pending, PageFrame } from "../components/PageFrame";
import type { Readout } from "../components/Readouts";
import type { Loaded } from "../data/state";
import { useLive } from "../data/useRun";
import { money } from "../format/money";
import { orDash, ratio } from "../format/number";
import { timeET } from "../format/time";
import { holdsShares, stateLabel } from "../format/wheel";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { Live as LiveFile, LiveRun } from "../types/generated/live";
import { Algorithm, LiveRules, OpenOrders, option, RunLog, SanjiFile } from "./live/sections";
import { IvRv, Smile } from "./live/vol";
import { panel, whenLoaded } from "./placeholder";

const READOUT_HINTS = [
  ["State", "What Sanji's book holds, read each night"],
  ["Cash", "Sanji starts no book: the starting cash until the first fill"],
  ["Cost basis", "Of the shares, while they're held"],
  ["Next session", "The session the last run planned"],
  ["Tonight's decision", "The last run's order, or why there was none"],
  ["Last run", "The nightly run's time, in New York"],
] as const;

const PENDING = pending(READOUT_HINTS.map(([l, h]) => [l, h]));

/** The decision readout: by the row's outcome, an order's pick when the row has one. */
function decision(row: LiveRun): [string, string] {
  if (row.outcome === "order") {
    return row.pick
      ? [`Sell 1 ${row.pick.contract}`,
         `${option(row.pick)}; delta ${ratio(row.pick.delta)} at the close`]
      : ["Order", `${row.rule}: ${row.reason}`];
  }
  return [row.outcome === "failed" ? "Failed" : "No order", `${row.rule}: ${row.reason}`];
}

function readouts(live: LiveFile): Readout[] {
  const row = live.runs.at(-1);
  if (row === undefined) return PENDING;
  const [value, why] = decision(row);
  const shown: readonly (readonly [string, string])[] = [
    [orDash(row.state, stateLabel), ""],
    [orDash(row.cash, money), ""],
    [row.state !== null && holdsShares(row.state) ? orDash(row.cost_basis, money) : "—", ""],
    [row.next_session, ""],
    [value, why],
    [timeET(row.run_at), row.outcome === "failed" ? "; it failed, so no new order" : ""],
  ];
  return READOUT_HINTS.map(([label, hint], i) => {
    const [v, extra] = shown[i] ?? ["—", ""];
    const text = label === "Tonight's decision" ? extra : `${hint}${extra}`;
    return { label, value: v, hint: text };
  });
}

/** The live wheel's file, or why a panel can't show it: still loading, missing, or the route
 * names a symbol the live wheel doesn't trade. */
function forSymbol(state: Loaded<LiveFile>, symbol: string): Loaded<LiveFile> {
  if (state.kind !== "ready" || state.value.symbol === symbol) return state;
  return { kind: "error",
           message: `The wheel forward test trades ${state.value.symbol}, not ${symbol}.` };
}

export function Live() {
  const { symbol = "" } = useParams();
  const state = forSymbol(useLive(), symbol);
  const body = (render: (l: LiveFile) => ReactNode) => whenLoaded(state, render);
  return (
    <PageFrame
      readouts={state.kind === "ready" ? readouts(state.value) : PENDING}
      panels={[
        { ...panel("algorithm", "The algorithm", W_FULL, body((l) => <Algorithm live={l} />),
                   false) },
        { ...panel("orders", "Open orders", W_FULL, body((l) => <OpenOrders live={l} />)),
          note: "open_orders.json, as the nightly run left it",
          caption: <>Picked at the close is the option the nightly run chose from LSEG&apos;s
            chain at the last close; Sent as is the strike Sanji gets, a put&apos;s as its percent
            below the close, which Sanji applies to the open so the strike moves with a gap
            (LD-29). An order stays in the file until the week it&apos;s for has ended; Sanji
            acts on it only on its own session, and never fills an id twice. Monday Nov 16&apos;s
            order was first written with its strike as a number, $155, and re-sent before the open
            as its percent below Friday&apos;s close, so the run log&apos;s first rows name its
            first id.</> },
        { ...panel("vol", "Implied against realized", W_HALF, body((l) => <IvRv live={l} />)),
          note: "live/vol.jsonl, from LSEG each night",
          caption: <>NVDA&apos;s ATM implied vol for the weekly expiry nearest 30 days out (the
            call&apos;s and put&apos;s at the strike nearest the close, averaged) against its
            realized vol over the 20 sessions to that close. The wheel sells options, so it is paid
            when the shaded gap has IV on top: the market prices more movement than the stock then
            delivers.</> },
        { ...panel("smile", "This week's skew", W_HALF, body((l) => <Smile live={l} />)),
          note: "live/smile.json, at the last close",
          caption: <>
            <p>This chart shows implied volatility across the out-of-the-money options expiring
              at the end of the coming week, with puts below the stock&apos;s closing price and
              calls above it.</p>
            <p>One thing that stands out is the volatility skew. Rather than a symmetrical smile,
              the puts generally have higher implied volatility than the calls. You can also see
              the impact of earnings: when an expiration includes an earnings announcement,
              implied volatility tends to increase across the strikes, pushing the entire curve
              higher and sometimes making it flatter.</p>
            <p>The dashed line marks the put strike my L-P3 rule would select based on the
              closing price, targeting a delta closest to −0.30. The chart shows where that strike
              falls, although the strategy only submits an order for the first trading session of
              each week.</p></> },
        { ...panel("positions", "Positions", W_HALF, body((l) => (
            <SanjiFile file={l.positions} empty="No positions yet." />))),
          note: "Sanji's positions.json" },
        { ...panel("fills", "Fills", W_HALF, body((l) => (
            <SanjiFile file={l.fills} empty="No fills yet." />))),
          note: "Sanji's fills.json" },
        { ...panel("runs", "Nightly run log", W_FULL, body((l) => <RunLog live={l} />)),
          note: "newest first, from live/runs.jsonl",
          caption: <>One row a night, failed nights included. The option is the night&apos;s
            pick: its delta and IV are Black-Scholes from the mid at the close, and its bid, ask,
            mid and spread are its quote then (— before the log kept them).</> },
        { ...panel("rules", "The rules", W_FULL, body((l) => <LiveRules live={l} />)),
          note: "configs/live.yaml" },
      ]}
    />
  );
}
