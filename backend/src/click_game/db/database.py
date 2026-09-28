import logging
from typing import Any

import mysql.connector
from mysql.connector import Error

from click_game.core.config import settings

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": settings.database_host,
    "port": settings.database_port,
    "user": settings.database_user,
    "password": settings.database_password,
    "database": settings.database_name,
}

_pool = None


def initialize_database() -> None:
    global _pool
    try:
        _pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="click_game",
            pool_size=10,
            pool_reset_session=True,
            **DB_CONFIG,
        )
        logger.info("Database pool initialized")
    except Error:
        logger.exception("Failed to initialize database pool")
        # Preserve the original application's tolerant startup behavior.


def close_database() -> None:
    # mysql.connector's pool does not require an explicit close operation.
    global _pool
    _pool = None


def execute(
    query: str,
    params: tuple | None = None,
    fetch: bool = False,
    dictionary: bool = False,
    commit: bool = False,
) -> Any:
    conn = None
    cursor = None

    try:
        if _pool is not None:
            conn = _pool.get_connection()
        else:
            conn = mysql.connector.connect(**DB_CONFIG)

        cursor = conn.cursor(dictionary=dictionary)
        cursor.execute(query, params or ())

        if commit:
            conn.commit()
            return cursor.lastrowid

        if fetch:
            return cursor.fetchall() or []

        return None

    except Error:
        logger.exception("DB Error")

        if fetch:
            return []

        return None

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def fetch_one(query: str, params: tuple | None = None) -> dict | None:
    rows = execute(query, params=params, fetch=True, dictionary=True)
    return rows[0] if rows else None


def fetch_all(query: str, params: tuple | None = None) -> list[dict]:
    return execute(
        query,
        params=params,
        fetch=True,
        dictionary=True,
    ) or []
