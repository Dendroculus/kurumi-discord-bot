from __future__ import annotations

from typing import Optional, Callable, Awaitable
import asyncpg

from utils import config


class Database:
    """
    Database abstraction using PostgreSQL when POSTGRE_CONN_STRING is provided.
    Falls back to raising if Postgres is not configured (migration target is Postgres).
    """
    _pool: Optional[asyncpg.Pool]

    def __init__(self) -> None:
        self._pool = None

    async def init(self) -> None:
        if self._pool:
            return

        if not config.POSTGRES_CONN_STRING:
            raise RuntimeError("POSTGRE_CONN_STRING is not set. Please configure Postgres in your .env.")

        self._pool = await asyncpg.create_pool(dsn=config.POSTGRES_CONN_STRING, min_size=1, max_size=5)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings (
                    user_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
                """
            )

    async def _with_conn(self, func: Callable[[asyncpg.Connection], Awaitable]):
        if not self._pool:
            raise RuntimeError("Database not initialized. Call await db.init() early in startup.")
        async with self._pool.acquire() as conn:
            return await func(conn)

    async def increase_warning(self, user_id: int, guild_id: int) -> int:
        async def _op(conn: asyncpg.Connection):
            await conn.execute(
                """
                INSERT INTO warnings (user_id, guild_id, count)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, guild_id)
                DO UPDATE SET count = warnings.count + 1
                """,
                user_id,
                guild_id,
            )
            row = await conn.fetchrow(
                "SELECT count FROM warnings WHERE user_id=$1 AND guild_id=$2",
                user_id,
                guild_id,
            )
            count = int(row["count"]) if row else 1
            return min(count, config.MAX_WARNINGS)

        return await self._with_conn(_op)

    async def get_warnings(self, user_id: int, guild_id: int) -> int:
        async def _op(conn: asyncpg.Connection):
            row = await conn.fetchrow(
                "SELECT count FROM warnings WHERE user_id=$1 AND guild_id=$2",
                user_id,
                guild_id,
            )
            return int(row["count"]) if row else 0

        return await self._with_conn(_op)

    async def reset_warnings(self, user_id: int, guild_id: int) -> None:
        async def _op(conn: asyncpg.Connection):
            await conn.execute(
                "UPDATE warnings SET count=0 WHERE user_id=$1 AND guild_id=$2",
                user_id,
                guild_id,
            )

        await self._with_conn(_op)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None


db = Database()