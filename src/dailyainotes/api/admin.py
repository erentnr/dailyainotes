"""The /admin page's API: the latest published notes, and withdrawing one. Notes and topic
plans publish without a review (ADR 0008). Cloudflare Access signs the editor in before a
request gets here (ADR 0003)."""

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from dailyainotes.api.access import HEADER, AccessDeniedError, AccessVerifier
from dailyainotes.db import editorial as db

log = structlog.get_logger(__name__)


async def editor(request: Request) -> str:
    """The signed-in editor's email, from the token Cloudflare Access adds to the request."""
    verifier: AccessVerifier | None = request.app.state.access
    if verifier is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Admin is off: Cloudflare Access is not set up."
        )
    token = request.headers.get(HEADER)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in through Cloudflare Access.")
    try:
        return await verifier.email(token)
    except AccessDeniedError as error:
        log.warning("access_token_refused", reason=str(error))
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Sign in through Cloudflare Access."
        ) from error


Editor = Annotated[str, Depends(editor)]
router = APIRouter(dependencies=[Depends(editor)])


class SignedInEditor(BaseModel):
    email: str


@router.get("/me")
async def me(email: Editor) -> SignedInEditor:
    return SignedInEditor(email=email)


# How many of the latest published notes /admin lists.
RECENT = 60


class AdminNote(BaseModel):
    id: int
    slug: str
    topic: str
    edition_date: date
    title: str
    supported: int
    claims: int


@router.get("/notes")
async def published(request: Request) -> list[AdminNote]:
    """The latest published notes, newest first, so the editor can withdraw one."""
    notes = await db.notes(request.app.state.engine, status="published")
    return [
        AdminNote(
            id=n.id,
            slug=n.slug,
            topic=n.topic,
            edition_date=n.edition_date,
            title=n.title,
            supported=n.supported,
            claims=n.claims,
        )
        for n in reversed(notes[-RECENT:])
    ]


class Withdrawal(BaseModel):
    comment: str = ""


@router.post("/notes/{note_id}/withdraw", responses={409: {"description": "Not published"}})
async def withdraw(
    request: Request, note_id: int, body: Withdrawal, email: Editor
) -> dict[str, str]:
    """Take the note off the site, Ask and the MCP server, keeping who did it and why."""
    if not await db.withdraw(request.app.state.engine, note_id, body.comment, email):
        raise HTTPException(status.HTTP_409_CONFLICT, f"note-{note_id} is not published")
    return {"status": "withdrawn"}
