import pytest
from cogs.miscellaneous import Misc

class FakeResponse:
    def __init__(self, done=False):
        self._done = done
        self.sent = None

    def is_done(self):
        return self._done

    async def send_message(self, content=None, ephemeral=False):
        self.sent = ("send_message", content, ephemeral)

    async def defer(self):
        self.sent = ("defer", None, None)

class FakeFollowup:
    def __init__(self):
        self.sent = None
    async def send(self, content=None, ephemeral=False):
        self.sent = ("followup", content, ephemeral)

class FakeInteraction:
    def __init__(self, done=False):
        self._done = done
        self.response = FakeResponse(done=done)
        self.followup = FakeFollowup()

@pytest.mark.asyncio
async def test_reply_ephemeral_uses_response_first():
    inter = FakeInteraction(done=False)
    await Misc._reply_ephemeral(interaction=inter, content="hi")
    assert inter.response.sent == ("send_message", "hi", True)

@pytest.mark.asyncio
async def test_reply_ephemeral_fallback_followup():
    inter = FakeInteraction(done=True)
    await Misc._reply_ephemeral(interaction=inter, content="hi")
    assert inter.followup.sent == ("followup", "hi", True)