"""`configs/thesis.yaml`: the spec's §13 values, loaded strictly (THESIS-SPEC §13)."""

from datetime import date, time
from pathlib import Path

import pytest

from pmcc.thesis.config import THESIS_PATH, ThesisConfigError, load_thesis_config

CONFIG_TEXT = THESIS_PATH.read_text(encoding="utf-8")


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "thesis.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_config_holds_section_13s_values() -> None:
    config = load_thesis_config()
    assert (config.strategy_id, config.model_version) == ("conditional_volatility_premium", "v1.0")
    assert config.history_start_day == date(2015, 1, 1)
    assert config.decision_time == time(20, 30)
    f, s, n, c = config.forecast, config.shock, config.normalization, config.credit
    assert (f.horizon_calendar_days, f.ewma_lambda, f.initialization_sessions) == (30, 0.94, 60)
    assert f.signal_warmup_sessions == 252
    assert (s.percentile_lookback_sessions, s.percentile_threshold) == (252, 0.80)
    assert (s.ratio_lookback_sessions, s.minimum_vix_ratio, s.search_sessions_after_shock) == (
        5,
        1.25,
        10,
    )
    assert (n.short_rv_sessions, n.long_rv_sessions, n.falling_rv_comparison_sessions) == (5, 20, 3)
    assert n.minimum_forecast_gap_decimal == 0.03
    assert (c.maximum_level_bps, c.maximum_change_5_observations_bps) == (450, 15)
    assert c.maximum_change_20_observations_bps == 40
    assert (c.assumed_publication_lag_business_days, c.maximum_age_business_days) == (2, 3)
    assert c.publication_time == time(20, 30)
    assert config.evidence.kill_window_selected_events == 30


def test_config_refuses_an_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(ThesisConfigError, match="tuned"):
        load_thesis_config(_write(tmp_path, CONFIG_TEXT + "tuned: true\n"))


def test_config_refuses_a_missing_key(tmp_path: Path) -> None:
    text = CONFIG_TEXT.replace("  ewma_lambda: 0.94\n", "")
    with pytest.raises(ThesisConfigError, match="ewma_lambda"):
        load_thesis_config(_write(tmp_path, text))


def test_config_refuses_a_threshold_given_as_text(tmp_path: Path) -> None:
    text = CONFIG_TEXT.replace("maximum_level_bps: 450", "maximum_level_bps: '450'")
    with pytest.raises(ThesisConfigError, match="maximum_level_bps"):
        load_thesis_config(_write(tmp_path, text))


@pytest.mark.parametrize("bad", ["8:30", "20:30:00", "25:00", "noon"])
def test_config_refuses_a_decision_time_not_hh_mm(tmp_path: Path, bad: str) -> None:
    text = CONFIG_TEXT.replace("decision_time_et: '20:30'", f"decision_time_et: '{bad}'")
    with pytest.raises(ThesisConfigError, match="decision_time_et"):
        load_thesis_config(_write(tmp_path, text))


def test_config_refuses_short_rv_not_below_long(tmp_path: Path) -> None:
    text = CONFIG_TEXT.replace("short_rv_sessions: 5", "short_rv_sessions: 20")
    with pytest.raises(ThesisConfigError, match="short_rv_sessions"):
        load_thesis_config(_write(tmp_path, text))


def test_config_hash_is_stable_and_follows_every_value(tmp_path: Path) -> None:
    shipped = load_thesis_config()
    assert shipped.config_hash() == load_thesis_config().config_hash()
    assert len(shipped.config_hash()) == 64
    changed = load_thesis_config(
        _write(tmp_path, CONFIG_TEXT.replace("ewma_lambda: 0.94", "ewma_lambda: 0.95"))
    )
    assert changed.config_hash() != shipped.config_hash()
