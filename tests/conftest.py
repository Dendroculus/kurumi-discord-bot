import sys
from pathlib import Path
import types
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

class DummyChannel:
    def __init__(self):
        self.sent = []
    async def send(self, *args, **kwargs):
        self.sent.append((args, kwargs))

class DummyCtx:
    def __init__(self):
        self.channel = DummyChannel()
        self.author = types.SimpleNamespace(id=1, mention="<@1>")

@pytest.fixture
def dummy_ctx():
    return DummyCtx()

@pytest.fixture
def dummy_channel():
    return DummyChannel()

