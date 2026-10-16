"""Reader accounts' API (ADR 0003): sign-in with an emailed code or link, the session cookie,
the topics a reader follows, and deleting an account.

The session is a random token in an HttpOnly cookie, never readable by the site's scripts.
Requests that change an account must come from the site's own origin; with SameSite=Lax that
stops another site from acting on a reader's behalf."""

from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from dailyainotes.accounts import (
    AccountDeps,
    BotCheckFailedError,
    CodeUsedUpError,
    Followed,
    InvalidEmailError,
    InvalidTopicsError,
    Session,
    SignedIn,
    SignInOffError,
    TooManyCodesError,
    TooManySuggestionsError,
    WrongCodeError,
    delete_account,
    follow,
    followed,
    send_code,
    sign_in_with_code,
    sign_in_with_link,
    sign_out,
    signed_in,
    suggest,
    suggestions,
)
from dailyainotes.ask import hash_ip
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.accounts import MAX_TOPICS
from dailyainotes.external.resend import EmailNotSentError, ResendMailer
from dailyainotes.external.turnstile import TurnstileCheck
from dailyainotes.settings import Settings

COOKIE = "dan_session"

router = APIRouter()


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def account_deps(settings: Settings, engine: AsyncEngine, client: Any) -> AccountDeps:
    """Sign-in is off without a Resend key; the form has no bot check without Turnstile's."""
    site_url = settings.site_url.rstrip("/")
    key, secret = settings.resend_api_key, settings.turnstile_secret_key
    return AccountDeps(
        engine,
        ResendMailer(client, key.get_secret_value(), settings.email_from) if key else None,
        TurnstileCheck(client, secret.get_secret_value(), urlsplit(site_url).hostname or "")
        if secret
        else None,
        site_url,
    )


def accounts(request: Request) -> AccountDeps:
    deps: AccountDeps = request.app.state.accounts
    return deps


Deps = Annotated[AccountDeps, Depends(accounts)]


def same_origin(request: Request, deps: Deps) -> None:
    if request.headers.get("origin") != origin_of(deps.site_url):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Changes to an account must come from this site."
        )


async def reader(request: Request, response: Response, deps: Deps) -> SignedIn | None:
    """The signed-in reader, or None; renews the cookie when the session was renewed."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    found = await signed_in(deps.engine, token, datetime.now(UTC))
    if found is not None and found.renewed_until is not None:
        set_cookie(response, deps, token, found.renewed_until)
    return found


async def required_reader(found: Annotated[SignedIn | None, Depends(reader)]) -> SignedIn:
    if found is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in first.")
    return found


Reader = Annotated[SignedIn, Depends(required_reader)]
SameOrigin = Depends(same_origin)


def set_cookie(response: Response, deps: AccountDeps, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=round((expires_at - datetime.now(UTC)).total_seconds()),
        path="/",
        # Local development runs on http://localhost.
        secure=deps.site_url.startswith("https://"),
        httponly=True,
        samesite="lax",
    )


class Options(BaseModel):
    sign_in: bool
    turnstile_site_key: str | None


class CodeRequest(BaseModel):
    email: str = Field(max_length=254)
    # The Turnstile widget's token; empty when the form has no bot check.
    bot_token: str = Field(default="", max_length=2048)


class CodeSignIn(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(pattern=r"^\s*\d{6}\s*$")


class LinkSignIn(BaseModel):
    token: str = Field(min_length=20, max_length=100)


class FollowedTopic(BaseModel):
    slug: str = Field(max_length=80)
    slot: int = Field(ge=1, le=MAX_TOPICS)


class Suggestion(BaseModel):
    id: int
    name: str
    note: str
    # open, accepted or declined; once accepted, the topic is live when its status is active.
    status: str
    reason: str
    created_at: datetime
    topic_slug: str | None
    topic_status: str | None


class Me(BaseModel):
    email: str
    topics: list[FollowedTopic]
    suggestions: list[Suggestion]


class NewSuggestion(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    # What the topic should follow, in a line.
    note: str = Field(default="", max_length=300)


class Topics(BaseModel):
    topics: list[FollowedTopic] = Field(max_length=MAX_TOPICS)


async def me_for(deps: AccountDeps, found: SignedIn) -> Me:
    topics = await followed(deps.engine, found.reader_id)
    return Me(
        email=found.email,
        topics=[FollowedTopic(slug=t.slug, slot=t.slot) for t in topics],
        suggestions=[
            Suggestion(**vars(s)) for s in await suggestions(deps.engine, found.reader_id)
        ],
    )


def refuse(error: Exception, code: int) -> HTTPException:
    return HTTPException(code, str(error))


@router.get("/auth/options")
async def options(request: Request, deps: Deps) -> Options:
    return Options(
        sign_in=deps.mailer is not None,
        turnstile_site_key=request.app.state.settings.turnstile_site_key,
    )


@router.post(
    "/auth/code",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[SameOrigin],
    responses={
        400: {"description": "Not an email, or the bot check failed"},
        429: {"description": "Too many codes"},
        502: {"description": "The email could not be sent"},
        503: {"description": "Sign-in is off"},
    },
)
async def request_code(body: CodeRequest, request: Request, deps: Deps) -> dict[str, bool]:
    ip = request.client.host if request.client else ""
    try:
        await send_code(
            deps,
            body.email,
            ip=ip,
            ip_hash=hash_ip(ip, request.app.state.ip_key),
            bot_token=body.bot_token,
            now=datetime.now(UTC),
        )
    except SignInOffError as error:
        raise refuse(error, status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except (InvalidEmailError, BotCheckFailedError) as error:
        raise refuse(error, status.HTTP_400_BAD_REQUEST) from error
    except TooManyCodesError as error:
        raise refuse(error, status.HTTP_429_TOO_MANY_REQUESTS) from error
    except EmailNotSentError as error:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The email could not be sent. Try again in a minute."
        ) from error
    return {"sent": True}


@router.post(
    "/auth/verify",
    dependencies=[SameOrigin],
    responses={400: {"description": "Not an email, or a wrong, used or expired code"}},
)
async def verify_code(body: CodeSignIn, response: Response, deps: Deps) -> Me:
    try:
        session = await sign_in_with_code(deps.engine, body.email, body.code, datetime.now(UTC))
    except (InvalidEmailError, WrongCodeError, CodeUsedUpError) as error:
        raise refuse(error, status.HTTP_400_BAD_REQUEST) from error
    return await start(response, deps, session)


@router.post(
    "/auth/link",
    dependencies=[SameOrigin],
    responses={400: {"description": "Used or expired link"}},
)
async def verify_link(body: LinkSignIn, response: Response, deps: Deps) -> Me:
    try:
        session = await sign_in_with_link(deps.engine, body.token, datetime.now(UTC))
    except CodeUsedUpError as error:
        raise refuse(error, status.HTTP_400_BAD_REQUEST) from error
    return await start(response, deps, session)


async def start(response: Response, deps: AccountDeps, session: Session) -> Me:
    set_cookie(response, deps, session.token, session.expires_at)
    return await me_for(deps, SignedIn(session.reader_id, session.email, None))


@router.post("/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT, dependencies=[SameOrigin])
async def end_session(request: Request, response: Response, deps: Deps) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        await sign_out(deps.engine, token)
    response.delete_cookie(COOKIE, path="/")


@router.get("/me")
async def me(deps: Deps, found: Annotated[SignedIn | None, Depends(reader)]) -> Me | None:
    """The signed-in reader's account, or null when no one is signed in."""
    return await me_for(deps, found) if found else None


@router.put(
    "/me/topics",
    dependencies=[SameOrigin],
    responses={400: {"description": "Too many topics, or one twice"}, 401: {}},
)
async def set_topics(body: Topics, deps: Deps, found: Reader) -> Me:
    try:
        await follow(deps.engine, found.reader_id, [Followed(t.slug, t.slot) for t in body.topics])
    except InvalidTopicsError as error:
        raise refuse(error, status.HTTP_400_BAD_REQUEST) from error
    return await me_for(deps, found)


@router.post(
    "/me/suggestions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[SameOrigin],
    responses={400: {"description": "Too many waiting"}, 401: {}},
)
async def suggest_topic(body: NewSuggestion, deps: Deps, found: Reader) -> Me:
    try:
        await suggest(deps.engine, found.reader_id, body.name, body.note)
    except TooManySuggestionsError as error:
        raise refuse(error, status.HTTP_400_BAD_REQUEST) from error
    return await me_for(deps, found)


@router.delete(
    "/me", status_code=status.HTTP_204_NO_CONTENT, dependencies=[SameOrigin], responses={401: {}}
)
async def delete_me(response: Response, deps: Deps, found: Reader) -> None:
    await delete_account(deps.engine, found.reader_id)
    response.delete_cookie(COOKIE, path="/")
