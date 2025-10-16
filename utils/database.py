from __future__ import annotations

import asyncio
from typing import Optional
import aiosqlite
from utils import config 

class Database:
    _lock: asyncio.Lock
    _conn: Optional[aiosqlite.Connection]

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._conn = None

    async def init(self) -> None:
        if self._conn:
            return
        self._conn = await aiosqlite.connect(config.DB_PATH.as_posix())
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA synchronous=NORMAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """)
        await self._conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not initialized. Call await db.init() early in startup.")
        return self._conn

    async def increase_warning(self, user_id: int, guild_id: int) -> int:
        async with self._lock:
            await self.conn.execute("""
            INSERT INTO warnings (user_id, guild_id, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET count = count + 1
            """, (user_id, guild_id))
            await self.conn.commit()

            async with self.conn.execute(
                "SELECT count FROM warnings WHERE user_id=? AND guild_id=?",
                (user_id, guild_id),
            ) as cur:
                row = await cur.fetchone()
                count = int(row[0]) if row else 1
                return min(count, config.MAX_WARNINGS)

    async def get_warnings(self, user_id: int, guild_id: int) -> int:
        async with self.conn.execute(
            "SELECT count FROM warnings WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def reset_warnings(self, user_id: int, guild_id: int) -> None:
        await self.conn.execute(
            "UPDATE warnings SET count=0 WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None


db = Database()