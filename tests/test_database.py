# tests/test_database.py
import pytest
from unittest.mock import AsyncMock
from utils import database as db_mod

class FakeConn:
    def __init__(self):
        self.counts = {}

    async def execute(self, query, *params):
        if "INSERT INTO warnings" in query or "ON CONFLICT" in query:
            user_id, guild_id = params[0], params[1]
            key = (user_id, guild_id)
            self.counts[key] = self.counts.get(key, 0) + 1
        elif query.strip().startswith("UPDATE warnings SET count=0"):
            user_id, guild_id = params[0], params[1]
            key = (user_id, guild_id)
            if key in self.counts:
                self.counts[key] = 0

    async def fetchrow(self, query, *params):
        user_id, guild_id = params[0], params[1]
        key = (user_id, guild_id)
        if key in self.counts:
            return {"count": min(self.counts[key], getattr(db_mod, "MAX_WARNINGS", self.counts[key]))}
        return None

class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False

@pytest.mark.asyncio
async def test_init_requires_conn_string(monkeypatch):
    monkeypatch.setattr(db_mod, "POSTGRES_CONN_STRING", None)
    db = db_mod.Database()
    with pytest.raises(RuntimeError):
        await db.init()

@pytest.mark.asyncio
async def test_warning_flow(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(db_mod, "POSTGRES_CONN_STRING", "postgres://test")
    monkeypatch.setattr(db_mod.asyncpg, "create_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(db_mod, "MAX_WARNINGS", 2)

    db = db_mod.Database()
    await db.init()

    assert await db.increase_warning(1, 1) == 1
    assert await db.increase_warning(1, 1) == 2# capped
    assert await db.get_warnings(1, 1) == 2
    await db.reset_warnings(1, 1)
    assert await db.get_warnings(1, 1) == 0