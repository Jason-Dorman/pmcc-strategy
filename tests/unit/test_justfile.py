"""The justfile's recipe surface (ARCHITECTURE §14, DEC-58)."""

import re
from pathlib import Path

JUSTFILE = Path(__file__).resolve().parents[2] / "justfile"

RECIPES = [
    "setup",
    "check",
    "test",
    "probe",
    "fetch",
    "run",
    "wheel",
    "wheels",
    "batch",
    "calibrate",
    "export",
    "verify",
    "web-dev",
    "web-build",
    "e2e",
    "serve",
    "reproduce",
]


def _recipe_names() -> set[str]:
    header = re.compile(r"^@?([a-z][a-z0-9-]*)\b[^:=]*:(?!=)")
    lines = JUSTFILE.read_text(encoding="utf-8").splitlines()
    return {m.group(1) for line in lines if (m := header.match(line))}


def test_justfile_runs_recipes_under_bash() -> None:
    assert 'set shell := ["bash", "-cu"]' in JUSTFILE.read_text(encoding="utf-8")


def test_justfile_defines_every_architecture_recipe() -> None:
    assert set(RECIPES) <= _recipe_names()


def test_w3_02_reproduce_runs_the_wheel_and_its_friction_runs_after_the_batch() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith("reproduce:"))
    assert line.split() == ["reproduce:", "batch", '(wheels', '"NVDA")', "verify", "export",
                            "web-build"]  # fmt: skip
