"""URL helpers: the canonical form we deduplicate on, its hash, and the registrable domain."""

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import tldextract

# The bundled public-suffix snapshot: no download at runtime or in tests.
_extract = tldextract.TLDExtract(suffix_list_urls=())

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(url: str) -> str:
    """Lower-case scheme and host, no fragment, no tracking parameters."""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), "")
    )


def url_hash(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()


def registrable_domain(url: str) -> str:
    """`https://feeds.bbci.co.uk/x` → `bbci.co.uk`."""
    parts = _extract(url)
    return parts.top_domain_under_public_suffix or parts.domain
