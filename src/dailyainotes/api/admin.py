"""The /admin page's API: notes, topic plans and readers' topic suggestions waiting for the
editor, and the decision on each. Cloudflare Access signs the editor in before a request gets
here (ADR 0003)."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from dailyainotes.accounts import accept_suggestion, decline_suggestion
from dailyainotes.api.access import HEADER, AccessDeniedError, AccessVerifier
from dailyainotes.api.deps import story_deps
from dailyainotes.db import editorial as db
from dailyainotes.db import planner as planner_db
from dailyainotes.db import suggestions as suggestions_db
from dailyainotes.graphs.edition import NotAwaitingApprovalError, decide_note
from dailyainotes.graphs.planning import EmptyPlanError, NotProposedError, decide_plan, planner
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


class PlanSource(BaseModel):
    type: str
    locator: str
    recent_items: int
    # The share of recent items that name a keyword or an entity.
    match_share: float
    # The share of sampled pages a model may read; None for query sources.
    readable_share: float | None = None


class DroppedSource(BaseModel):
    # A site, feed or query the planner tried, and why the plan does not keep it.
    locator: str
    reason: str


class Plan(BaseModel):
    id: int
    topic: str
    name: str
    version: int
    created_at: datetime
    keywords: list[str]
    negative_keywords: list[str]
    entities: list[str]
    sources: list[PlanSource]
    dropped: list[DroppedSource]


class PlanDecision(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = ""


def plan_of(proposal: planner_db.Proposal) -> Plan:
    profile: dict[str, Any] = proposal.profile
    return Plan(
        id=proposal.id,
        topic=proposal.slug,
        name=proposal.name,
        version=proposal.version,
        created_at=proposal.created_at,
        keywords=profile["keywords"],
        negative_keywords=profile["negative_keywords"],
        entities=profile["entities"],
        sources=[PlanSource(**s) for s in profile["sources"]],
        # Plans made before the planner kept this record have none.
        dropped=[DroppedSource(**d) for d in profile.get("dropped", [])],
    )


@router.get("/plans")
async def plans(request: Request) -> list[Plan]:
    """Topic plans waiting for review."""
    proposals = await planner_db.proposals(request.app.state.engine, status="proposed")
    return [plan_of(p) for p in proposals]


@router.post(
    "/plans/{plan_id}/decision",
    responses={409: {"description": "Not waiting, or approving a plan without sources"}},
)
async def decide_on_plan(
    request: Request, plan_id: int, body: PlanDecision, email: Editor
) -> dict[str, str]:
    """Approving adds the plan's sources and makes the topic active."""
    engine = request.app.state.engine
    try:
        async with planner(request.app.state.settings, engine) as graph:
            await decide_plan(engine, graph, plan_id, body.decision, body.comment, by=email)
    except (NotProposedError, EmptyPlanError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return {"status": "approved" if body.decision == "approve" else "rejected"}


class WaitingSuggestion(BaseModel):
    id: int
    name: str
    note: str
    created_at: datetime


class SuggestionDecision(BaseModel):
    decision: Literal["accept", "decline"]
    # Shown to the reader when declining.
    reason: str = Field(default="", max_length=300)


@router.get("/suggestions")
async def waiting_suggestions(request: Request) -> list[WaitingSuggestion]:
    """Readers' topic suggestions waiting for a decision; who suggested them is not shown."""
    found = await suggestions_db.waiting(request.app.state.engine)
    return [WaitingSuggestion(**vars(s)) for s in found]


@router.post(
    "/suggestions/{suggestion_id}/decision", responses={409: {"description": "Not waiting"}}
)
async def decide_on_suggestion(
    request: Request, suggestion_id: int, body: SuggestionDecision, email: Editor
) -> dict[str, str]:
    """Accepting makes a draft topic and queues the Topic Planner; its plan then waits here."""
    engine = request.app.state.engine
    try:
        if body.decision == "accept":
            slug = await accept_suggestion(
                engine, suggestion_id, email, request.app.state.plan_queue
            )
            return {"status": "accepted", "topic": slug}
        await decline_suggestion(engine, suggestion_id, body.reason, email)
    except suggestions_db.NotOpenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return {"status": "declined"}
