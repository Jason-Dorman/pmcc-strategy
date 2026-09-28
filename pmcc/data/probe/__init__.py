"""The P1-04 probes: small LSEG requests that answer the spec's open items before a pull.

One report per symbol in `data_cache/probes/` (ARCHITECTURE §6.2, §6.4). The probes ask through
the `HistoryProvider` port; `pmcc.cli` hands them an LSEG session.
"""

from pmcc.data.probe.identifiers import ProbeStoppedError
from pmcc.data.probe.runner import probe_path, run_probe, write_report

__all__ = ["ProbeStoppedError", "probe_path", "run_probe", "write_report"]
