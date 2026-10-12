"""GitHub releases through the REST API. github.com's robots.txt disallows `.atom` feeds,
so the API is the polite way in: 60 requests an hour without a token, 5,000 with one."""

from dailyainotes.sources.http import Http
from dailyainotes.sources.items import LEAD_LIMIT, FetchOutcome, RawItem, from_iso


async def fetch_github_releases(http: Http, repo: str, *, token: str | None = None) -> FetchOutcome:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = await http.get(f"https://api.github.com/repos/{repo}/releases?per_page=10", headers)
    response.raise_for_status()
    return FetchOutcome(
        [
            RawItem(
                url=release["html_url"],
                title=f"{repo} {release['name'] or release['tag_name']}",
                lead=" ".join((release["body"] or "").split())[:LEAD_LIMIT],
                published_at=from_iso(release["published_at"]),
            )
            for release in response.json()
            # Release candidates and drafts are noise for daily notes.
            if not release["draft"] and not release["prerelease"]
        ]
    )
