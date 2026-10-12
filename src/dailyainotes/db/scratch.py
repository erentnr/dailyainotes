"""Throwaway databases next to the main one, for the eval set."""

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def _maintenance_url(database_url: str) -> str:
    url = make_url(database_url).set(drivername="postgresql", database="postgres")
    return url.render_as_string(hide_password=False)


def recreate_database(database_url: str, name: str) -> str:
    """Drop and create the database `name` on the same server; its URL."""
    with psycopg.connect(_maintenance_url(database_url), autocommit=True) as connection:
        identifier = sql.Identifier(name)
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(identifier))
        connection.execute(sql.SQL("CREATE DATABASE {}").format(identifier))
    return make_url(database_url).set(database=name).render_as_string(hide_password=False)


def drop_database(database_url: str, name: str) -> None:
    with psycopg.connect(_maintenance_url(database_url), autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )
