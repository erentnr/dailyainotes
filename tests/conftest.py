"""INTENT.md, Testing Requirements: unit tests never touch the network, and integration tests
reach only this machine (Postgres from `make up`).

The guard wraps Python sockets. libpq, which psycopg uses, connects from C and is not
guarded, so database access stays limited to tests marked `integration`.
"""

import hashlib
import math
import re
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest
from langchain_core.embeddings import Embeddings

from dailyainotes.domain.embedding import EMBEDDING_DIMENSIONS
from dailyainotes.sources.http import Http

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
FIXTURES = Path(__file__).parent / "fixtures"

# A recorded response: a body alone means 200, or (status, body, headers).
Recording = bytes | tuple[int, bytes, dict[str, str]]


class RecordedWeb:
    """Serves recorded responses by URL prefix through httpx2's MockTransport and remembers
    every request. Anything unrecorded gets a 404."""

    def __init__(self, routes: dict[str, Recording]) -> None:
        self.routes = routes
        self.requests: list[httpx2.Request] = []
        client = httpx2.AsyncClient(transport=httpx2.MockTransport(self._handle))
        self.http = Http(client, intervals={}, default_interval=0)

    def _handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        for prefix, recording in self.routes.items():
            if str(request.url).startswith(prefix):
                if isinstance(recording, bytes):
                    return httpx2.Response(200, content=recording)
                status, body, headers = recording
                return httpx2.Response(status, content=body, headers=headers)
        return httpx2.Response(404)


class WordHashEmbeddings(Embeddings):
    """A deterministic stand-in for the local model, which tests must not download: each word
    adds to one dimension, so texts that share words get close vectors."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"\w+", text.lower()) or ["empty"]:
            digest = hashlib.blake2b(word.encode(), digest_size=4).digest()
            vector[int.from_bytes(digest) % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector]


@pytest.fixture
def embeddings() -> Embeddings:
    return WordHashEmbeddings()


@pytest.fixture
def fixture() -> Callable[[str], bytes]:
    """`fixture("rss/feed.xml")` → the recorded bytes."""
    return lambda name: (FIXTURES / name).read_bytes()


@pytest.fixture
def web() -> Callable[[dict[str, Recording]], RecordedWeb]:
    return RecordedWeb


@pytest.fixture
def anyio_backend() -> str:
    """Async tests run on asyncio, the loop uvicorn and the worker use."""
    return "asyncio"


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
