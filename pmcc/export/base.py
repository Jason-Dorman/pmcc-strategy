"""What every result model shares: strict frozen models, exact dollars, JSON-scalar value maps and
the schema version (ARCHITECTURE §12).

Dollars are `Decimal` (exact $0.0001 units, DEC-44). Canonical JSON prints them to 4 dp as JSON
numbers, so their schema is a number, which is what the site's generated types read (INV-14).
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, WithJsonSchema

SCHEMA_VERSION = 6  # every file `pmcc export` publishes; the site refuses another (UI-SPEC §8)

_SCALAR_TYPES = (float, int, str, bool, type(None))
_JSON_SCALARS = ["number", "string", "boolean", "null"]


class Model(BaseModel):
    """A file as written: every field is always there, defaults included, so the schema marks
    them all required and the site's generated types have no optional fields."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, json_schema_serialization_defaults_required=True
    )


def _current(version: int) -> int:
    if version != SCHEMA_VERSION:
        raise ValueError(f"schema_version {version} isn't this build's {SCHEMA_VERSION}")
    return version


SchemaVersion = Annotated[
    int, AfterValidator(_current), WithJsonSchema({"type": "integer", "const": SCHEMA_VERSION})
]

Dollars = Annotated[Decimal, WithJsonSchema({"type": "number"})]


def _exact_scalars(values: Mapping[str, Any]) -> Mapping[str, Any]:
    """Refuses a value that isn't exactly a JSON scalar type: strict mode alone would read a
    `Decimal`, a numpy number or a numpy bool as a float."""
    for key, value in values.items():
        if type(value) not in _SCALAR_TYPES:
            raise ValueError(f"{key}: {type(value).__name__} isn't a JSON scalar: {value!r}")
    return values


# A blotter audit or gate-log value map.
ScalarMap = Annotated[
    Mapping[str, Any],
    AfterValidator(_exact_scalars),
    WithJsonSchema({"type": "object", "additionalProperties": {"type": _JSON_SCALARS}}),
]
