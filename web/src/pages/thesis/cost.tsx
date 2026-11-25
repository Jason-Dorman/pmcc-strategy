// The thesis page's potential return and trading costs (UI-SPEC §6 › Thesis; PO, TD-07, TD-21,
// TD-30, TD-32, TD-33): the volatility gap observed, by version and counting view, and an
// estimated cost as a share of an option's mid-price, each with its unit, never netted.
import { KeyValue } from "../../components/cells";
import { longDate } from "../../components/charts/axis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { count, pct } from "../../format/number";
import { level } from "../../format/thesis";
import type { Thesis, ThesisLegCost } from "../../types/generated/thesis";
import { Disclosure, Section, Titled } from "./parts";
import { versionGap } from "./versions";

function costSentence(t: Thesis): string {
  const { puts, calls, sample_session: day } = t.evidence.cost;
  return "Using the sampled bid–ask quotes and assumed fees, we estimate a round-trip cost of about "
    + `${pct(puts.base_share)} of a put's mid-price and ${pct(calls.base_share)} of a call's. The `
    + `quotes are from the ${longDate(day)} close.`;
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
  { id: "base", header: "Estimated round trip, % of mid-price", num: true, sort: (r) => r.leg.base_share,
    cell: (r) => pct(r.leg.base_share) },
  { id: "stressed", header: "Stressed estimate", num: true, sort: (r) => r.leg.stressed_share,
    cell: (r) => pct(r.leg.stressed_share) },
];

function Assumptions({ thesis }: { thesis: Thesis }) {
  const { cost } = thesis.evidence;
  const rows: CostRow[] = [{ name: "Put", leg: cost.puts }, { name: "Call", leg: cost.calls }];
  return (
    <>
      <p>The table shows the round-trip cost we estimate for one option, using the sampled bid–ask
        quotes and assumed fees, and in a stressed case of {cost.stressed_spread_multiple} times the
        spread and {cost.stressed_fee_multiple} times the fees. Prices are in index points.</p>
      <DataTable label="Cost sample" rows={rows} columns={COST_COLUMNS} rowId={(r) => r.name} grow />
      <p>The table lists the assumptions behind it.</p>
      <KeyValue label="Cost assumptions" rows={[
        ["Quotes taken at the close of", longDate(cost.sample_session)],
        ["VIX that day", level(cost.sample_vix_points)],
        ["Options", `S&P 500 weeklies expiring ${longDate(cost.sample_expiry)}`],
        ["Which strikes", `those with an absolute delta from ${cost.absolute_delta_low} to `
          + String(cost.absolute_delta_high)],
        ["Fee per contract, each way", `$${cost.fee_per_contract_transaction_usd.toFixed(2)}`],
        ["Round trip, as assumed", "one full bid–ask spread, plus two fees"],
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
               followed, and an estimate of what trading could cost. Net strategy returns have not yet
               been estimated.</>}>
      <div className="th-pair th-wide">
        <Titled className="th-card" title="Observed volatility gap">
          <p>{versionGap(thesis, "A", "all")}</p>
          <p>{versionGap(thesis, "B", "all")}</p>
          <p className="th-caption">A gross economic premium, not tradable alpha. The spacing views,
            medians and variance statistics are under “Explore the spacing views, medians and
            observations” above.</p>
        </Titled>
        <Titled className="th-card" title="Estimated trading cost">
          <p>{costSentence(thesis)}</p>
          <p>The percentages refer to each option&apos;s mid-price, halfway between its bid and ask,
            for one option. A strategy with several options would pay on each. It is a limited quote
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
