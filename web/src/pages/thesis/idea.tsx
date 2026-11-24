// The thesis page's opening and its macro paragraph (UI-SPEC §6 › Thesis): the PO's copy (TD-30),
// which THESIS-SPEC §1 holds.
import { Section } from "./parts";

export const TITLE = "Selling expensive protection after market scares";

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
        I believe S&amp;P 500 options remain expensive relative to subsequent market movements after
        a volatility spike when market swings begin to ease and corporate credit conditions stay
        stable, creating opportunities to sell protection selectively after costs.
      </p>
      <p>
        Investors may continue paying heavily for protection after the initial scare has passed.
        This project looks for situations where that demand remains high while market conditions
        begin to settle. Corporate borrowing conditions help us judge whether the scare could become
        a deeper financial problem.
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
        The opportunity and the holding period are planning estimates, not measured results.
      </p>
    </section>
  );
}

export function Macro() {
  return (
    <Section id="macro" title="Macro conditions">
      <p>
        This idea depends on the market scare fading. Persistent inflation, unexpected Federal
        Reserve policy changes, or worsening corporate financing conditions could keep volatility
        elevated. A technology selloff could also spread into the broader market. In those
        situations, options that appear expensive may be pricing risks that subsequently
        materialize.
      </p>
    </Section>
  );
}
