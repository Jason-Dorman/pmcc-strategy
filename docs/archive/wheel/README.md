# Wheel docs (archived)

Archived 2026-11-13 (PO, [LD-01](../../DECISIONS.md#ld-01--wheel-docs-archived-the-live-assignments-docs)). These are the frozen docs of the wheel backtest, the second assignment. Its code, configs, results and site pages stay live and unchanged; these files remain their record, but they are **not** requirements for the live assignment. Its requirements are in [docs/LIVE-SPEC.md](../../LIVE-SPEC.md) and [docs/DECISIONS.md](../../DECISIONS.md) alone.

The wheel's code, configs and tests cite these files by short name. Read each citation against this folder:

| Citation in wheel code | File here |
| --- | --- |
| `docs/WHEEL-SPEC.md`, `Spec › …`, `WINV-01` … `WINV-10` | [WHEEL-SPEC.md](WHEEL-SPEC.md) |
| `WD-nn` | [DECISIONS.md](DECISIONS.md) |
| `W0-01` … `W5-02` | [BUILD-PLAN.md](BUILD-PLAN.md) |
| `UI-SPEC §6` (the Wheel and Wheel review pages), `§7` (their routes) | [UI-SPEC.md](UI-SPEC.md), a copy of the UI spec as it stood when the wheel finished |

The wheel's rule IDs (`W-T1`, `W-P3`, `W-C3`, …) are defined in its spec and in `configs/wheel.yaml`, which still runs in `just reproduce`.
