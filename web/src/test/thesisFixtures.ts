// A small `thesis.json` (T4-01), shaped as the nightly run writes it and typed against the
// generated schema: fixtures, never market data. Four sessions before credit data, then a spike
// with an eligible candidate, one filtered out, and one whose outcome is pending.
import type {
  Thesis,
  ThesisCohort,
  ThesisEpisode,
  ThesisParameters,
  ThesisPoint,
} from "../types/generated/thesis";
import { SCHEMA_VERSION } from "../types/generated/version";

/** Long after any test runs, so the fixture is fresh unless a test says otherwise. */
export const FRESH = "2999-01-01T12:00:00-05:00";

function point(day: string, over: Partial<ThesisPoint> = {}): ThesisPoint {
  return {
    day,
    index_close: 6000,
    vix: 20,
    forecast_vol: 0.15,
    forecast_gap_vol: 0.05,
    rv_short: 0.12,
    rv_long: 0.16,
    realized_vol: 0.14,
    outcome: "MATURED",
    outcome_end: "2026-03-10",
    credit_bps: 300,
    credit_status: "STABLE",
    credit_observation_date: "2026-02-04",
    credit_change_short_bps: 5,
    credit_change_long_bps: -10,
    ...over,
  };
}

const NO_CREDIT: Partial<ThesisPoint> = {
  credit_bps: null, credit_status: "UNAVAILABLE", credit_observation_date: null,
  credit_change_short_bps: null, credit_change_long_bps: null,
};

export const SERIES: ThesisPoint[] = [
  point("2026-02-02", NO_CREDIT),
  point("2026-02-03", { ...NO_CREDIT, forecast_vol: null, forecast_gap_vol: null }),
  point("2026-02-04"),
  point("2026-02-05", { vix: 30, forecast_gap_vol: 0.15 }),
  point("2026-02-06", { credit_bps: 460, credit_status: "UNSTABLE" }),
  point("2026-02-09", { vix: 27.5, forecast_vol: 0.16, forecast_gap_vol: 0.115,
                        realized_vol: null, outcome: "PENDING", outcome_end: "2026-03-11" }),
];

function episode(shock: string, over: Partial<ThesisEpisode>): ThesisEpisode {
  return {
    episode_id: `v1.0:${shock}`,
    shock_day: shock,
    window_end: "2026-02-06",
    status: "CANDIDATE",
    candidate_day: null,
    eligibility: null,
    vix: null,
    credit_bps: null,
    credit_change_short_bps: null,
    credit_change_long_bps: null,
    outcome: null,
    outcome_end: null,
    realized_vol: null,
    premium: null,
    note: "",
    ...over,
  };
}

export const EPISODES: ThesisEpisode[] = [
  episode("2026-02-02", { candidate_day: "2026-02-02", eligibility: "CREDIT_UNAVAILABLE", vix: 20,
                          outcome: "MATURED", outcome_end: "2026-03-10", realized_vol: 0.14,
                          premium: 0.0012, window_end: "2026-02-03" }),
  episode("2026-02-04", { candidate_day: "2026-02-04", eligibility: "ELIGIBLE", vix: 20,
                          credit_bps: 300, outcome: "MATURED", outcome_end: "2026-03-10",
                          realized_vol: 0.14, premium: 0.0019 }),
  episode("2026-02-05", { candidate_day: "2026-02-06", eligibility: "FILTERED_OUT", vix: 20,
                          credit_bps: 460, outcome: "PENDING", outcome_end: "2026-03-11" }),
  episode("2026-02-09", { status: "SEARCHING", window_end: "2026-02-24",
                          note: "the window runs past the data at 2026-02-10" }),
];

function cohort(name: string, count: number, share: number | null): ThesisCohort {
  const some = count > 0;
  return {
    name,
    count,
    first_day: some ? "2026-02-02" : null,
    last_day: some ? "2026-02-06" : null,
    mean_premium: some ? 0.0019 : null,
    median_premium: some ? 0.0018 : null,
    mean_vol_gap: some ? 0.076 : null,
    median_vol_gap: some ? 0.082 : null,
    mean_start_vix: some ? 19.25 : null,
    mean_overstatement: share,
  };
}

export const PARAMETERS: ThesisParameters = {
  history_start: "2015-01-01",
  decision_time_et: "20:30",
  horizon_calendar_days: 30,
  ewma_lambda: 0.94,
  initialization_sessions: 60,
  signal_warmup_sessions: 252,
  percentile_lookback_sessions: 252,
  percentile_threshold: 0.8,
  ratio_lookback_sessions: 5,
  minimum_vix_ratio: 1.25,
  search_sessions_after_shock: 10,
  short_rv_sessions: 5,
  long_rv_sessions: 20,
  falling_rv_comparison_sessions: 3,
  minimum_forecast_gap: 0.03,
  credit_maximum_level_bps: 450,
  credit_maximum_change_short_bps: 15,
  credit_maximum_change_long_bps: 40,
  credit_publication_lag_business_days: 2,
  credit_publication_time_et: "20:30",
  credit_maximum_age_business_days: 3,
};

const NOT_EVALUATED = "Not yet evaluated — requires strategy backtesting";

export const THESIS: Thesis = {
  schema_version: SCHEMA_VERSION,
  strategy_id: "conditional_volatility_premium",
  model_version: "v1.0",
  config_hash: "a".repeat(64),
  generated_at: "2026-02-09T23:17:00-05:00",
  data_through: "2026-02-09",
  expected_by: FRESH,
  run_status: "OK",
  data_status: "CURRENT",
  thesis_status: "PROVISIONAL",
  evidence_status: "INSUFFICIENT_EVIDENCE",
  signal: {
    day: "2026-02-09", status: "SEARCHING", assessment: "OK", episode_id: "v1.0:2026-02-09",
    shock_day: "2026-02-09", candidate_day: null, window_end: "2026-02-24", reason: "",
  },
  current: {
    day: "2026-02-09",
    vix: 27.5,
    shock_level: 19.91,
    vix_share_at_or_below: 1,
    vix_ratio: 1.86,
    forecast_vol: 0.16,
    forecast_gap_vol: 0.115,
    rv_short: 0.342,
    rv_long: 0.27,
    credit_status: "UNSTABLE",
    credit_bps: 347,
    credit_observation_date: "2026-02-05",
    credit_available_at: "2026-02-09T20:30:00-05:00",
    credit_change_short_bps: 17,
    credit_change_long_bps: 20,
    credit_note: "",
  },
  parameters: PARAMETERS,
  sources: [
    { series: "vix", provider: "LSEG", identifier: ".VIX", first: "2014-01-02", last: "2026-02-09",
      observations: 3000, units: "VIX points", note: "Cboe VIX, daily close" },
  ],
  evidence: {
    cohorts: {
      all_sessions: cohort("all matured sessions", 3222, 0.195),
      candidates: cohort("all candidates", 19, 0.226),
      stable: cohort("stable credit", 5, 0.388),
      unstable: cohort("unstable credit", 0, null),
      credit_unavailable: cohort("credit unavailable", 12, 0.272),
    },
    statements: ["The average premium was positive in the 5 available stable-credit episodes.",
                 "Credit-regime comparison unavailable in this sample.",
                 "A sample this small does not establish a reliable edge."],
    validation_target_per_cohort: 20,
    conditions: [
      { condition_id: "K1", name: "Priced risk is not excessive",
        formula: "mean realized_variance_premium over the latest 30 episodes",
        threshold: "wrong if <= 0", minimum_sample: "30 matured selected episodes",
        status: "INSUFFICIENT_DATA", value: 0.0019, sample: 5, assessed_on: "2026-02-09",
        note: "A current rolling assessment." },
      { condition_id: "K2", name: "Edge does not survive costs", formula: "mean net return",
        threshold: "wrong if <= 0", minimum_sample: "30 resolved trades",
        status: "NOT_EVALUATED", value: null, sample: null, assessed_on: null,
        note: NOT_EVALUATED },
    ],
    cost: {
      sample_session: "2026-02-09",
      sample_expiry: "2026-03-13",
      sample_vix_points: 27.5,
      absolute_delta_low: 0.1,
      absolute_delta_high: 0.3,
      fee_per_contract_transaction_usd: 2,
      stressed_spread_multiple: 1.5,
      stressed_fee_multiple: 2,
      puts: { legs: 20, median_spread_points: 9.65, median_mid_points: 106.225,
              median_spread_fraction_of_mid: 0.0971, base_share: 0.0975, stressed_share: 0.1464 },
      calls: { legs: 24, median_spread_points: 8.65, median_mid_points: 35.55,
               median_spread_fraction_of_mid: 0.1961, base_share: 0.1972, stressed_share: 0.2964 },
      spec_condor: "skipped on the sample day",
    },
  },
  episodes: EPISODES,
  series: SERIES,
};

/** The first night's file, before T4-01's fields: the export fills each as null. */
export const FIRST_NIGHT: Thesis = {
  ...THESIS,
  expected_by: null,
  parameters: null,
  current: THESIS.current && { ...THESIS.current, credit_available_at: null },
  episodes: EPISODES.map((e) => ({ ...e, outcome_end: null })),
  series: SERIES.map((s) => ({ ...s, outcome_end: null, credit_observation_date: null,
                               credit_change_short_bps: null, credit_change_long_bps: null })),
};
