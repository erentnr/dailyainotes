import httpx2

from dailyainotes.sources.http import USER_AGENT


def create_client() -> httpx2.AsyncClient:
    """One client for the outside services, closed when the API stops."""
    return httpx2.AsyncClient(headers={"User-Agent": USER_AGENT})
