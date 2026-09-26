"""Import boundaries between packages (ARCHITECTURE §3.3), by AST scan of `pmcc/`.

Every import statement counts, including ones inside functions and `TYPE_CHECKING` blocks.
"""

import ast
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "pmcc"
LSEG_ADAPTER = "pmcc.data.lseg"

# (importer, imported) -> True when the import breaks the rule.
Rule = Callable[[str, str], bool]


def _within(name: str, *packages: str) -> bool:
    return any(name == p or name.startswith(p + ".") for p in packages)


def _top_package(module: str) -> str:
    return ".".join(module.split(".")[:2])


def _rule_1(importer: str, imported: str) -> bool:
    """`lseg` and `pandas` are imported only under `pmcc/data/lseg/`."""
    return _within(imported, "lseg", "pandas") and not _within(importer, LSEG_ADAPTER)


def _rule_2(importer: str, imported: str) -> bool:
    """`pmcc.data.lseg` is imported only by `pmcc.data.fetch` and `pmcc.cli`."""
    allowed = (LSEG_ADAPTER, "pmcc.data.fetch", "pmcc.cli")
    return _within(imported, LSEG_ADAPTER) and not _within(importer, *allowed)


def _rule_3(importer: str, imported: str) -> bool:
    """`pmcc.strategy` never imports `engine`, `data`, `accounting` or `export`."""
    banned = ("pmcc.engine", "pmcc.data", "pmcc.accounting", "pmcc.export")
    return _within(importer, "pmcc.strategy") and _within(imported, *banned)


def _rule_4(importer: str, imported: str) -> bool:
    """`pmcc.accounting` and `pmcc.pricing` import only `pmcc.domain` from this package."""
    own = _top_package(importer)
    return (
        _within(importer, "pmcc.accounting", "pmcc.pricing")
        and _within(imported, "pmcc")
        and not _within(imported, "pmcc.domain", own)
    )


def _rule_5(importer: str, imported: str) -> bool:
    """`pmcc.analytics` never imports `engine` or `data`."""
    return _within(importer, "pmcc.analytics") and _within(imported, "pmcc.engine", "pmcc.data")


def _rule_6(importer: str, imported: str) -> bool:
    """`pmcc.domain` imports nothing from `pmcc`. Nothing imports `pmcc.cli`."""
    domain_reaches_out = _within(importer, "pmcc.domain") and not _within(imported, "pmcc.domain")
    return (domain_reaches_out and _within(imported, "pmcc")) or _within(imported, "pmcc.cli")


def _rule_7(importer: str, imported: str) -> bool:
    """`pmcc.log` is imported only by `pmcc.cli`; everything else uses `structlog.get_logger()`."""
    return _within(imported, "pmcc.log") and not _within(importer, "pmcc.cli")


RULES: dict[int, Rule] = {
    1: _rule_1,
    2: _rule_2,
    3: _rule_3,
    4: _rule_4,
    5: _rule_5,
    6: _rule_6,
    7: _rule_7,
}


def _module_name(path: Path, root: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _base_for_relative(module: str, is_package: bool, level: int) -> str:
    package = module.split(".") if is_package else module.split(".")[:-1]
    return ".".join(package[: len(package) - (level - 1)])


def _imports(tree: ast.Module, module: str, is_package: bool) -> Iterator[str]:
    """Absolute names of everything `tree` imports; `from a import b` yields `a.b`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                prefix = _base_for_relative(module, is_package, node.level)
                base = f"{prefix}.{base}" if base else prefix
            yield from (base if a.name == "*" else f"{base}.{a.name}" for a in node.names)


def scan(package_dir: Path) -> dict[str, set[str]]:
    """Map each module under `package_dir` to the names it imports."""
    root = package_dir.parent
    graph: dict[str, set[str]] = {}
    for path in sorted(package_dir.rglob("*.py")):
        module = _module_name(path, root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        graph[module] = set(_imports(tree, module, path.name == "__init__.py"))
    return graph


def violations(package_dir: Path) -> list[str]:
    return [
        f"rule {number}: {importer} imports {imported}"
        for importer, imported_names in scan(package_dir).items()
        for imported in sorted(imported_names)
        for number, broken in RULES.items()
        if broken(importer, imported)
    ]


def test_imports_scan_sees_the_whole_package() -> None:
    assert {"pmcc", "pmcc.cli", "pmcc.domain", LSEG_ADAPTER} <= set(scan(PACKAGE_DIR))


def test_imports_pmcc_obeys_every_boundary_rule() -> None:
    assert violations(PACKAGE_DIR) == []


# One planted forbidden import per rule, plus the forms the scanner must see through.
PLANTED = [
    (1, "pmcc/engine/loop.py", "import pandas as pd\n"),
    (1, "pmcc/data/load.py", "from lseg.data import get_history\n"),
    (1, "pmcc/export/site.py", "def f() -> None:\n    import pandas\n"),
    (2, "pmcc/engine/loop.py", "from pmcc.data.lseg import provider\n"),
    (2, "pmcc/data/load.py", "from .lseg import provider\n"),
    (3, "pmcc/strategy/gates.py", "from pmcc.engine import loop\n"),
    (3, "pmcc/strategy/gates.py", "from pmcc import accounting\n"),
    (3, "pmcc/strategy/gates.py", "from ..data import load\n"),
    (
        3,
        "pmcc/strategy/gates.py",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from pmcc.export import models\n",
    ),
    (4, "pmcc/accounting/book.py", "from pmcc.config import models\n"),
    (4, "pmcc/pricing/iv.py", "import pmcc.strategy\n"),
    (5, "pmcc/analytics/performance.py", "from pmcc.engine.loop import run\n"),
    (5, "pmcc/analytics/performance.py", "from pmcc.data import load\n"),
    (6, "pmcc/domain/money.py", "from pmcc.config import models\n"),
    (6, "pmcc/engine/loop.py", "from pmcc.cli import app\n"),
    (7, "pmcc/data/fetch.py", "from pmcc.log import configure_logging\n"),
    (7, "pmcc/engine/loop.py", "from pmcc import log\n"),
]

ALLOWED = [
    "pmcc/data/lseg/provider.py",
    "pmcc/data/fetch.py",
    "pmcc/cli.py",
]


def _plant(tmp_path: Path, relative: str, source: str) -> Path:
    package_dir = tmp_path / "pmcc"
    for path in (package_dir / relative.removeprefix("pmcc/")).parents:
        if path == tmp_path:
            break
        path.mkdir(parents=True, exist_ok=True)
        (path / "__init__.py").touch()
    (package_dir / relative.removeprefix("pmcc/")).write_text(source, encoding="utf-8")
    return package_dir


@pytest.mark.parametrize(("rule", "relative", "source"), PLANTED)
def test_imports_planted_forbidden_import_is_caught(
    tmp_path: Path, rule: int, relative: str, source: str
) -> None:
    found = violations(_plant(tmp_path, relative, source))
    assert any(v.startswith(f"rule {rule}:") for v in found), found


@pytest.mark.parametrize("relative", ALLOWED)
def test_imports_lseg_adapter_is_allowed_where_the_rules_permit(
    tmp_path: Path, relative: str
) -> None:
    source = "from pmcc.data.lseg import provider\n"
    if relative.startswith("pmcc/data/lseg/"):
        source += "import pandas as pd\nimport lseg.data as ld\n"
    assert violations(_plant(tmp_path, relative, source)) == []


def test_imports_cli_may_configure_logging(tmp_path: Path) -> None:
    source = "from pmcc.log import configure_logging\n"
    assert violations(_plant(tmp_path, "pmcc/cli.py", source)) == []


def test_imports_domain_may_import_itself(tmp_path: Path) -> None:
    source = "from pmcc.domain.time import bar_end\nfrom .time import bar_end as b\n"
    assert violations(_plant(tmp_path, "pmcc/domain/money.py", source)) == []


def test_imports_pricing_may_import_its_own_package_and_domain(tmp_path: Path) -> None:
    source = "from pmcc.pricing.black_scholes import price\nfrom pmcc.domain import Price\n"
    assert violations(_plant(tmp_path, "pmcc/pricing/iv.py", source)) == []
