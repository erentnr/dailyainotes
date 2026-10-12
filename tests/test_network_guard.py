import socket

import pytest

# 192.0.2.1 is reserved for documentation (RFC 5737), so a leak would never reach a real host.
OUTSIDE = ("192.0.2.1", 80)


def test_a_unit_test_cannot_open_a_socket() -> None:
    with socket.socket() as sock, pytest.raises(RuntimeError, match="network access"):
        sock.connect(OUTSIDE)


@pytest.mark.integration
def test_an_integration_test_can_reach_this_machine_only() -> None:
    with socket.socket() as sock, pytest.raises(RuntimeError, match="network access"):
        sock.connect(OUTSIDE)
    with socket.socket() as sock:
        # Nothing listens on port 1: the connection is refused, not blocked by the guard.
        assert sock.connect_ex(("127.0.0.1", 1)) != 0
