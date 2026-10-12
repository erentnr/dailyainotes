"""`GET /api/v1/health`: used by Docker, the deploy script and uptime checks."""

from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from dailyainotes.db.engine import database_is_reachable

router = APIRouter()


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]


@router.get("/health")
async def health(request: Request, response: Response) -> Health:
    if await database_is_reachable(request.app.state.engine):
        return Health(status="ok", database="ok")
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(status="degraded", database="unreachable")
