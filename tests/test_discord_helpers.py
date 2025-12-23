from utils.discordHelpers import create_choices, create_same_choices
from discord import app_commands

def test_create_choices():
    data = {"A": "a", "B": "b"}
    choices = create_choices(data)
    assert all(isinstance(c, app_commands.Choice) for c in choices)
    assert {c.name for c in choices} == {"A", "B"}

def test_create_same_choices():
    items = ["x", "y"]
    choices = create_same_choices(items)
    assert [c.value for c in choices] == items