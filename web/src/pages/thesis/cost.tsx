// The thesis page's potential return and trading costs (UI-SPEC §6 › Thesis; PO, TD-07, TD-21,
// TD-30): a gross premium in volatility points and a cost as a share of an option's price, each
// with its unit and denominator, never netted against each other.
import { KeyValue } from "../../components/cells";
import { longDate } from "../../components/charts/axis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { count, pct } from "../../format/number";
import { completed, level, points, variance } from "../../format/thesis";
import type { Thesis, ThesisCohort, ThesisLegCost } from "../../types/generated/thesis";
import { Disclosure, Section, Titled } from "./parts";

function median(c: ThesisCohort): string {
  if (c.median_vol_gap === null || c.count < 2) return "";
  return ` The median was ${c.median_vol_gap < 0 ? "−" : "+"}${points(c.median_vol_gap)}.`;
}

/** The rough gross premium, in words: every qualifying observation, whatever its credit. */
export function grossPremium(t: Thesis): string {
  const c = t.evidence.cohorts.candidates;
  if (c.count === 0 || c.mean_vol_gap === null) {
    return "No qualifying observation has completed, so there is no premium to report yet.";
  }
  const side = c.mean_vol_gap < 0 ? "below" : "above";
  const size = c.count === 1 ? points(c.mean_vol_gap) : `an average of ${points(c.mean_vol_gap)}`;
  return `Across ${completed(c.count)}, with any credit conditions, market-priced volatility was `
    + `${size} volatility points ${side} the volatility that followed.${median(c)}`;
}

/** The variance premium's mean and median, for the same observations. */
function inVariance(c: ThesisCohort): string {
  if (c.mean_premium === null || c.median_premium === null) return "";
  return `In variance units the mean was ${variance(c.mean_premium)} and the median `
    + `${variance(c.median_premium)}, over 30 days.`;
}

function costSentence(t: Thesis): string {
  const { puts, calls, sample_session: day } = t.evidence.cost;
  return `On ${longDate(day)}'s closing quotes, opening and closing one option cost about `
    + `${pct(puts.base_share)} of a put's price and ${pct(calls.base_share)} of a call's, in the `
    + "bid–ask spread and fees.";
}

interface CostRow {
  name: string;
  leg: ThesisLegCost;
}

const COST_COLUMNS: readonly TableColumn<CostRow>[] = [
  { id: "name", header: "Option", sort: (r) => r.name, cell: (r) => r.name },
  { id: "n", header: "Quotes", num: true, sort: (r) => r.leg.legs, cell: (r) => count(r.leg.legs) },
  { id: "spread", header: "Median spread", num: true, sort: (r) => r.leg.median_spread_points,
    cell: (r) => `${level(r.leg.median_spread_points)} pts` },
  { id: "mid", header: "Median mid-price", num: true, sort: (r) => r.leg.median_mid_points,
    cell: (r) => `${level(r.leg.median_mid_points)} pts` },
  { id: "base", header: "Round trip, % of price", num: true, sort: (r) => r.leg.base_share,
    cell: (r) => pct(r.leg.base_share) },
  { id: "stressed", header: "Stressed", num: true, sort: (r) => r.leg.stressed_share,
    cell: (r) => pct(r.leg.stressed_share) },
];

function Assumptions({ thesis }: { thesis: Thesis }) {
  const { cost } = thesis.evidence;
  const rows: CostRow[] = [{ name: "Put", leg: cost.puts }, { name: "Call", leg: cost.calls }];
  return (
    <>
      <p>The table shows what one option&apos;s round trip cost on the sample day, and in a stressed
        case of {cost.stressed_spread_multiple} times the spread and {cost.stressed_fee_multiple}{" "}
        times the fees. Prices are in index points.</p>
      <DataTable label="Cost sample" rows={rows} columns={COST_COLUMNS} rowId={(r) => r.name} grow />
      <p>The table lists the assumptions behind it.</p>
      <KeyValue label="Cost assumptions" rows={[
        ["Quotes taken at the close of", longDate(cost.sample_session)],
        ["VIX that day", level(cost.sample_vix_points)],
        ["Options", `S&P 500 weeklies expiring ${longDate(cost.sample_expiry)}`],
        ["Which strikes", `those with an absolute delta from ${cost.absolute_delta_low} to `
          + String(cost.absolute_delta_high)],
        ["Fee per contract, each way", `$${cost.fee_per_contract_transaction_usd.toFixed(2)}`],
        ["Round trip", "one full bid–ask spread, plus two fees"],
      ]} />
      <p>
        These are one day&apos;s quotes, taken on a day VIX had spiked, and medians over the strikes
        quoted. They leave out margin, slippage and losses. The planning specification&apos;s
        four-option structure was {cost.spec_condor}. It is an assumption for the next phase, and
        nothing here validates it.
      </p>
    </>
  );
}

export function Cost({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="cost" title="Potential return and trading costs"
             intro={<>Two separate measurements: how far market-priced volatility stood above what
               followed, and what it costs to trade. Net strategy returns have not yet been
               estimated.</>}>
      <div className="th-pair th-wide">
        <Titled className="th-card" title="Gross premium observed">
          <p>{grossPremium(thesis)}</p>
          <p>{inVariance(thesis.evidence.cohorts.candidates)} This is evidence about the proposed
            opportunity: a gross economic premium, not tradable alpha.</p>
        </Titled>
        <Titled className="th-card" title="Cost to trade, illustrated">
          <p>{costSentence(thesis)}</p>
          <p>The percentage is of the option&apos;s mid-price, halfway between its bid and ask, for
            one option. A strategy with several options pays it on each. It is a limited quote
            sample.</p>
        </Titled>
      </div>
      <p>
        The two are in different units, volatility points and a share of an option&apos;s price, so
        one cannot be subtracted from the other to estimate a net return.
      </p>
      <Disclosure title="Cost assumptions and limitations" wide>
        <Assumptions thesis={thesis} />
      </Disclosure>
    </Section>
  );
}
