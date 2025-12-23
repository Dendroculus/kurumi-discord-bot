import logging
import pytest
from utils import moderationUtils as mod

class FakeGuild:
    def __init__(self):
        self.banned = False
        self.kicked = False
    async def ban(self, member, reason=None):
        self.banned = True
    async def kick(self, member, reason=None):
        self.kicked = True

class FakeChannel:
    def __init__(self):
        self.messages = []
    async def send(self, content, ephemeral=False, delete_after=None):
        self.messages.append(content)

class FakeMember:
    def __init__(self):
        self.guild = FakeGuild()
        self.timed_out_until = None
        self.mention = "<@1>"  # provide mention used in messages
    async def edit(self, timed_out_until=None, reason=None):
        self.timed_out_until = timed_out_until

@pytest.mark.asyncio
async def test_enforce_punishments_paths(monkeypatch):
    monkeypatch.setattr(mod, "BAN_AT_WARNINGS", 4)
    monkeypatch.setattr(mod, "KICK_AT_WARNINGS", 3)
    monkeypatch.setattr(mod, "TIMEOUT_AT_WARNINGS", 2)
    monkeypatch.setattr(mod, "TIMEOUT_SECONDS_ON_THRESHOLD", 60)

    member = FakeMember()
    channel = FakeChannel()
    logger = logging.getLogger("bot-test")

    assert await mod.enforce_punishments(member, 4, channel, logger) == "ban"
    assert member.guild.banned is True

    member = FakeMember()
    assert await mod.enforce_punishments(member, 3, channel, logger) == "kick"
    assert member.guild.kicked is True

    member = FakeMember()
    result = await mod.enforce_punishments(member, 2, channel, logger)
    assert result == "timeout"
    assert member.timed_out_until is not None