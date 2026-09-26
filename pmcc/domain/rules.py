"""Rule IDs as the spec writes them (`E-T1`, `G-3`, `X-S5`, …)."""

from __future__ import annotations

import re
from typing import final

_RULE_ID = re.compile(r"(?:E-[TLS]|G-|X-[SLE])[1-9]")


@final
class RuleId(str):
    """A well-formed rule ID. Whether the config defines it is checked there (INV-09)."""

    __slots__ = ()

    def __new__(cls, value: str) -> RuleId:
        if not _RULE_ID.fullmatch(value):
            raise ValueError(f"not a rule ID: {value!r}")
        return super().__new__(cls, value)
