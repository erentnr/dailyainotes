"""Checks a Cloudflare Turnstile token from the sign-in form: siteverify answers whether a
person solved the challenge on our site (developers.cloudflare.com/turnstile, 2026-10-15). A
token works once, for five minutes."""

from dataclasses import dataclass, field

import httpx2

ENDPOINT = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
MAX_TOKEN_LENGTH = 2048


@dataclass(frozen=True)
class TurnstileCheck:
    client: httpx2.AsyncClient
    # Out of the repr, so no error message or log line can carry it.
    secret: str = field(repr=False)
    # The hostname the widget ran on; a token solved on another site is refused.
    hostname: str

    async def passed(self, token: str, ip: str) -> bool:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            return False
        try:
            response = await self.client.post(
                ENDPOINT,
                data={"secret": self.secret, "response": token, "remoteip": ip},
                timeout=10,
            )
            result = response.json()
        except httpx2.HTTPError, ValueError:
            # Turnstile unreachable: refuse, so sign-in fails closed rather than open.
            return False
        return result.get("success") is True and result.get("hostname") == self.hostname
