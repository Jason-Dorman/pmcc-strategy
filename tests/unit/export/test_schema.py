"""The JSON Schemas `pmcc export` publishes (P4-05), from which the site generates its types
(INV-14). They describe files as written: dollars are numbers, and a result's config is its dump."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.config.strategy import Detail, Section
from pmcc.export.base import SCHEMA_VERSION
from pmcc.export.models import RunResult
from pmcc.export.schema import SCHEMAS, schema, write_schemas

type Schema = dict[str, Any]


def _defs(name: str) -> dict[str, Schema]:
    return cast(dict[str, Schema], schema(SCHEMAS[name])["$defs"])


def test_schema_every_file_the_site_reads_has_one() -> None:
    site = ["index", "rules", "run_result"]
    analytics = [
        "robustness",
        "fill_check",
        "coverage",
        "pooled",
        "headline",
        "pooled_fill_check",
        "suitability",
    ]

    assert sorted(SCHEMAS) == sorted(site + analytics)


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schema_pins_the_schema_version(name: str) -> None:
    written = schema(SCHEMAS[name])
    version = written["properties"]["schema_version"]

    assert (version["const"], version["type"]) == (SCHEMA_VERSION, "integer")
    assert "schema_version" in written["required"]


def test_schema_a_field_with_a_default_is_still_required_as_written() -> None:
    """Every file writes every field, so the site's types have no optional fields."""
    result, strategy = schema(RunResult), _defs("run_result")["StrategyConfig"]

    assert set(result["required"]) == set(result["properties"])
    assert "report" in strategy["required"]
    assert set(_defs("run_result")["Report"]["required"]) == {"detail", "sections"}


def test_schema_dollars_are_numbers() -> None:
    blotter = _defs("run_result")["BlotterRow"]["properties"]
    ledger = _defs("run_result")["LedgerRowOut"]["properties"]

    assert blotter["cash_delta"]["type"] == "number"
    assert {"type": "number"} in blotter["fill"]["anyOf"]
    assert ledger["nav"]["type"] == "number"
    assert schema(RunResult)["properties"]["starting_cash"]["type"] == "number"


def test_schema_a_results_config_is_its_json_dump() -> None:
    """Dollars in the config are "0.1000" strings, as its hash covers them (DEC-90)."""
    defs = _defs("run_result")

    assert schema(RunResult)["properties"]["config"] == {"$ref": "#/$defs/RunConfig"}
    fee = defs["FillModel"]["properties"]["fee_per_contract"]
    assert fee["type"] == "string"
    assert "report" in defs["StrategyConfig"]["properties"]


def test_dec_54_schema_names_the_detail_levels_and_sections() -> None:
    defs = _defs("run_result")

    assert defs["Detail"]["enum"] == [d.value for d in Detail]
    assert defs["Section"]["enum"] == [s.value for s in Section]


def test_schema_rows_are_nullable_for_a_summary_run() -> None:
    properties = schema(RunResult)["properties"]

    for rows in ("blotter", "ledger", "gate_log", "cycles", "attribution"):
        assert {"type": "null"} in properties[rows]["anyOf"]
    assert {"type": "null"} not in properties["summary"].get("anyOf", [])


def test_schema_files_are_written_with_sorted_keys_and_lf(tmp_path: Path) -> None:
    written = write_schemas(tmp_path)

    assert sorted(p.name for p in written) == sorted(f"{n}.schema.json" for n in SCHEMAS)
    for path in written:
        raw = path.read_bytes()
        assert raw.endswith(b"}\n")
        assert b"\r" not in raw
        assert raw == (json.dumps(json.loads(raw), indent=2, sort_keys=True,
                                  ensure_ascii=False) + "\n").encode()  # fmt: skip


def test_schema_files_are_the_same_bytes_every_time(tmp_path: Path) -> None:
    first = {p.name: p.read_bytes() for p in write_schemas(tmp_path / "a")}
    second = {p.name: p.read_bytes() for p in write_schemas(tmp_path / "b")}

    assert first == second
