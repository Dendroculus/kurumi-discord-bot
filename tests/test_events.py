import types
import pytest
from cogs import events as events_mod

@pytest.mark.asyncio
async def test_can_respond_cooldowns(monkeypatch):
    # Avoid random cleanup branch
    monkeypatch.setattr(events_mod.random, "random", lambda: 1.0)
    bot = types.SimpleNamespace()
    ev = events_mod.Events(bot)
    ev.mention_cooldown = 2
    ev.global_cooldown = 2
    ev.dm_cooldown = 2
    ev.channel_cooldown = 1

    # Freeze time
    monkeypatch.setattr(ev, "_now", lambda: 1000.0)
    assert ev.can_respond(user_id=1, is_dm=False, channel_id=10) is True

    # Within cooldown -> blocked
    monkeypatch.setattr(ev, "_now", lambda: 1001.0)
    assert ev.can_respond(user_id=1, is_dm=False, channel_id=10) is False

    # After cooldown -> allowed
    monkeypatch.setattr(ev, "_now", lambda: 1003.1)
    assert ev.can_respond(user_id=1, is_dm=False, channel_id=10) is True