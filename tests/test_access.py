"""The editor's sign-in (ADR 0003): only a token Cloudflare Access signed for this application,
still valid and naming an email, lets a request into the admin API."""

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from dailyainotes.api.access import AccessDeniedError

pytestmark = pytest.mark.anyio


async def test_a_token_from_access_names_the_editor(access: Any) -> None:
    assert await access.verifier.email(access.token("Editor@Example.com")) == "editor@example.com"


async def test_a_token_signed_by_another_key_is_refused(access: Any) -> None:
    stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(AccessDeniedError, match="Signature verification failed"):
        await access.verifier.email(access.token(key=stranger))


@pytest.mark.parametrize(
    ("claims", "reason"),
    [
        ({"aud": ["another-application"]}, "Audience doesn't match"),
        ({"iss": "https://other.cloudflareaccess.com"}, "Invalid issuer"),
        ({"exp": int(time.time()) - 120}, "Signature has expired"),
        ({"exp": None}, 'Token is missing the "exp" claim'),
        ({"email": None}, "names no email"),
    ],
)
async def test_a_token_for_another_app_expired_or_without_an_email_is_refused(
    access: Any, claims: dict[str, Any], reason: str
) -> None:
    with pytest.raises(AccessDeniedError, match=reason):
        await access.verifier.email(access.token(**claims))


async def test_an_unsigned_token_is_refused(access: Any) -> None:
    now = int(time.time())
    claims = {"aud": [access.AUD], "iss": f"https://{access.TEAM}", "iat": now, "exp": now + 60}
    unsigned = jwt.encode({**claims, "email": "editor@example.com"}, None, algorithm="none")

    with pytest.raises(AccessDeniedError):
        await access.verifier.email(unsigned)


async def test_a_few_seconds_of_clock_skew_are_allowed(access: Any) -> None:
    just_expired = access.token(exp=int(time.time()) - 5)

    assert await access.verifier.email(just_expired) == "editor@example.com"
