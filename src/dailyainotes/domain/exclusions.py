"""Publishers whose terms rule out our use (INTENT.md, Copyright): none of their pages is
fetched, none of their feeds becomes a source (MEMORY.md has each reason)."""

# Registrable domains, as `sources.urls.registrable_domain` returns them.
EXCLUDED_PUBLISHERS = frozenset(
    {
        "theguardian.com",
        "guardian.co.uk",
        "nytimes.com",
        "reddit.com",
        "redd.it",
    }
)


def is_excluded(domain: str | None) -> bool:
    return domain in EXCLUDED_PUBLISHERS
