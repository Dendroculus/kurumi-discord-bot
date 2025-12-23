import discord
import pytest
from utils.invitePages import InvitePages

class FakeResponse:
    def __init__(self):
        self.kwargs = None
    async def edit_message(self, **kwargs):
        self.kwargs = kwargs

class FakeInteraction:
    def __init__(self):
        self.response = FakeResponse()

@pytest.mark.asyncio
async def test_invite_pages_navigation():
    embeds = [discord.Embed(title="One"), discord.Embed(title="Two")]
    view = InvitePages(embeds)
    interaction = FakeInteraction()
    await view.go_next(interaction)
    assert view.index == 1
    assert interaction.response.kwargs["embed"].title == "Two"
    await view.go_prev(interaction)
    assert view.index == 0
    assert interaction.response.kwargs["embed"].title == "One"