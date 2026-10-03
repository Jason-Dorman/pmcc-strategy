"""Rule text rendered from the params the engine uses (DEC-52), so the published rules can't drift.

A rule's `condition`, `action` and `rationale` are `str.format` templates whose placeholders are
bare param names with an optional format spec (`{max_delta:.2f}`, `{check_by:%H:%M}`). Attribute
and index lookups, conversions and positional fields are refused: a template names a param or
nothing. `{{` and `}}` are literal braces.
"""

import string
from collections.abc import Mapping, Sequence

_FORMATTER = string.Formatter()


def placeholders(template: str) -> frozenset[str]:
    """The param names `template` refers to. Raises `ValueError` for anything but a bare name."""
    names: set[str] = set()
    try:
        fields = [
            (f, spec, conv) for _, f, spec, conv in _FORMATTER.parse(template) if f is not None
        ]
    except ValueError as e:
        raise ValueError(f"unbalanced brace in {template!r}: {e}") from None
    for field, spec, conversion in fields:
        if not field.isidentifier() or conversion is not None or "{" in (spec or ""):
            raise ValueError(f"placeholder {{{field}}} in {template!r} must be a bare param name")
        names.add(field)
    return frozenset(names)


def render(template: str, values: Mapping[str, object]) -> str:
    """`template` with each placeholder formatted from `values`."""
    unknown = sorted(placeholders(template) - values.keys())
    if unknown:
        raise ValueError(f"unknown placeholder {unknown} in {template!r}")
    try:
        return template.format_map(values)
    except (ValueError, TypeError) as e:
        raise ValueError(f"can't render {template!r}: {e}") from None


def shown(templates: Sequence[str], values: Mapping[str, object]) -> dict[str, str]:
    """Each value as the first placeholder naming it formats it (`{max_ratio:.2f}` → "1.20"), or
    as `str` when none does: a threshold on the Trade rules page reads as the rule's text does."""
    specs: dict[str, str] = {}
    for template in templates:
        for _, field, spec, _ in _FORMATTER.parse(template):
            if field is not None:
                specs.setdefault(field, spec or "")
    return {name: format(value, specs.get(name, "")) for name, value in values.items()}
