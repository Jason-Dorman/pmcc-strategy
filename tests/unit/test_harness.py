"""The suite-wide guards in tests/conftest.py (TEST-STRATEGY §1)."""

import os
import socket

import pytest
from hypothesis import given
from hypothesis import strategies as st

PROFILE_EXAMPLES = {"dev": 50, "ci": 300}


def test_no_network_blocks_localhost_connect() -> None:
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
        pytest.raises(RuntimeError, match="network"),
    ):
        sock.connect(("127.0.0.1", 9000))


def test_no_network_blocks_create_connection() -> None:
    with pytest.raises(RuntimeError, match="network"):
        socket.create_connection(("example.com", 443))


def test_no_network_blocks_name_lookup() -> None:
    with pytest.raises(RuntimeError, match="network"):
        socket.getaddrinfo("example.com", 443)


def test_hypothesis_profile_sets_example_count_from_environment() -> None:
    seen: list[int] = []

    @given(st.integers())
    def record(value: int) -> None:
        seen.append(value)

    record()

    assert len(seen) == PROFILE_EXAMPLES[os.environ.get("HYPOTHESIS_PROFILE", "dev")]
