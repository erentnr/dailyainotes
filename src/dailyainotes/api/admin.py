"""The /admin page's API: the notes waiting for approval, and the decision on one. Cloudflare
Access signs the editor in before a request gets here (ADR 0003)."""

from datetime import date
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from dailyainotes.api.access import HEADER, AccessDeniedError, AccessVerifier
from dailyainotes.api.deps import story_deps
from dailyainotes.db import editorial as db
from dailyainotes.graphs.edition import NotAwaitingApprovalError, decide_note
from dailyainotes.graphs.story import StoryDeps

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
    email: Editor,
    deps: Annotated[StoryDeps, Depends(story_deps)],
) -> dict[str, str]:
    database_url = request.app.state.settings.database_url
    try:
        await decide_note(deps, database_url, note_id, body.decision, body.comment, by=email)
    except NotAwaitingApprovalError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return {"status": "published" if body.decision == "approve" else "rejected"}
