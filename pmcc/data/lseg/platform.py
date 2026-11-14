"""`platform_session()`: the headless LSEG session the live wheel uses (LD-05).

A platform session signs in with an app key, a username and a password, so it needs no Workspace:
the GitHub Action runs it with the repo's secrets, and the PO runs it locally with the same names
as environment variables (`LSEG_APP_KEY`, `LSEG_USERNAME`, `LSEG_PASSWORD`).

lseg-data 2.1.1's `Session.open()` doesn't raise when the sign-in fails: it closes the session and
returns Closed (its `_session.py`), the same trap as the desktop session (LDG §4.2). So the state
is checked before the caller gets a provider, and nothing is requested on a session that isn't
Opened. The credentials never show in a repr, an error or a log (LINV-09): an error raised while
building or opening the session is re-raised with every credential masked, as typed and in the
encodings an HTTP or JSON error could echo it in, and without its original as the cause, since
that would print the unmasked text.
"""

import json
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Protocol, final
from urllib.parse import quote, quote_plus

from pmcc.data.lseg.api import LsegApi
from pmcc.data.lseg.provider import LsegProvider
from pmcc.data.provider import ProviderOutageError

APP_KEY = "LSEG_APP_KEY"
USERNAME = "LSEG_USERNAME"
PASSWORD = "LSEG_PASSWORD"
ENV_NAMES = (APP_KEY, USERNAME, PASSWORD)
MASK = "***"

_NOT_OPEN_HELP = (
    "Check the app key, username and password (an EDP API app key, LD-05), and that the account "
    "isn't locked. Nothing was requested."
)


@final
@dataclass(frozen=True, slots=True)
class PlatformCredentials:
    """The three values a platform session signs in with. Never printed."""

    app_key: str = field(repr=False)
    username: str = field(repr=False)
    password: str = field(repr=False)

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "PlatformCredentials":
        """Read from the environment, as given: a password may hold spaces. A missing or blank
        variable raises, naming it alone."""
        missing = [name for name in ENV_NAMES if not environ.get(name, "").strip()]
        if missing:
            raise ProviderOutageError(
                f"{', '.join(missing)} not set: the platform session needs {', '.join(ENV_NAMES)} "
                "(GitHub secrets in Actions, environment variables locally). Nothing was requested."
            )
        return cls(*(environ[name] for name in ENV_NAMES))

    def __str__(self) -> str:
        return repr(self)

    def masked(self, text: str) -> str:
        """`text` with every credential replaced by `***`: as typed, URL-encoded (a form body or
        a query string) and JSON-escaped. Longest first, so no form leaves part of another."""
        forms = {
            form
            for value in (self.password, self.username, self.app_key)
            for form in (value, quote(value, safe=""), quote_plus(value), json.dumps(value)[1:-1])
            if form
        }
        for form in sorted(forms, key=len, reverse=True):
            text = text.replace(form, MASK)
        return text


class PlatformSession(Protocol):
    """The slice of an lseg-data platform session this adapter calls."""

    @property
    def open_state(self) -> object: ...

    def open(self) -> object: ...

    def close(self) -> object: ...


Opener = Callable[[PlatformCredentials], PlatformSession]


@contextmanager
def platform_session(
    credentials: PlatformCredentials, api: LsegApi | None = None, opener: Opener | None = None
) -> Generator[LsegProvider]:
    """A provider over an open platform session, closed on the way out whatever happens.

    Raises `ProviderOutageError` before any request when building the session raises, when
    opening it raises, or when it doesn't report Opened. `api` and `opener` are lseg-data's unless
    a test passes fakes; the opener makes the session lseg-data's default, which `api` then asks
    through.
    """
    try:
        api = api if api is not None else _lseg_data()
        session = (opener if opener is not None else _platform_opener)(credentials)
    except Exception as exc:
        raise _not_opened(exc, credentials) from None
    try:
        yield _open(api, session, credentials)
    finally:
        session.close()


def _open(api: LsegApi, session: PlatformSession, credentials: PlatformCredentials) -> LsegProvider:
    try:
        session.open()
    except Exception as exc:
        raise _not_opened(exc, credentials) from None
    provider = LsegProvider(api)
    if not provider.is_open():
        raise ProviderOutageError(
            f"the LSEG platform session did not open (state {session.open_state}). {_NOT_OPEN_HELP}"
        )
    return provider


def _not_opened(exc: Exception, credentials: PlatformCredentials) -> ProviderOutageError:
    described = credentials.masked(f"{type(exc).__name__}: {exc}")
    return ProviderOutageError(
        f"the LSEG platform session did not open: {described}. {_NOT_OPEN_HELP}"
    )


def _platform_opener(credentials: PlatformCredentials) -> PlatformSession:
    # Imported here, so importing pmcc never loads lseg-data; only opening a session does.
    import lseg.data as ld

    grant = ld.session.platform.GrantPassword(
        username=credentials.username, password=credentials.password
    )
    # signon_control: take the account's sign-on from another platform session, as the course's
    # nightly job does, so a session left open elsewhere can't fail the nightly run (LD-21).
    session = ld.session.platform.Definition(
        app_key=credentials.app_key, grant=grant, signon_control=True
    ).get_session()
    ld.session.set_default(session)
    return session


def _lseg_data() -> LsegApi:
    import lseg.data as ld

    return ld
