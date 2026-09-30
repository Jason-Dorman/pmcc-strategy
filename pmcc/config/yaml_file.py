"""Reading a config file: safe YAML that refuses a mapping key given twice (DEC-86).

`yaml.safe_load` keeps the last of two equal keys without a word, so a second `stock_ric:` in a
symbol's entry, or a second `closed:` list, would quietly replace the first.
"""

from collections.abc import Hashable
from pathlib import Path
from typing import Any, cast

import yaml
from yaml.nodes import MappingNode


class _StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Hashable, Any]:
        seen: set[Hashable] = set()
        for key_node, _ in node.value:
            # The stubs leave construct_object untyped; a mapping key is always hashable.
            key = cast(Hashable, self.construct_object(key_node, deep=deep))  # pyright: ignore[reportUnknownMemberType]
            if key in seen:
                raise ValueError(f"{key!r} is given more than once {key_node.start_mark}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def read_yaml(path: Path) -> object:
    """The file's content, as safe YAML with no key given twice in any mapping."""
    return parse_yaml(path.read_text(encoding="utf-8"))


def parse_yaml(text: str) -> object:
    """`text` as safe YAML with no key given twice in any mapping."""
    return yaml.load(text, Loader=_StrictLoader)
