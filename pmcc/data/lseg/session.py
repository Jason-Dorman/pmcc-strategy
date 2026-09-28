"""`lseg_session()`: open a Workspace desktop session, prove it opened, always close it.

`ld.open_session()` doesn't raise when the handshake fails. It leaves a closed session, and every
request after that looks like "no data" (LDG §4.2). So the session's state is checked before the
caller gets a provider, and nothing is requested on a session that isn't Opened.

The config is `lseg-data.config.json` at the repo root, found from this file rather than from the
working directory (ARCHITECTURE §6.1). lseg-data reads it; this code only passes its path.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pmcc.data.lseg.api import LsegApi
from pmcc.data.lseg.provider import LsegProvider
from pmcc.data.provider import ProviderOutageError

CONFIG_PATH = Path(__file__).resolve().parents[3] / "lseg-data.config.json"

_NOT_OPEN_HELP = (
    "Workspace must be running AND signed in (a quote loads in the app). If the proxy answers "
    "(curl -s http://localhost:9000/api/status) but the handshake hangs, restart Workspace "
    "completely (LDG §4.2). Nothing was requested."
)


@contextmanager
def lseg_session(api: LsegApi | None = None, config: Path = CONFIG_PATH) -> Generator[LsegProvider]:
    """A provider over an open session, closed on the way out whatever happens.

    Raises `ProviderOutageError` before any request when the config is missing, when opening raises,
    or when the session doesn't report Opened. `api` is the `lseg.data` module unless a test
    passes a fake.
    """
    if not config.is_file():
        raise ProviderOutageError(
            f"no LSEG config at {config}: copy lseg-data.config.json to the repo root. "
            "Nothing was requested."
        )
    api = api if api is not None else _lseg_data()
    try:
        yield _open(api, config)
    finally:
        api.close_session()


def _open(api: LsegApi, config: Path) -> LsegProvider:
    try:
        api.open_session(config_name=str(config))
    except Exception as exc:
        raise ProviderOutageError(
            f"the LSEG session did not open: {exc}. {_NOT_OPEN_HELP}"
        ) from exc
    provider = LsegProvider(api)
    if not provider.is_open():
        state = api.session.get_default().open_state
        raise ProviderOutageError(
            f"the LSEG session did not open (state {state}). {_NOT_OPEN_HELP}"
        )
    return provider


def _lseg_data() -> LsegApi:
    # Imported here, so importing pmcc never loads lseg-data; only opening a session does.
    import lseg.data as ld

    return ld
