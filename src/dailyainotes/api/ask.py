"""`POST /api/v1/ask`: Ask the notes, answered as server-sent events (`sources`, `text`
pieces, then `done`, or `error`)."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dailyainotes.api.deps import ask_deps
from dailyainotes.ask import AskDeps, RateLimitedError, ask, check_limits, hash_ip

router = APIRouter()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    # Topic slugs the visitor follows; all topics when empty.
    topics: list[str] = Field(default_factory=list, max_length=20)


@router.post("/ask", responses={429: {"description": "Over the day's question limit"}})
async def ask_the_notes(
    body: Question, request: Request, deps: Annotated[AskDeps, Depends(ask_deps)]
) -> StreamingResponse:
    # Behind Caddy, uvicorn takes the client address from X-Forwarded-For.
    ip_hash = hash_ip(request.client.host if request.client else "", request.app.state.ip_key)
    try:
        await check_limits(deps.engine, ip_hash, datetime.now(UTC).date())
    except RateLimitedError as error:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(error)) from error

    async def events() -> AsyncIterator[str]:
        async for kind, data in ask(deps, body.question, body.topics, ip_hash=ip_hash):
            yield f"event: {kind}\ndata: {json.dumps(data, default=str)}\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
