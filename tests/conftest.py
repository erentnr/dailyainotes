"""INTENT.md, Testing Requirements: unit tests never touch the network, and integration tests
reach only this machine (Postgres from `make up`).

The guard wraps Python sockets. libpq, which psycopg uses, connects from C and is not
guarded, so database access stays limited to tests marked `integration`.
"""

import socket
from typing import Any

import pytest

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def network_guard(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    allow_local = request.node.get_closest_marker("integration") is not None

    def allowed(sock: socket.socket, address: Any) -> bool:
        if sock.family == socket.AF_UNIX:
            return True
        return allow_local and isinstance(address, tuple) and address[0] in LOCAL_HOSTS

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock: socket.socket, address: Any) -> None:
        if not allowed(sock, address):
            raise RuntimeError(f"network access in a test: {address!r}")
        real_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any) -> int:
        if not allowed(sock, address):
            raise RuntimeError(f"network access in a test: {address!r}")
        return real_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
