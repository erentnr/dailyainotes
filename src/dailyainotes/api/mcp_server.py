"""The MCP server (ADR 0005): the published notes for AI assistants, at /api/mcp over Streamable
HTTP. Public and read-only, like the site's own pages; no tool calls a model. It lives in the
API because search needs the embedding model the API already holds for Ask."""

from datetime import UTC, date, datetime
from typing import Annotated, Any
from urllib.parse import urlsplit

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.streamable_http_manager import StreamableHTTPASGIApp
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.datastructures import State
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from dailyainotes.api.deps import load_models
from dailyainotes.api.notes import Citation
from dailyainotes.ask import hash_ip, is_strong
from dailyainotes.db import asks as asks_db
from dailyainotes.db import notes as notes_db
from dailyainotes.domain.editorial import without_markers
from dailyainotes.retrieval.hybrid import search_notes

PATH = "/api/mcp"
# Requests a day, each one counted: an assistant sends a few for every question.
PER_IP_PER_DAY = 300
PER_DAY = 3000
MAX_RESULTS = 10
SUMMARY_CHARS = 400

INSTRUCTIONS = """Daily AI Notes publishes short daily notes on a fixed set of topics. Every
sentence cites its sources inline as [1], [2]; every claim was fact-checked, and an editor
approved each note. Find notes with search_notes, read one with get_note, and give readers the
note's url. The notes say only what they cite; they are not complete coverage of a topic."""

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


class TopicInfo(BaseModel):
    slug: str
    name: str
    description: str
    notes: int


class NoteMatch(BaseModel):
    slug: str
    url: str
    topic: str
    date: date
    title: str
    summary: str


class NoteText(BaseModel):
    slug: str
    url: str
    topic: str
    topic_name: str
    date: date
    title: str
    # The note's text, with markers like [1] that point at its citations.
    body: str
    why_it_matters: str
    citations: list[Citation]
    # How the note's claims fared in the fact-check.
    supported: int
    weak: int
    unsupported: int


def build(state: State) -> MCPServer:
    """The server and its tools, over the API's engine and models."""
    site = state.settings.site_url.rstrip("/")
    server = MCPServer(
        name="dailyainotes",
        title="Daily AI Notes",
        instructions=INSTRUCTIONS,
        website_url=site,
    )

    def url(slug: str) -> str:
        return f"{site}/notes/{slug}"

    @server.tool(annotations=READ_ONLY)
    async def list_topics() -> list[TopicInfo]:
        """The topics Daily AI Notes covers, with how many notes each has."""
        topics = await notes_db.active_topics(state.engine)
        return [
            TopicInfo(slug=t.slug, name=t.name, description=t.description, notes=t.notes)
            for t in topics
        ]

    @server.tool(name="search_notes", annotations=READ_ONLY)
    async def search(  # not search_notes: that is the retrieval function it calls
        query: Annotated[str, Field(min_length=3, max_length=300)],
        topics: Annotated[list[str], Field(max_length=20)] | None = None,
        since: date | None = None,
        until: date | None = None,
        limit: Annotated[int, Field(ge=1, le=MAX_RESULTS)] = 5,
    ) -> list[NoteMatch]:
        """Published notes that answer the query, best first; empty when none does. `topics`
        takes topic slugs from list_topics; `since` and `until` limit the notes' days."""
        embeddings = load_models(state).embeddings
        hits = await search_notes(
            state.engine,
            embeddings,
            query,
            topic_slugs=topics or None,
            since=since,
            until=until,
            limit=2 * limit,
        )
        strong = [hit.note for hit in hits if is_strong(hit)][:limit]
        return [
            NoteMatch(
                slug=n.slug,
                url=url(n.slug),
                topic=n.topic,
                date=n.edition_date,
                title=n.title,
                summary=without_markers(n.text)[:SUMMARY_CHARS],
            )
            for n in strong
        ]

    @server.tool(annotations=READ_ONLY)
    async def get_note(slug: Annotated[str, Field(max_length=200)]) -> NoteText:
        """One published note with its citations: each a source's title, publisher, link and a
        quote of at most 25 words."""
        found = await notes_db.note_by_slug(state.engine, slug)
        if found is None:
            raise ToolError(f"No published note has the slug {slug!r}.")
        note, citations = found
        return NoteText(
            slug=note.slug,
            url=url(note.slug),
            topic=note.topic,
            topic_name=note.topic_name,
            date=note.edition_date,
            title=note.title,
            body=note.body,
            why_it_matters=note.why_it_matters,
            citations=[Citation(**vars(c)) for c in citations],
            supported=note.supported,
            weak=note.weak,
            unsupported=note.unsupported,
        )

    scheme, host = urlsplit(site).scheme, urlsplit(site).netloc
    server.streamable_http_app(
        streamable_http_path=PATH,
        # Each request stands alone and gets one JSON answer: nothing to keep between them,
        # and nothing for the tunnel to stream.
        stateless_http=True,
        json_response=True,
        # Guards against DNS rebinding: only the site's own host, or a local one in development.
        transport_security=TransportSecuritySettings(
            allowed_hosts=[host, "localhost:*", "127.0.0.1:*"],
            allowed_origins=[f"{scheme}://{host}", "http://localhost:*", "http://127.0.0.1:*"],
        ),
    )
    return server


class Endpoint:
    """The server's HTTP endpoint, with Ask's kind of daily limits per hashed IP and in all."""

    def __init__(self, state: State, server: MCPServer) -> None:
        self.state = state
        self.app = StreamableHTTPASGIApp(server.session_manager)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and await self.over_limit(scope):
            message = "Daily AI Notes has answered all it can for this connection today."
            await JSONResponse({"error": message}, status_code=429)(scope, receive, send)
            return
        await self.app(scope, receive, send)

    async def over_limit(self, scope: Scope) -> bool:
        engine, today = self.state.engine, datetime.now(UTC).date()
        # Behind Caddy, uvicorn takes the client address from X-Forwarded-For.
        client: Any = scope.get("client")
        ip_hash = hash_ip(client[0] if client else "", self.state.ip_key)
        if await asks_db.count_request(engine, f"mcp-ip:{ip_hash}", today) > PER_IP_PER_DAY:
            return True
        return await asks_db.count_request(engine, "mcp-all", today) > PER_DAY
