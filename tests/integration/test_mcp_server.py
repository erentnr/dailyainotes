from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from langchain_core.embeddings import Embeddings
from mcp import Client
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.api import mcp_server
from dailyainotes.api.app import create_app
from dailyainotes.api.deps import Models
from dailyainotes.ask import AskDeps
from dailyainotes.db.tables import Topic
from dailyainotes.evals import EVALS, CorpusNote, load_corpus, read_jsonl
from dailyainotes.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

# Ten fictional notes: climate tech (2026-09-02 to 09-30) and astronomy (09-03 to 10-01).
NOTES = read_jsonl(EVALS / "corpus.jsonl", CorpusNote)[:10]
BATTERY = "2026-09-02-brightwater-energy-starts-a-100-hour-iron-air-battery-pilot"
JSON_RPC = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
async def app(engine: AsyncEngine, embeddings: Embeddings) -> FastAPI:
    """The API over the ten notes, published and on active topics."""
    await load_corpus(engine, AskDeps(engine, embeddings, None), NOTES)  # type: ignore[arg-type]
    async with engine.begin() as connection:
        await connection.execute(update(Topic).values(status="active"))
    app = create_app(Settings(_env_file=None, site_url="http://test"))
    app.state.engine = engine  # ASGITransport does not run the lifespan
    app.state.models = Models(embeddings, None)  # type: ignore[arg-type]
    return app


@pytest.fixture
async def http(app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    transport = httpx2.ASGITransport(app=app)
    async with (
        app.state.mcp.session_manager.run(),  # the lifespan's job
        httpx2.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        yield client


def rpc(method: str, params: dict[str, Any], id_: int = 1) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params}


INITIALIZE = rpc(
    "initialize",
    {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
)


async def test_assistants_get_three_read_only_tools(app: FastAPI) -> None:
    async with Client(app.state.mcp) as client:
        tools = await client.list_tools()

    assert {t.name for t in tools.tools} == {"list_topics", "search_notes", "get_note"}
    assert all(t.annotations and t.annotations.read_only_hint for t in tools.tools)


async def test_topics_search_and_a_note_come_from_the_published_notes(app: FastAPI) -> None:
    async with Client(app.state.mcp) as client:
        topics = await client.call_tool("list_topics", {})
        found = await client.call_tool("search_notes", {"query": "iron-air battery pilot"})
        note = await client.call_tool("get_note", {"slug": BATTERY})

    slugs = [t["slug"] for t in topics.structured_content["result"]]  # type: ignore[index]
    assert slugs == ["astronomy-and-spaceflight", "climate-tech"]
    first = found.structured_content["result"][0]  # type: ignore[index]
    assert first["slug"] == BATTERY
    assert first["url"] == f"http://test/notes/{BATTERY}"
    assert "[1]" not in first["summary"]
    text = note.structured_content
    assert text is not None
    assert "[1]" in text["body"]
    # The eval corpus keeps no citation rows (as in test_api_notes); the note page's own
    # Citation model carries them here.
    assert text["citations"] == []
    assert (text["supported"], text["weak"], text["unsupported"]) == (0, 0, 0)


async def test_a_search_the_notes_do_not_cover_finds_nothing(app: FastAPI) -> None:
    async with Client(app.state.mcp) as client:
        found = await client.call_tool("search_notes", {"query": "zz qq xx yy"})

    assert found.structured_content == {"result": []}


async def test_an_unknown_note_is_a_tool_error(app: FastAPI) -> None:
    async with Client(app.state.mcp) as client:
        missing = await client.call_tool("get_note", {"slug": "no-such-note"})

    assert missing.is_error


async def test_the_endpoint_speaks_json_rpc_over_http(http: httpx2.AsyncClient) -> None:
    response = await http.post(mcp_server.PATH, json=INITIALIZE, headers=JSON_RPC)

    assert response.status_code == 200, response.text
    assert response.json()["result"]["serverInfo"]["name"] == "dailyainotes"


async def test_requests_past_the_daily_limit_per_connection_are_refused(
    http: httpx2.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp_server, "PER_IP_PER_DAY", 2)

    statuses = [
        (await http.post(mcp_server.PATH, json=INITIALIZE, headers=JSON_RPC)).status_code
        for _ in range(3)
    ]

    assert statuses == [200, 200, 429]


async def test_a_request_for_another_host_is_refused(http: httpx2.AsyncClient) -> None:
    """DNS rebinding: a page on another site must not reach the server through the browser."""
    response = await http.post(
        mcp_server.PATH, json=INITIALIZE, headers={**JSON_RPC, "Host": "evil.example"}
    )

    assert response.status_code in {400, 403, 421}
