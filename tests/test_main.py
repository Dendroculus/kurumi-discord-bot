import pytest
from main import get_command_description

@pytest.mark.parametrize(
    "help_text,expected",
    [
        ("Cat: A feline", "A feline"),
        ("No colon here", "No colon here"),
        (None, "No description available."),
        ("Category:   spaced", "spaced"),
    ],
)
def test_get_command_description(help_text, expected):
    assert get_command_description(help_text) == expected