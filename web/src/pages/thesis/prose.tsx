// The thesis page's prose (UI-SPEC §6 › Thesis; T4-01). The thesis, its explanation, its horizons
// and the macro paragraph are THESIS-SPEC §1's text (PO, TD-28), less its pointers to the spec's
// own sections. The dated summary under the macro paragraph is generated from the tracker's
// measured values alone (TD-10): no news, no explanation of a day's move.
import { longDate } from "../../components/charts/axis";
import { KeyValue } from "../../components/cells";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Note } from "../../components/Note";
import { count, iv, orDash, pct } from "../../format/number";
import { bps, bpsChange, creditLabel, level, volPts } from "../../format/thesis";
import { timeET } from "../../format/time";
import type { Thesis, ThesisParameters, ThesisSource } from "../../types/generated/thesis";

export function TheThesis() {
  return (
    <Note>
      <p>
        <b>Following equity-volatility spikes, options overprice subsequent market fluctuations when
          corporate credit conditions remain stable and realized volatility begins to normalize,
          creating opportunities to sell protection selectively after costs.</b>
      </p>
      <p>
        The proposed mechanism is that demand for protection can remain elevated after an initial
        equity-market shock. If credit conditions remain stable and actual price fluctuations begin
        to diminish, the insurance price may decline more slowly than the underlying risk. Stable
        credit is proposed as evidence that the shock is less likely to become a persistent
        financing or solvency problem.
      </p>
      <p>
        This is a testable interpretation, not an established causal conclusion. Credit spreads can
        lag, volatility can rise again, and option sellers ordinarily receive compensation for
        bearing adverse tail outcomes. The system must test whether the credit condition adds
        information beyond an ordinary volatility forecast and whether the resulting trades offer
        useful net compensation for their exposure.
      </p>
    </Note>
  );
}

const HORIZONS: readonly (readonly [string, string])[] = [
  ["Thesis useful life",
   "Working estimate of 12–24 months as a recurring opportunity, reassessed quarterly. This is a "
   + "planning estimate, not an empirical forecast of persistence."],
  ["Forecast and tracker horizon",
   "30 calendar days, using the daily-close realized-variance convention described under "
   + "Methodology."],
  ["Contract horizon",
   "Approximately 30 calendar days to expiration at the intended execution date."],
  ["Expected trade lifetime",
   "Approximately 5–10 trading sessions; a provisional estimate, until measured trades exist."],
  ["Maximum planned holding period",
   "Ten trading sessions after entry, with earlier exits."],
];

export function Horizons() {
  return (
    <Note>
      <ul className="pm-terms">
        {HORIZONS.map(([name, text]) => <li key={name}><b>{name}.</b> {text}</li>)}
      </ul>
    </Note>
  );
}

/** The measured state in one sentence, dated: only what the tracker holds. */
export function stateSentence(t: Thesis): string {
  const c = t.current;
  if (c === null) return "No session is in the tracker yet.";
  const shock = c.shock_level === null ? ""
    : `, against a spike threshold of ${level(c.shock_level)}`;
  const credit = c.credit_bps === null
    ? "no usable credit spread"
    : `a high-yield spread of ${bps(c.credit_bps)} (${creditLabel(c.credit_status).toLowerCase()}`
      + `${c.credit_change_short_bps === null ? "" : `, ${bpsChange(c.credit_change_short_bps)} `
        + "over five observations"})`;
  return `At the ${longDate(c.day)} close: VIX at ${orDash(c.vix, level)}${shock}; a 30-day `
    + `volatility forecast of ${orDash(c.forecast_vol, iv)}, so VIX minus the forecast is `
    + `${orDash(c.forecast_gap_vol, volPts)}; realized volatility of ${orDash(c.rv_short, iv)} over `
    + `5 sessions and ${orDash(c.rv_long, iv)} over 20; and ${credit}.`;
}

export function Macro({ thesis }: { thesis: Thesis }) {
  return (
    <Note>
      <p>
        This thesis is most plausible when a volatility spike reflects a temporary repricing of
        equity risk while corporate financing conditions remain comparatively stable. Persistent
        inflation surprises, unexpected changes in Federal Reserve policy, deteriorating credit
        conditions, or renewed equity selling could instead produce sustained volatility. A
        technology-sector selloff could remain concentrated or spread into broader financial stress;
        the strategy therefore evaluates broad equity volatility alongside corporate credit rather
        than assuming every selloff will reverse. Lower implied volatility alone does not guarantee
        a profitable trade, because the underlying can move enough to overwhelm the benefit from
        cheaper options. These relationships are hypotheses evaluated by the tracker and historical
        tests, not assumptions that a particular macro regime is currently present.
      </p>
      <p><b>Measured state.</b> {stateSentence(thesis)}</p>
    </Note>
  );
}

// ---- methodology --------------------------------------------------------------------------------

const SOURCE_COLUMNS: readonly TableColumn<ThesisSource>[] = [
  { id: "series", header: "Series", sort: (s) => s.series, cell: (s) => s.series },
  { id: "provider", header: "Provider", sort: (s) => s.provider, cell: (s) => s.provider },
  { id: "identifier", header: "Identifier", sort: (s) => s.identifier, cell: (s) => s.identifier },
  { id: "first", header: "First", sort: (s) => s.first ?? undefined,
    cell: (s) => orDash(s.first, String) },
  { id: "last", header: "Last", sort: (s) => s.last ?? undefined,
    cell: (s) => orDash(s.last, String) },
  { id: "n", header: "Values", num: true, sort: (s) => s.observations,
    cell: (s) => count(s.observations) },
  { id: "units", header: "Units", sort: (s) => s.units, cell: (s) => s.units },
  { id: "note", header: "Note", sort: (s) => s.note,
    cell: (s) => <div className="pm-prose">{s.note}</div> },
];

function Rules({ p }: { p: ThesisParameters }) {
  return (
    <ol className="pm-steps">
      <li><b>Forecast.</b> Each day&apos;s S&amp;P 500 log return is squared and averaged with
        exponentially falling weights (a decay of {p.ewma_lambda}), starting from the mean of the
        first {p.initialization_sessions} returns. The 30-day forecast is that daily variance times
        the number of closes in the next {p.horizon_calendar_days} calendar days, annualized on a
        365-day year.</li>
      <li><b>Gap.</b> VIX, as a decimal, minus the forecast volatility: both cover the same{" "}
        {p.horizon_calendar_days} calendar days.</li>
      <li><b>Outcome.</b> Once the {p.horizon_calendar_days} days have passed, the sum of squared
        daily returns in them is the realized variance. The variance premium is VIX&apos;s implied
        30-day variance minus that. It is computed from daily closes, so it is not an exact
        replication of a variance swap, and VIX is not the implied volatility of any one option.</li>
      <li><b>Spike.</b> VIX at or above the {pct(p.percentile_threshold, 0)} percentile of the{" "}
        {p.percentile_lookback_sessions} sessions before, and at least {p.minimum_vix_ratio} times
        its level {p.ratio_lookback_sessions} sessions earlier, once {p.signal_warmup_sessions}{" "}
        returns exist. A spike opens a search of {p.search_sessions_after_shock} sessions; another
        spike inside it is ignored.</li>
      <li><b>Candidate.</b> The first session of the search where {p.short_rv_sessions}-session
        realized volatility is below {p.long_rv_sessions}-session, is no higher than{" "}
        {p.falling_rv_comparison_sessions} sessions earlier, and the gap is at least{" "}
        {(p.minimum_forecast_gap * 100).toFixed(1)} volatility points. It is fixed before credit is read, so credit can never
        move it to a better day.</li>
      <li><b>Credit.</b> Stable when the latest usable spread is at most{" "}
        {bps(p.credit_maximum_level_bps)}, its change over five observations at most{" "}
        {bpsChange(p.credit_maximum_change_short_bps)}, and over twenty at most{" "}
        {bpsChange(p.credit_maximum_change_long_bps)}. An observation is assumed usable{" "}
        {p.credit_publication_lag_business_days} business days after its date, at{" "}
        {p.credit_publication_time_et} New York, and for at most{" "}
        {p.credit_maximum_age_business_days} business days; otherwise credit is unavailable, which
        is not the same as unstable.</li>
      <li><b>Decision.</b> A session is decided at {p.decision_time_et} New York, with only what was
        known then. A run before that leaves the session out.</li>
    </ol>
  );
}

const LIMITS: readonly string[] = [
  "The thresholds are provisional assumptions set before the history was examined; they were not "
  + "tuned to it, and no result here is out-of-sample.",
  "Credit data starts in November 2023: FRED serves the last three years of this series, and the "
  + "course's LSEG account is not entitled to it. Earlier candidates have no credit assessment.",
  "Daily outcomes overlap: consecutive sessions share most of their 30 days, so the all-sessions "
  + "row is far fewer independent observations than its count.",
  "A larger gap between VIX and what followed can simply reflect a higher starting VIX, so each "
  + "group's starting VIX is shown beside it. Nothing here establishes cause.",
  "No trade is simulated. Two of the three wrong-if conditions, and any claim about net return, "
  + "wait for the options backtest.",
];

export function Methodology({ thesis }: { thesis: Thesis }) {
  return (
    <>
      <Note>
        <p>
          Every number on this page is computed each night from daily closes and the published
          credit spread, all of it recomputed from the sources, and committed to the site as one
          file. If a source does not answer, nothing is written and the last good file stays, with
          its date. Last updated {timeET(thesis.generated_at)}.
        </p>
      </Note>
      <Details summary="How the tracker is computed">
        {thesis.parameters ? <Rules p={thesis.parameters} /> : <p>The rules&apos; values arrive with
          the next nightly run.</p>}
      </Details>
      <Details summary="Limitations">
        <ul className="pm-terms">{LIMITS.map((l) => <li key={l}>{l}</li>)}</ul>
      </Details>
      <Details summary="Data sources and coverage" table>
        <DataTable label="Data sources" rows={thesis.sources} columns={SOURCE_COLUMNS}
                   rowId={(s) => s.series} wrap grow />
        <Note>
          <p>
            S&amp;P 500 and VIX closes from LSEG. ICE BofA US High Yield Index Option-Adjusted
            Spread (BAMLH0A0HYM2): ICE Data Indices, LLC, retrieved from FRED, Federal Reserve Bank
            of St. Louis. This product uses the FRED® API but is not endorsed or certified by the
            Federal Reserve Bank of St. Louis. Cboe computes VIX from S&amp;P 500 option prices for
            a constant 30-day term.
          </p>
        </Note>
      </Details>
      <Details summary="Version" table>
        <KeyValue label="Version" rows={[
          ["Model version", thesis.model_version],
          ["Configuration hash", thesis.config_hash.slice(0, 12)],
          ["Schema version", String(thesis.schema_version)],
        ]} />
      </Details>
    </>
  );
}
