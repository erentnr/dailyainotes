"""Sends email through Resend's HTTPS API (resend.com/docs, 2026-10-15). The free plan sends
3,000 emails a month and 100 a day."""

from dataclasses import dataclass

import httpx2

ENDPOINT = "https://api.resend.com/emails"


class EmailNotSentError(Exception):
    pass


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class ResendMailer:
    client: httpx2.AsyncClient
    api_key: str
    sender: str

    async def send(self, email: Email) -> None:
        try:
            response = await self.client.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "from": self.sender,
                    "to": [email.to],
                    "subject": email.subject,
                    "text": email.text,
                    "html": email.html,
                },
                timeout=15,
            )
        except httpx2.HTTPError as error:
            raise EmailNotSentError(type(error).__name__) from error
        if response.status_code != 200:
            # Resend's error body names the problem; the request itself held the address.
            raise EmailNotSentError(
                f"Resend answered {response.status_code}: {response.text[:200]}"
            )
