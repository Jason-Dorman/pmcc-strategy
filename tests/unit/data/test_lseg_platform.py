"""`platform_session`: the headless LSEG session the live wheel uses (LD-05).

It opens from the PO's credentials in the environment, with no Workspace. Like the desktop
session, a failed sign-in leaves it Closed rather than raising, so it is checked before anything
is requested. The credentials never show in an error, a repr or a log (LINV-09).
"""

import json
from collections.abc import Callable
from datetime import date
from urllib.parse import quote, quote_plus

import pytest

from pmcc.data.lseg import PlatformCredentials, platform_session
from pmcc.data.provider import Interval, ProviderOutageError
from tests.fakes.lseg import FakeLseg, FakePlatformSession, OpenState

ENV = {"LSEG_APP_KEY": "key-0123", "LSEG_USERNAME": "user@example.edu", "LSEG_PASSWORD": "s3cr3t!"}
RIC = "NVDA.O"


def _credentials() -> PlatformCredentials:
    return PlatformCredentials.from_env(ENV)


def _opener(
    fake: FakeLseg, made: list[PlatformCredentials]
) -> Callable[[PlatformCredentials], FakePlatformSession]:
    def open_with(credentials: PlatformCredentials) -> FakePlatformSession:
        made.append(credentials)
        return FakePlatformSession(fake)

    return open_with


def _ask(fake: FakeLseg, made: list[PlatformCredentials]) -> None:
    with platform_session(_credentials(), api=fake, opener=_opener(fake, made)) as provider:
        provider.history([RIC], ["TRDPRC_1"], date(2026, 9, 14), date(2026, 9, 15), Interval.HOURLY)


def _shows_no_credential(text: str) -> bool:
    return not any(value in text for value in ENV.values())


def test_ld_05_credentials_come_from_the_three_variables() -> None:
    credentials = _credentials()

    assert (credentials.app_key, credentials.username, credentials.password) == (
        ENV["LSEG_APP_KEY"],
        ENV["LSEG_USERNAME"],
        ENV["LSEG_PASSWORD"],
    )


@pytest.mark.parametrize("missing", sorted(ENV))
def test_ld_05_a_missing_variable_is_named_without_the_others_values(missing: str) -> None:
    env = {name: value for name, value in ENV.items() if name != missing}

    with pytest.raises(ProviderOutageError, match=missing) as raised:
        PlatformCredentials.from_env(env)

    assert _shows_no_credential(str(raised.value))


def test_ld_05_a_blank_variable_counts_as_missing() -> None:
    with pytest.raises(ProviderOutageError, match="LSEG_PASSWORD"):
        PlatformCredentials.from_env({**ENV, "LSEG_PASSWORD": "  "})


def test_linv_09_credentials_never_show_in_their_repr_or_str() -> None:
    credentials = _credentials()

    assert _shows_no_credential(repr(credentials))
    assert _shows_no_credential(str(credentials))


def test_ld_05_platform_session_asks_through_an_open_session_and_closes_it() -> None:
    fake = FakeLseg(listed={RIC: {"TRDPRC_1": [1.0, 2.0, 3.0]}})
    made: list[PlatformCredentials] = []

    _ask(fake, made)

    assert made == [_credentials()]
    assert [r.session_open for r in fake.requests] == [True]
    assert fake.state is OpenState.Closed
    assert fake.closes == 1


@pytest.mark.parametrize("left", [OpenState.Closed, OpenState.Pending])
def test_ld_05_a_session_that_does_not_open_raises_before_any_request(left: OpenState) -> None:
    fake = FakeLseg(opens_to=left)

    with pytest.raises(ProviderOutageError, match="did not open"):
        _ask(fake, [])

    assert fake.requests == []
    assert fake.closes == 1


def test_ld_05_the_session_closes_when_the_work_inside_fails() -> None:
    fake = FakeLseg()

    with (
        pytest.raises(RuntimeError, match="inside"),
        platform_session(_credentials(), api=fake, opener=_opener(fake, [])),
    ):
        raise RuntimeError("inside")

    assert fake.closes == 1


def test_linv_09_an_error_opening_never_shows_the_credentials() -> None:
    leaked = f"invalid_grant for {ENV['LSEG_USERNAME']} with {ENV['LSEG_PASSWORD']}"
    fake = FakeLseg(open_error=RuntimeError(leaked))

    with pytest.raises(ProviderOutageError, match="did not open") as raised:
        _ask(fake, [])

    assert _shows_no_credential(str(raised.value))
    assert "invalid_grant" in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    assert fake.closes == 1


def test_ld_05_credentials_are_read_as_given_spaces_and_all() -> None:
    credentials = PlatformCredentials.from_env({**ENV, "LSEG_PASSWORD": " pass word "})

    assert credentials.password == " pass word "


def test_linv_09_masking_covers_url_encoded_and_json_escaped_forms() -> None:
    password = 'p@ss&wo"rd 1'
    credentials = PlatformCredentials.from_env({**ENV, "LSEG_PASSWORD": password})
    echoed = (
        f"body: password={quote_plus(password)}; query: p={quote(password, safe='')}; "
        f"json: {json.dumps({'password': password})}; raw: {password}"
    )

    masked = credentials.masked(echoed)

    for form in (password, quote_plus(password), quote(password, safe=""), json.dumps(password)):
        assert form.strip('"') not in masked
    assert masked.count("***") == 4


def test_linv_09_an_error_building_the_session_is_masked_and_nothing_is_asked() -> None:
    fake = FakeLseg()

    def broken(credentials: PlatformCredentials) -> FakePlatformSession:
        raise ValueError(f"bad app key {credentials.app_key} for {credentials.username}")

    with (
        pytest.raises(ProviderOutageError, match="did not open") as raised,
        platform_session(_credentials(), api=fake, opener=broken),
    ):
        pytest.fail("the body ran")

    assert _shows_no_credential(str(raised.value))
    assert raised.value.__cause__ is None
    assert fake.requests == []
    assert fake.closes == 0
