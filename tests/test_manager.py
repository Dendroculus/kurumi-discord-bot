import pytest
from cogs.manager import Manager

@pytest.mark.parametrize(
    "duration,seconds",
    [
        ("10s", 10),
        ("2m", 120),
        ("1h", 3600),
        ("1d", 86400),
    ],
)
def test_parse_duration_valid(duration, seconds):
    manager = Manager(bot=None)
    delta = manager.parse_duration(duration)
    assert delta.total_seconds() == seconds

def test_parse_duration_invalid():
    manager = Manager(bot=None)
    assert manager.parse_duration("bad") is None