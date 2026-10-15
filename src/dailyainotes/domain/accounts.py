"""Reader accounts as plain rules (ADR 0003): what counts as an email address, how sign-in codes
and session tokens are made, and how they are stored, which is only as a hash."""

import hashlib
import re
import secrets
from datetime import timedelta

# A code or link works once, for this long; this many wrong codes void it.
CODE_LIFETIME = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5
# A session lasts this long after its last use; it is renewed at most once a day.
SESSION_LIFETIME = timedelta(days=30)
SESSION_RENEWAL = timedelta(days=1)
# A reader follows at most as many topics as there are color slots (DESIGN.md, Colors).
MAX_TOPICS = 8

# Deliberately loose: one @, no spaces, a dot in the domain. Sending the code is the real check.
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s.]+")
MAX_EMAIL_LENGTH = 254


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return len(email) <= MAX_EMAIL_LENGTH and EMAIL.fullmatch(email) is not None


def new_code() -> str:
    """Six digits, typed by hand from the email."""
    return f"{secrets.randbelow(1_000_000):06d}"


def new_token() -> str:
    """For the sign-in link and the session cookie: 256 random bits."""
    return secrets.token_urlsafe(32)


def digest(value: str) -> str:
    """What is stored instead of a code or token, so a copy of the database signs no one in."""
    return hashlib.sha256(value.encode()).hexdigest()


def code_digest(email: str, code: str) -> str:
    # With the email, so the same code sent to two readers is stored differently.
    return digest(f"{email}:{code}")
