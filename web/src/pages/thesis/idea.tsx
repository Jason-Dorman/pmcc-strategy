// The thesis page's opening and its macro paragraph (UI-SPEC §6 › Thesis): the PO's copy (TD-30),
// which THESIS-SPEC §1 holds.
import { Section } from "./parts";

export const TITLE = "Selling expensive protection, selectively";

const HORIZONS: readonly (readonly [string, string])[] = [
  ["Expected opportunity", "Recurring over the next 12–24 months, reviewed quarterly."],
  ["Expected holding period", "Approximately 5–10 trading days."],
  ["Tracker window", "Compares volatility over the next 30 calendar days."],
];

export function Idea() {
  return (
    <section className="th-section th-hero" id="idea" aria-labelledby="idea-title" tabIndex={-1}>
      <p className="th-eyebrow">Volatility thesis · a hypothesis being investigated</p>
      <h1 className="th-h1" id="idea-title">{TITLE}</h1>
      <p className="th-thesis">
        I believe S&amp;P 500 options can offer opportunities to sell protection when implied
        volatility materially exceeds a forecast based on recent market movements and corporate
        credit conditions remain stable.
      </p>
      <p>
        We compare entering when those conditions are met with waiting until recent market swings
        also begin to ease.
      </p>
      <p>
        <b>Implied volatility</b> is the movement option prices imply. When it stands well above what
        recent markets suggest, protection may be expensive, or it may be pricing a risk still to
        come. Corporate borrowing conditions help us judge which.
      </p>
      <dl className="th-horizons th-wide">
        {HORIZONS.map(([name, text]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>{text}</dd>
          </div>
        ))}
      </dl>
      <p className="th-caption">
        The opportunity and the holding period are planning estimates, not measured results. The
        proposed holding period for a trade is shorter than the 30-calendar-day window the tracker
        observes.
      </p>
    </section>
  );
}

export function Macro() {
  return (
    <Section id="macro" title="Macro conditions">
      <p>
        This idea depends on markets moving less than options price in. Persistent inflation,
        unexpected Federal Reserve policy changes, or worsening corporate financing conditions could
        raise volatility or keep it elevated, whether or not a market scare came first. A technology
        selloff could also spread into the broader market. In those situations, options that appear
        expensive may be pricing risks that subsequently materialize.
      </p>
    </Section>
  );
}
