import time
from cogs.errors import is_handled

def test_is_handled_debounces():
    key = ("g", "u", "cmd")
    assert is_handled(key, ttl=1) is False
    assert is_handled(key, ttl=1) is True  # within TTL
    time.sleep(1.1)
    assert is_handled(key, ttl=1) is False  # expired