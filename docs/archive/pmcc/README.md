# PMCC docs (archived)

Archived 2026-10-26 (PO, [WD-01](../../DECISIONS.md#wd-01--pmcc-docs-archived-styling-carried-over)). These are the frozen docs of the PMCC backtest, the first assignment. Its code, configs, results and site pages stay live and unchanged; these files remain their record, but they are **not** requirements for the wheel. The wheel's requirements are in [docs/WHEEL-SPEC.md](../../WHEEL-SPEC.md) and [docs/DECISIONS.md](../../DECISIONS.md) alone.

The PMCC's code and tests cite these files by short name. Read each citation against this folder:

| Citation in PMCC code | File here |
| --- | --- |
| `Spec › …` | [PMCC-Backtest-System-Spec.md](PMCC-Backtest-System-Spec.md) |
| `DEC-nn` | [DECISIONS.md](DECISIONS.md) |
| `ARCHITECTURE §n` | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `TEST-STRATEGY §n` | [TEST-STRATEGY.md](TEST-STRATEGY.md) |
| `UI-SPEC §n` | [UI-SPEC.md](UI-SPEC.md) |
| `P0-01` … `P8-04`, `L-01` … | [BUILD-PLAN.md](BUILD-PLAN.md) |
| `PRD FR-…` | [PRD.md](PRD.md) |

Two tests still read the spec here (`tests/unit/config/test_baseline_config.py`, `test_quant_config.py`). They check that the PMCC configs match its rule tables.
