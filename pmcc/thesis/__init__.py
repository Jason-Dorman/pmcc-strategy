"""The volatility thesis's tracker (THESIS-SPEC §5; TD-03): pure functions on series in memory.

`run_tracker` is the entry point: daily index and VIX closes and a credit series in, the
per-session features, their matured outcomes, the shock episodes with their candidates, and the
credit state out. Nothing here asks LSEG or FRED, or reads or writes a data file.
"""
