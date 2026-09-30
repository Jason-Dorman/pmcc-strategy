"""Errors that stop a run (DEC-49): the engine never writes a result it can't stand behind."""


class EngineError(Exception):
    """A state the rules guarantee can't happen: a look-ahead read, an uncovered short, a quantity
    mismatch. The run stops and writes nothing (DEC-49)."""
