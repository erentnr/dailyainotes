"""The editor's sign-in (ADR 0003). Cloudflare Access stands in front of /admin and the admin
API: it signs the editor in, then adds a signed token to every request it lets through, in the
`Cf-Access-Jwt-Assertion` header. The API checks that token against the team's published keys,
so a request that did not pass Access, or a forged header, is refused. The token's email names
who decided."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

import jwt

from dailyainotes.sources.http import USER_AGENT

HEADER = "cf-access-jwt-assertion"
# Clocks on Cloudflare's edge and on the server may differ by a few seconds.
LEEWAY_SECONDS = 30


class AccessDeniedError(Exception):
    """The token is missing, expired, signed by another key, or meant for another application."""


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


@dataclass(frozen=True)
class AccessVerifier:
    team_domain: str
    audience: str
    keys: SigningKeys

    async def email(self, token: str) -> str:
        """The signed-in editor's email, lower-cased."""
        try:
            # PyJWKClient fetches the keys with urllib, which would block the event loop.
            key = await asyncio.to_thread(self.keys.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://{self.team_domain}",
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "aud", "iss"]},
            )
        except jwt.PyJWTError as error:
            raise AccessDeniedError(str(error)) from error
        email = claims.get("email")
        if not isinstance(email, str) or "@" not in email:
            raise AccessDeniedError("the token names no email")
        return email.lower()


def access_verifier(team_domain: str, audience: str) -> AccessVerifier:
    """A verifier that reads the team's public keys and keeps them for an hour; a token signed
    by a newer key makes it read them again."""
    keys = jwt.PyJWKClient(
        f"https://{team_domain}/cdn-cgi/access/certs",
        cache_keys=True,
        lifespan=3600,
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    return AccessVerifier(team_domain, audience, keys)
