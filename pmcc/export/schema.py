"""JSON Schema for every file the site reads, generated from the result models (Spec › Frontend
constraints: typed results). `pmcc export` writes them to `schema/`, and the site's `gen:types`
turns them into TypeScript, so a model change the frontend doesn't handle fails `tsc` (INV-14).

`pmcc verify` validates with the same models, so a file that passes it matches its schema.
Schemas describe files as written (serialization mode): dollars are numbers, and a result's config
is its JSON dump.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pmcc.export.analytics_models import SYMBOL_FILES, UNIVERSE_FILES
from pmcc.export.models import RunResult
from pmcc.export.site_models import Index, Rules

SCHEMA_DIR = "schema"
SCHEMAS: Mapping[str, type[BaseModel]] = {
    "index": Index,
    "rules": Rules,
    "run_result": RunResult,
    **SYMBOL_FILES,
    **UNIVERSE_FILES,
}


def schema(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema(mode="serialization")


def write_schemas(out: Path) -> list[Path]:
    """`out/schema/{name}.schema.json` for each model: sorted keys, LF, one trailing newline."""
    folder = out / SCHEMA_DIR
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in SCHEMAS.items():
        path = folder / f"{name}.schema.json"
        text = json.dumps(schema(model), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        path.write_bytes(text.encode("utf-8"))
        written.append(path)
    return written
