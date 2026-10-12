"""Publishers: who wrote a document, and how far we trust them to start with."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from dailyainotes.db.tables import Publisher
from dailyainotes.domain.trust import TRUST_PRIOR


async def ensure_publisher(connection: AsyncConnection, domain: str) -> int:
    """The publisher's id, creating an `unknown` publisher the first time a domain appears."""
    await connection.execute(
        insert(Publisher)
        .values(
            domain=domain,
            name=domain,
            kind="unknown",
            owner_group=domain,
            trust_prior=TRUST_PRIOR["unknown"],
        )
        .on_conflict_do_nothing(index_elements=["domain"])
    )
    publisher_id: int = (
        await connection.execute(select(Publisher.id).where(Publisher.domain == domain))
    ).scalar_one()
    return publisher_id
