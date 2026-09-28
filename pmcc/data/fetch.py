"""Batched history requests over any `HistoryProvider` (LDG §4.4, §5; DEC-45, DEC-49, DEC-83).

- `fetch_rics` asks in batches of 25. A RIC that doesn't come back with bars is asked again on
  its own, because only a single-RIC request says what happened to that RIC. A batch holding a
  failed RIC is rejected whole (or, for daily bars, answers without it), and a rejected batch's
  codes don't say which RIC got which.
- A RIC is unanswered only when the service says so, to that RIC alone: a no-data code, or no
  bars in the window. Any other failure is asked again, up to 3 attempts with backoff, and after
  that it is an outage.
- `fetch_contracts` asks each contract in the forms `forms_to_ask` gives it, in order: the next
  form is asked only for contracts the one before left unanswered. It records which form
  answered, and counts per contract, not per RIC.

Guess-and-check fails soft: a RIC nothing answered comes back as an empty series and a
`fetch.ric.unanswered` log event, never an exception (INV-12). An outage raises
`ProviderOutageError` and returns nothing, so nothing can be written from it (LDG §4.3). Unit
orchestration, the cache and resume come with P1-08.
"""

import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import final

import polars as pl
import structlog

from pmcc.data.provider import (
    HistoryProvider,
    Interval,
    NoDataError,
    ProviderOutageError,
    RawHistory,
    TransientError,
    UnreadableAnswerError,
)
from pmcc.data.ric import RicForm, build_ric, forms_to_ask, parse_ric
from pmcc.domain.instruments import OptionId

BATCH_SIZE = 25  # RICs per request (LDG §4.4)
ATTEMPTS = 3  # tries per request before a failure counts as an outage (DEC-49)

log = structlog.get_logger()


def backoff_seconds(attempt: int) -> float:
    """Seconds to wait after failed attempt `attempt` (1-based): 2, 4, 8, …"""
    return 2.0**attempt


@final
@dataclass(frozen=True, slots=True)
class Retry:
    """How failed requests are asked again. Tests pass a `sleep` that doesn't wait."""

    attempts: int = ATTEMPTS
    backoff: Callable[[int], float] = backoff_seconds
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError(f"a request needs at least 1 attempt, got {self.attempts}")


@final
@dataclass(frozen=True, slots=True)
class BarRequest:
    """The bars wanted for every RIC: these fields, from `start` up to `end_exclusive`."""

    fields: tuple[str, ...]
    start: date
    end_exclusive: date
    interval: Interval


class MissReason(StrEnum):
    """Why the service left a RIC unanswered. Nothing else ever does (DEC-49)."""

    NO_DATA = "no_data"  # a no-data code: never listed, or a field the RIC doesn't carry
    EMPTY = "empty"  # no bars in the window


@final
@dataclass(frozen=True, slots=True)
class Miss:
    """A RIC's verdict, from a request that asked for it alone."""

    reason: MissReason
    codes: tuple[str, ...]
    message: str


@final
@dataclass(frozen=True, slots=True)
class RequestError:
    """A rejected request, batch or single, kept for the sidecar's `errors` (LDG §5)."""

    rics: tuple[str, ...]
    error_class: str
    codes: tuple[str, ...]
    message: str


@final
@dataclass(frozen=True, slots=True)
class RicsResult:
    """What a set of RICs returned. `requested` is every RIC asked, once, in order.

    Every RIC asked is either answered or in `misses`, never both (LDG §5: the counts add up).
    """

    requested: tuple[str, ...]
    history: RawHistory
    misses: Mapping[str, Miss]
    errors: tuple[RequestError, ...]

    def __post_init__(self) -> None:
        answered, missed = self.history.rics(), frozenset(self.misses)
        if answered & missed or answered | missed != frozenset(self.requested):
            raise ValueError("every RIC asked must be answered or missed, and not both")

    @property
    def answered(self) -> frozenset[str]:
        return self.history.rics()

    @property
    def unanswered(self) -> tuple[str, ...]:
        return tuple(r for r in self.requested if r in self.misses)

    def series(self, ric: str) -> pl.DataFrame:
        """`ric`'s rows; empty, in the same schema, when it didn't answer (INV-12)."""
        return self.history.rows.filter(pl.col("ric") == ric)


@final
@dataclass(frozen=True, slots=True)
class ContractsResult:
    """What a set of contracts returned, each under the first of its forms that answered.

    `answered` maps a contract to the RIC that answered, `ric_form_used` maps that RIC to its
    form, and `unanswered` lists the contracts no form answered. `misses` holds every RIC asked
    that didn't answer, in any round; `requested` is every RIC asked.
    """

    history: RawHistory
    answered: Mapping[OptionId, str]
    ric_form_used: Mapping[str, RicForm]
    unanswered: tuple[OptionId, ...]
    misses: Mapping[str, Miss]
    requested: tuple[str, ...]
    errors: tuple[RequestError, ...]


def fetch_rics(
    provider: HistoryProvider,
    rics: Sequence[str],
    request: BarRequest,
    *,
    batch_size: int = BATCH_SIZE,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> RicsResult:
    """`request`'s bars for each of `rics`.

    Raises `ProviderOutageError` when LSEG stops answering, and `ValueError` for a batch size
    below 1.
    """
    unique = tuple(dict.fromkeys(rics))
    gathered = _Gathered()
    for batch in _batches(unique, batch_size):
        _fetch_batch(provider, batch, request, retry, gathered)
    frames = [frame.filter(pl.col("ric").is_in(unique)) for frame in gathered.frames]
    misses = {r: gathered.misses[r] for r in unique if r in gathered.misses}
    result = RicsResult(unique, _combine(frames, request.interval), misses, tuple(gathered.errors))
    for ric in result.unanswered:
        _log_unanswered(ric, result.misses[ric])
    return result


def fetch_contracts(
    provider: HistoryProvider,
    options: Sequence[OptionId],
    request: BarRequest,
    fetch_date: date,
    *,
    batch_size: int = BATCH_SIZE,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> ContractsResult:
    """`request`'s bars for each contract, asked form by form (DEC-45).

    Raises `ProviderOutageError` when LSEG stops answering, and `ValueError`, before anything is
    asked, for a batch size below 1 or a contract `build_ric` can't spell (a strike above $999.99).
    """
    forms = {o: forms_to_ask(o.expiry, fetch_date) for o in dict.fromkeys(options)}
    rounds = _Rounds()
    for turn in range(max((len(f) for f in forms.values()), default=0)):
        asking = {
            build_ric(o, f[turn]): (o, f[turn])
            for o, f in forms.items()
            if o not in rounds.answered and len(f) > turn
        }
        if not asking:
            break
        result = fetch_rics(provider, list(asking), request, batch_size=batch_size, retry=retry)
        rounds.add(result, asking)
    return ContractsResult(
        history=_combine(rounds.frames, request.interval),
        answered=rounds.answered,
        ric_form_used=rounds.ric_form_used,
        unanswered=tuple(o for o in forms if o not in rounds.answered),
        misses=rounds.misses,
        requested=tuple(rounds.requested),
        errors=tuple(rounds.errors),
    )


@dataclass
class _Gathered:
    """What `fetch_rics` has gathered so far."""

    frames: list[pl.DataFrame] = field(default_factory=list[pl.DataFrame])
    misses: dict[str, Miss] = field(default_factory=dict[str, Miss])
    errors: list[RequestError] = field(default_factory=list[RequestError])


@dataclass
class _Rounds:
    """What the form rounds of `fetch_contracts` have gathered so far."""

    frames: list[pl.DataFrame] = field(default_factory=list[pl.DataFrame])
    requested: list[str] = field(default_factory=list[str])
    errors: list[RequestError] = field(default_factory=list[RequestError])
    misses: dict[str, Miss] = field(default_factory=dict[str, Miss])
    answered: dict[OptionId, str] = field(default_factory=dict[OptionId, str])
    ric_form_used: dict[str, RicForm] = field(default_factory=dict[str, RicForm])

    def add(self, result: RicsResult, asking: Mapping[str, tuple[OptionId, RicForm]]) -> None:
        """One round's result; `asking` maps each RIC asked to its contract and form."""
        self.frames.append(result.history.rows)
        self.requested.extend(result.requested)
        self.errors.extend(result.errors)
        self.misses.update(result.misses)
        for ric in result.answered:
            option, form = asking[ric]
            self.answered[option] = ric
            self.ric_form_used[ric] = form


def _batches(rics: Sequence[str], size: int) -> Iterator[tuple[str, ...]]:
    if size < 1:
        raise ValueError(f"batch size must be at least 1, got {size}")
    for i in range(0, len(rics), size):
        yield tuple(rics[i : i + size])


def _fetch_batch(
    provider: HistoryProvider,
    batch: tuple[str, ...],
    request: BarRequest,
    retry: Retry,
    gathered: _Gathered,
) -> None:
    if len(batch) == 1:
        _settle(provider, batch[0], request, retry, gathered)
        return
    answer = _ask_batch(provider, batch, request, retry)
    if isinstance(answer, RawHistory):
        gathered.frames.append(answer.rows)
        left_out = [r for r in batch if r not in answer.rics()]
    else:
        error = _error(batch, answer)
        gathered.errors.append(error)
        log.warning(
            "fetch.batch.rejected",
            size=len(batch),
            error_class=error.error_class,
            message=error.message,
        )
        left_out = list(batch)
    for ric in left_out:
        _settle(provider, ric, request, retry, gathered)


def _settle(
    provider: HistoryProvider, ric: str, request: BarRequest, retry: Retry, gathered: _Gathered
) -> None:
    """Ask for `ric` alone: its bars, or the service's word that it has none."""
    answer = _ask_one(provider, ric, request, retry)
    if isinstance(answer, NoDataError):
        gathered.errors.append(_error((ric,), answer))
        gathered.misses[ric] = Miss(MissReason.NO_DATA, answer.codes, answer.message)
    elif ric in answer.rics():
        gathered.frames.append(answer.rows)
    else:
        gathered.misses[ric] = Miss(MissReason.EMPTY, (), "answered with no bars in the window")


def _ask_batch(
    provider: HistoryProvider, batch: Sequence[str], request: BarRequest, retry: Retry
) -> RawHistory | NoDataError | UnreadableAnswerError:
    """One request for several RICs. A rejection is returned, so the batch can be split."""

    def attempt() -> RawHistory | NoDataError | UnreadableAnswerError:
        try:
            return _history(provider, batch, request)
        except (NoDataError, UnreadableAnswerError) as exc:
            return exc

    return _retrying(attempt, retry, len(batch))


def _ask_one(
    provider: HistoryProvider, ric: str, request: BarRequest, retry: Retry
) -> RawHistory | NoDataError:
    """One request for one RIC. An unreadable answer can't be split further, so it is asked
    again like any other failure, and ends as an outage if it persists."""

    def attempt() -> RawHistory | NoDataError:
        try:
            return _history(provider, (ric,), request)
        except NoDataError as exc:
            return exc

    return _retrying(attempt, retry, 1)


def _history(provider: HistoryProvider, rics: Sequence[str], request: BarRequest) -> RawHistory:
    return provider.history(
        rics, request.fields, request.start, request.end_exclusive, request.interval
    )


def _retrying[T](attempt: Callable[[], T], retry: Retry, size: int) -> T:
    """`attempt()`, asked again on a transient or unreadable failure; then an outage."""
    last: TransientError | UnreadableAnswerError | None = None
    for n in range(1, retry.attempts + 1):
        try:
            return attempt()
        except (TransientError, UnreadableAnswerError) as exc:
            last = exc
            log.warning("fetch.retry", attempt=n, size=size, message=_describe(exc))
            if n < retry.attempts:
                retry.sleep(retry.backoff(n))
    raise ProviderOutageError(
        f"{retry.attempts} attempts in a row failed; last: {_describe(last)}"
    ) from last


def _describe(failure: TransientError | UnreadableAnswerError | None) -> str:
    if isinstance(failure, UnreadableAnswerError):
        return f"unreadable answer ({failure.error_class}: {failure.message})"
    return str(failure)


def _error(rics: Sequence[str], rejected: NoDataError | UnreadableAnswerError) -> RequestError:
    if isinstance(rejected, NoDataError):
        return RequestError(tuple(rics), "NoData", rejected.codes, rejected.message)
    return RequestError(tuple(rics), rejected.error_class, (), rejected.message)


def _combine(frames: Sequence[pl.DataFrame], interval: Interval) -> RawHistory:
    if not frames:
        return RawHistory.empty(interval)
    return RawHistory(interval, pl.concat(frames).sort("ric", "field", "bar_start"))


def _log_unanswered(ric: str, miss: Miss) -> None:
    log.warning(
        "fetch.ric.unanswered",
        ric=ric,
        form=_form_of(ric),
        reason=miss.reason.value,
        codes=list(miss.codes),
        message=miss.message,
    )


def _form_of(ric: str) -> str | None:
    """The form an option RIC is spelled in; `None` for any other RIC, such as a stock's."""
    try:
        return parse_ric(ric).form.value
    except ValueError:
        return None
