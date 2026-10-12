"""Alembic environment. Migrations run online only, over the psycopg 3 driver."""

from alembic import context
from sqlalchemy import create_engine, pool

from dailyainotes.db.tables import Base
from dailyainotes.settings import get_settings

database_url = context.config.attributes.get("database_url") or get_settings().database_url

engine = create_engine(database_url, poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
