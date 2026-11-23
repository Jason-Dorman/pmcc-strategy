"""`thesis run`'s pull, build and write (T3-01): spec §14 test 14 (a fixture's inputs to its
episode, criteria and JSON) and test 13 (the schema, no NaN, no fixture data in the live file).
The inputs are the synthetic spike: fixtures, never market data."""

import json
import math
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pmcc.domain.clock import ET
from pmcc.export import canonical
from pmcc.export.thesis_models import Thesis
from pmcc.thesis.fred import FredKey, FredUnavailableError
from pmcc.thesis.probe import INDEX_RIC, VIX_RIC
from pmcc.thesis.run import THESIS_FILE, ThesisRunError, build, on_sessions, plan, pull, write
from tests.fakes.thesis_probe import ChainProvider
from tests.fakes.thesis_tracker import (
    CAL,
    CONFIG,
    SPIKE_CANDIDATE,
    SPIKE_DAYS,
    SPIKE_SHOCK,
    spike_fred_text,
    spike_index,
    spike_vix,
)

KEY = FredKey("0123456789abcdef0123456789abcdef")
LAST = SPIKE_DAYS[-1]
NOW = datetime(LAST.year, LAST.month, LAST.day, 22, 0, tzinfo=ET)
HOLIDAY = date(2014, 7, 4)  # NYSE closed; Cboe's VIX may still print (TD-18)
REPO = Path(__file__).resolve().parents[3]


def _no_wait(_seconds: float) -> None:
    pass


def _provider(closes: dict[str, dict[date, float]] | None = None) -> ChainProvider:
    served = closes if closes is not None else {INDEX_RIC: spike_index(), VIX_RIC: spike_vix()}
    return ChainProvider(CAL, served, LAST, LAST)


def _night(provider: ChainProvider | None = None, fred: str | None = None) -> Thesis:
    text = fred if fred is not None else spike_fred_text()
    inputs = pull(provider or _provider(), lambda _url: text, KEY, CAL, NOW, _no_wait)
    return build(inputs, CAL, CONFIG, NOW)


def test_f14_14_a_fixtures_inputs_give_its_episode_criteria_and_json() -> None:
    thesis = _night()

    (episode,) = thesis.episodes
    assert episode.shock_day == SPIKE_DAYS[SPIKE_SHOCK].isoformat()
    assert episode.candidate_day == SPIKE_DAYS[SPIKE_CANDIDATE].isoformat()
    assert (episode.status, episode.eligibility, episode.outcome) == (
        "CANDIDATE",
        "ELIGIBLE",
        "MATURED",
    )
    assert episode.credit_bps == pytest.approx(350.0)  # 3.50% is 350 bps
    assert len(thesis.series) == len(SPIKE_DAYS)
    assert thesis.data_through == LAST.isoformat()
    assert (thesis.data_status, thesis.signal.status, thesis.thesis_status) == (
        "CURRENT",
        "NO_SHOCK",
        "PROVISIONAL",
    )
    k1, k2, k3 = thesis.evidence.conditions
    assert (k1.status, k1.sample) == ("INSUFFICIENT_DATA", 1)
    assert (k2.status, k3.status) == ("NOT_EVALUATED", "NOT_EVALUATED")
    assert thesis.evidence.cohorts.stable.count == 1
    assert thesis.evidence_status == "INSUFFICIENT_EVIDENCE"
    assert thesis.config_hash == CONFIG.config_hash()
    assert [s.identifier for s in thesis.sources] == [INDEX_RIC, VIX_RIC, "BAMLH0A0HYM2"]


def test_f14_14_pending_outcomes_are_null_never_zero() -> None:
    last = _night().series[-1]
    assert (last.outcome, last.realized_vol) == ("PENDING", None)


def test_t3_01_the_file_is_canonical_json_and_reads_back_as_written(tmp_path: Path) -> None:
    thesis = _night()
    path = write(tmp_path, thesis)

    raw = path.read_bytes()
    assert path == tmp_path / THESIS_FILE
    assert canonical.to_bytes(canonical.loads(raw)) == raw
    read = Thesis.model_validate_json(raw)  # floats rounded to 6 places, as canonical JSON has
    assert canonical.to_bytes(read.model_dump(mode="json")) == raw
    assert read.data_through == thesis.data_through
    assert len(read.series) == len(thesis.series)
    assert b"NaN" not in raw
    assert b"Infinity" not in raw
    assert not path.with_suffix(".json.tmp").exists()


def test_f14_13_nan_and_infinity_are_refused_not_written() -> None:
    thesis = _night()
    raw = json.loads(canonical.to_bytes(thesis.model_dump(mode="json")))
    for bad in (math.nan, math.inf):
        raw["series"][0]["vix"] = bad
        with pytest.raises(ValidationError):
            Thesis.model_validate(raw)


def test_td_18_vix_on_a_closed_day_is_left_out_and_counted() -> None:
    vix = spike_vix() | {HOLIDAY: 14.0}
    thesis = _night(_provider({INDEX_RIC: spike_index(), VIX_RIC: vix}))

    assert HOLIDAY.isoformat() not in {p.day for p in thesis.series}
    assert "1 values on days NYSE was closed" in thesis.sources[1].note
    kept, dropped = on_sessions({HOLIDAY: 14.0, LAST: 15.0}, CAL)
    assert (kept, dropped) == ({LAST: 15.0}, 1)


def test_t3_01_lseg_without_vix_writes_nothing() -> None:
    with pytest.raises(ThesisRunError, match=r"\.VIX"):
        _night(_provider({INDEX_RIC: spike_index()}))


def test_t3_01_a_fred_answer_without_the_series_is_a_run_error() -> None:
    with pytest.raises(ThesisRunError, match="not JSON"):
        _night(fred="<html>maintenance</html>")
    with pytest.raises(ThesisRunError, match="no values"):
        _night(fred=json.dumps({"observations": []}))


def test_t3_01_fred_not_answering_is_an_outage() -> None:
    def down(_url: str) -> str:
        raise FredUnavailableError("FRED did not answer: TimeoutError")

    with pytest.raises(FredUnavailableError):
        pull(_provider(), down, KEY, CAL, NOW, _no_wait)


def test_t3_01_the_plan_names_its_two_requests() -> None:
    text = plan(NOW)
    assert INDEX_RIC in text
    assert "BAMLH0A0HYM2" in text


def test_f14_13_the_committed_file_is_the_real_tracker() -> None:
    path = REPO / THESIS_FILE
    if not path.is_file():
        pytest.skip("live/thesis/thesis.json isn't committed yet (T3-02's first run)")
    thesis = Thesis.model_validate_json(path.read_bytes())
    index = thesis.sources[0]
    assert (index.identifier, index.provider) == (INDEX_RIC, "LSEG")
    assert index.observations > 3000  # the history from 2014, not the 360-session fixture
    assert index.first == "2014-01-02"
