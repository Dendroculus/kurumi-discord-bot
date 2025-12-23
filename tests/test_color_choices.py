import pytest
from utils.colorChoices import get_color_choices, color_choices, colors
from discord import app_commands

def test_get_color_choices_invalid():
    with pytest.raises(ValueError):
        get_color_choices("Bad", "123456")

def test_get_color_choices_valid():
    choice = get_color_choices("Red", "#FF0000")
    assert isinstance(choice, app_commands.Choice)
    assert choice.name == "Red"
    assert choice.value == "#FF0000"

def test_color_choices_matches_source():
    assert len(color_choices) == len(colors)
    first = color_choices[0]
    assert isinstance(first, app_commands.Choice)