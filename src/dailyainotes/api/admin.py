"""The minimal /admin page's API: the notes waiting for approval, and the decision on one.
Every request carries `Authorization: Bearer <ADMIN_TOKEN>`."""

import hmac
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from dailyainotes.api.deps import story_deps
from dailyainotes.db import editorial as db
from dailyainotes.graphs.edition import NotAwaitingApprovalError, decide_note
from dailyainotes.graphs.story import StoryDeps


def require_admin(request: Request) -> None:
    token = request.app.state.settings.admin_token
    if token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin is off: no ADMIN_TOKEN.")
    sent = request.headers.get("authorization", "").encode()
    if not hmac.compare_digest(sent, f"Bearer {token.get_secret_value()}".encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong or missing admin token.")


router = APIRouter(dependencies=[Depends(require_admin)])


class Citation(BaseModel):
    marker: int
    title: str
    url: str
    publisher: str


class Claim(BaseModel):
    text: str
    kind: str
    markers: list[int]
    verdict: str
    independent_origins: int
    rationale: str


class Review(BaseModel):
    id: int
    topic: str
    edition_date: date
    version: int
    title: str
    body: str
    why_it_matters: str
    citations: list[Citation]
    claims: list[Claim]


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = ""


@router.get("/notes")
async def waiting(request: Request) -> list[Review]:
    engine = request.app.state.engine
    reviews = []
    for note in await db.notes(engine, status="awaiting_approval"):
        text, citations, claims = await db.version_detail(engine, note.id, note.version)
        reviews.append(
            Review(
                id=note.id,
                topic=note.topic,
                edition_date=note.edition_date,
                version=note.version,
                title=text.title,
                body=text.body,
                why_it_matters=text.why_it_matters,
                citations=[Citation(**vars(c)) for c in citations],
                claims=[Claim(**vars(c)) for c in claims],
            )
        )
    return reviews


@router.post("/notes/{note_id}/decision", responses={409: {"description": "Not waiting"}})
async def decide(
    request: Request,
    note_id: int,
    body: Decision,
    deps: Annotated[StoryDeps, Depends(story_deps)],
) -> dict[str, str]:
    try:
        await decide_note(
            deps, request.app.state.settings.database_url, note_id, body.decision, body.comment
        )
    except NotAwaitingApprovalError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return {"status": "published" if body.decision == "approve" else "rejected"}
