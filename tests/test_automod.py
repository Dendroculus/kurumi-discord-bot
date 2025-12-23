from collections import deque
from cogs.automod import AutoMod
from constants import configs

def test_is_spamming_time_window():
    cog = AutoMod(bot=None)
    user_id = 1
    dq = deque(maxlen=configs.SPAM_TRACK_MESSAGE_COUNT)
    dq.extend([(b"a", 0), (b"b", 1), (b"c", 2), (b"d", 2.5), (b"e", 2.8)])
    cog.user_messages[user_id] = dq
    assert cog.is_spamming(user_id) is True  # dense window

def test_is_spamming_repeated_content():
    cog = AutoMod(bot=None)
    user_id = 2
    dq = deque(maxlen=configs.SPAM_TRACK_MESSAGE_COUNT)
    dq.extend([(b"x", t) for t in [0, 5, 10, 15, 20]])
    cog.user_messages[user_id] = dq
    assert cog.is_spamming(user_id) is True  # repeated content hash