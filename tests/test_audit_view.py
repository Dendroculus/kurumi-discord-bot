# tests/test_audit_view.py
import types
import discord
import pytest
from utils.auditView import AuditLogView

class DummyEntry:
    def __init__(self, user="u", target="t", action="AuditLogAction.ban", reason=None):
        self.user = user
        self.target = target
        self.action = action
        self.reason = reason

@pytest.mark.asyncio
async def test_format_target_prefers_name():
    class Named:
        def __init__(self): self.name = "named"
    view = AuditLogView([], types.SimpleNamespace(author=None))
    assert view.format_target(Named()) == "named"

@pytest.mark.asyncio
async def test_format_target_partial_integration(monkeypatch):
    class FakePartial:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(discord, "PartialIntegration", FakePartial, raising=False)
    view = AuditLogView([], types.SimpleNamespace(author=None))
    partial = FakePartial("X")
    result = view.format_target(partial)
    assert result.startswith("X")

@pytest.mark.asyncio
async def test_get_page_embed_contains_entries():
    entries = [DummyEntry(user="user1", target="target1", action="AuditLogAction.kick", reason="Because")]
    ctx = types.SimpleNamespace(author=types.SimpleNamespace(id=1))
    view = AuditLogView(entries, ctx, per_page=1)
    embed = view.get_page_embed()
    assert embed.title.startswith("Audit Log")
    assert len(embed.fields) == 1
    assert "user1" in embed.fields[0].name