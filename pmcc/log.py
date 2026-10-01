"""structlog JSON logging: one event per line, to stderr and to `logs/{command}_{timestamp}.jsonl`.

A command calls `configure_logging` once at startup. Everything else logs through
`structlog.get_logger()` and never imports this module (ARCHITECTURE §15, DEC-80). `pmcc batch`'s
worker processes each call it too, with a `suffix`, so each writes its own file (P5-03).
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog


class _TeeLogger:
    """Writes each rendered event to stderr and appends it to the run's JSONL file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def msg(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Opened per event, so a crash never loses a buffered line; LF on every OS (DEC-58).
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(message + "\n")

    debug = info = warning = error = critical = exception = msg


def configure_logging(command: str, log_dir: Path = Path("logs"), *, suffix: str = "") -> Path:
    """Route structlog to stderr and a new JSONL file for this command,
    `{command}_{timestamp}{suffix}.jsonl`; return the file's path."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"{command}_{stamp}{suffix}.jsonl"
    structlog.contextvars.bind_contextvars(command=command)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=lambda *_args: _TeeLogger(path),
        cache_logger_on_first_use=False,
    )
    return path
