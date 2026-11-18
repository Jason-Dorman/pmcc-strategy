// The live page's fixture (L4-01): `live.json` as the export writes it, after three nights: the
// first order (logged before the pick's quote was, LD-15), a failed night, and a night that
// planned no order. Sanji hasn't written his files yet.
import type { Live, LiveRun, SmileOut, VolPointOut } from "../types/generated/live";
import { SCHEMA_VERSION } from "../types/generated/version";

const PICK = { contract: "put", strike: "155", expiry: "2026-11-20", delta: -0.3188,
               iv: 0.8823 };

const FIRST: LiveRun = {
  run_at: "2026-11-15T22:31:26.205329-05:00", last_session: "2026-11-13",
  next_session: "2026-11-16", state: "cash", cash: 25000, cost_basis: null, outcome: "order",
  rule: "L-O1", reason: "sell 1 155.00 put expiring 2026-11-20 at the mid",
  order_id: "wheel-2026-11-16-P-155", strike_sent: null,
  pick: { ...PICK, bid: null, ask: null, mid: null, spread: null },
  open_orders: 1,
};

export const QUOTED: LiveRun = {
  ...FIRST, run_at: "2026-11-16T22:00:05-05:00", last_session: "2026-11-16",
  next_session: "2026-11-17", order_id: "wheel-2026-11-17-P-pct-5", strike_sent: "pct:-5",
  pick: { ...PICK, bid: 2.41, ask: 2.46, mid: 2.435, spread: 0.0205 },
};

const FAILED: LiveRun = {
  ...FIRST, run_at: "2026-11-17T22:00:03-05:00", last_session: "2026-11-17",
  next_session: "2026-11-18", state: null, cash: null, outcome: "failed", rule: "L-B1",
  reason: "Sanji's prices end on 2026-11-16, not the last completed session 2026-11-17",
  order_id: null, strike_sent: null, pick: null, open_orders: null,
};

// Three sessions of volatility (L4-02): the middle one had no strike with both sides quoted.
export const VOL: VolPointOut[] = [
  { session: "2026-11-13", close: 162.83, expiry: "2026-12-11", strike: 162.5, call_iv: 0.51,
    put_iv: 0.53, atm_iv: 0.52, rv20: 0.47 },
  { session: "2026-11-16", close: 156.14, expiry: "2026-12-18", strike: null, call_iv: null,
    put_iv: null, atm_iv: null, rv20: 0.49 },
  { session: "2026-11-17", close: 155.46, expiry: "2026-12-18", strike: 155, call_iv: 0.47,
    put_iv: 0.49, atm_iv: 0.48, rv20: 0.52 },
];

export const SMILE: SmileOut = {
  session: "2026-11-17", expiry: "2026-11-20", close: 155.46, pick: 147.5,
  points: [
    { strike: 145, right: "put", iv: 0.62, delta: -0.18 },
    { strike: 147.5, right: "put", iv: 0.58, delta: -0.3 },
    { strike: 160, right: "call", iv: 0.49, delta: 0.27 },
  ],
};

export const LIVE: Live = {
  schema_version: SCHEMA_VERSION,
  symbol: "NVDA",
  underlying_conid: 4815747,
  starting_cash: 25000,
  risk_free: { investment_yield_pct: 4.32, observed: "2026-11-12", rate: 0.042969,
               source: "FRED DGS3MO" },
  rules: [
    { id: "L-B1", rule: "Book is current", words: "Sanji's price file shows the last session." },
    { id: "L-P3", rule: "Put strike", words: "The OTM put whose delta is nearest −0.30." },
    { id: "L-O1", rule: "Order", words: "Sell to open 1 contract at a limit of the mid." },
  ],
  orders: [{ id: "wheel-2026-11-16-P-155", for: "2026-11-16", order_type: "lmt", action: "SHT",
             qty: 1, underlying: 4815747, contract: "put", expiry: "2026-11-20", strike: "155",
             ref: "open", lmt_prc: "mid" }],
  positions: null,
  fills: null,
  runs: [FIRST, QUOTED, FAILED],
  backtest: { path: "NVDA/wheel.json", start: "2026-03-30", end: "2026-09-25",
              starting_cash: 25000, pnl: 4171.5, return_on_starting_cash: 0.16686,
              sharpe_annualized: 1.573653, baseline_sharpe_annualized: 1.241761 },
  vol: VOL,
  smile: SMILE,
};
