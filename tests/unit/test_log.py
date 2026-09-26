"""structlog JSON logging to stderr and `logs/{command}_{timestamp}.jsonl` (ARCHITECTURE §15)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import structlog

from pmcc.log import configure_logging


@pytest.fixture(autouse=True)
def reset_structlog() -> Iterator[None]:
    yield
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def _events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines()]


def test_log_writes_one_json_event_per_line_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("fetch", log_dir=tmp_path)
    structlog.get_logger().info("fetch.unit.start", symbol="NVDA", unit="2026-09-18_C")

    [event] = _events(capsys.readouterr().err)
    assert event["event"] == "fetch.unit.start"
    assert event["level"] == "info"
    assert event["symbol"] == "NVDA"
    assert event["unit"] == "2026-09-18_C"


def test_log_appends_the_same_events_to_a_jsonl_file_named_for_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = configure_logging("fetch", log_dir=tmp_path)
    log = structlog.get_logger()
    log.info("fetch.unit.start", symbol="NVDA")
    log.warning("fetch.ric.unanswered", ric="NVDAJ182611500.U^J26")

    assert path.parent == tmp_path
    assert path.name.startswith("fetch_")
    assert path.suffix == ".jsonl"
    assert _events(path.read_text(encoding="utf-8")) == _events(capsys.readouterr().err)


def test_log_file_uses_lf_line_endings(tmp_path: Path) -> None:
    path = configure_logging("fetch", log_dir=tmp_path)
    structlog.get_logger().info("fetch.unit.done")
    structlog.get_logger().info("fetch.unit.done")

    raw = path.read_bytes()
    assert b"\r\n" not in raw
    assert raw.count(b"\n") == 2


def test_log_creates_the_log_directory(tmp_path: Path) -> None:
    path = configure_logging("run", log_dir=tmp_path / "logs")
    structlog.get_logger().info("engine.gate.fired")
    assert path.is_file()


def test_log_stamps_every_event_with_the_command_and_a_utc_timestamp(tmp_path: Path) -> None:
    path = configure_logging("probe", log_dir=tmp_path)
    structlog.get_logger().info("probe.done")

    [event] = _events(path.read_text(encoding="utf-8"))
    assert event["command"] == "probe"
    assert event["timestamp"].endswith("Z")


def test_log_drops_debug_events(tmp_path: Path) -> None:
    path = configure_logging("fetch", log_dir=tmp_path)
    structlog.get_logger().debug("fetch.noise")
    assert not path.exists()


def test_log_renders_exceptions_as_text_inside_the_json_event(tmp_path: Path) -> None:
    path = configure_logging("fetch", log_dir=tmp_path)
    try:
        raise ValueError("boom")
    except ValueError:
        structlog.get_logger().exception("fetch.abort.outage")

    [event] = _events(path.read_text(encoding="utf-8"))
    assert "ValueError: boom" in event["exception"]
