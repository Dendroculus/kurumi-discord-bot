from discord.ext import commands
from collections import deque, OrderedDict
import time
import logging
import hashlib
from typing import Dict, Tuple
from constants.configs import (
    SPAM_TRACK_MESSAGE_COUNT, 
    SPAM_WINDOW_SECONDS, 
    MAX_WARNINGS,
    MAX_TRACKED_USERS,
)

from utils.database import db
from utils.moderation_utils import enforce_punishments

"""
automod.py

Automated moderation cog for the Kurumi Discord bot.

Responsibilities:
- Track recent messages for users to detect spam patterns.
- Warn users who are spamming and escalate punishments via the moderation utilities.
- Maintain lightweight in-memory tracking structures (LRU Cache) to ensure scalability.

Expectations / Integration Points:
- Expects `utils.config` to provide configuration constants.
- Expects `utils.database.db` for warning persistence.
- Expects `utils.moderation_utils.enforce_punishments` for escalation logic.
"""

class AutoMod(commands.Cog):
    """
    Cog that implements scalable automated moderation (anti-spam and warnings).

    Behavior overview:
    - Uses a "Window Slider" algorithm with an LRU (Least Recently Used) cache.
    - Limits memory usage by strictly capping tracked users to MAX_TRACKED_USERS.
    - Detects spam via time density (bursts) or content repetition.
    - Uses "Lazy Expiration" to clean up debounce timers without background tasks.

    Attributes:
        bot: the discord bot instance.
        user_messages: OrderedDict(user_id -> deque) acting as an LRU cache.
        recently_warned: dict[(guild_id, user_id) -> expiry_timestamp] to debounce warns.
        logger: logger instance for recording automod actions.
    """
    def __init__(self, bot):
        self.bot = bot
        self.user_messages: OrderedDict[int, deque] = OrderedDict()
        self.recently_warned: Dict[Tuple[int, int], float] = {}
        self.logger = logging.getLogger("bot")

    async def on_message_warn(self, user_id: int, guild_id: int) -> int:
        return await db.increase_warning(user_id, guild_id)

    async def get_warnings(self, user_id: int, guild_id: int):
        return await db.get_warnings(user_id, guild_id)

    async def reset_warnings(self, user_id: int, guild_id: int):
        await db.reset_warnings(user_id, guild_id)

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not message.guild:
            return

        now = time.time()
        user_id = message.author.id
        guild_id = message.guild.id
        warn_key = (guild_id, user_id)
        
        if warn_key in self.recently_warned:
            if now > self.recently_warned[warn_key]:
                del self.recently_warned[warn_key] 
            else:
                return 

        content_bytes = message.content.encode('utf-8')
        content_hash = hashlib.sha256(content_bytes).digest()[:8]

        if user_id in self.user_messages:
            self.user_messages.move_to_end(user_id)
        else:
            if len(self.user_messages) >= MAX_TRACKED_USERS:
                self.user_messages.popitem(last=False) # Remove oldest user
            self.user_messages[user_id] = deque(maxlen=SPAM_TRACK_MESSAGE_COUNT)

        self.user_messages[user_id].append((content_hash, now))
        
        if self.is_spamming(user_id):
            self.recently_warned[warn_key] = now + 5.0
            await self.warn_user(message)

    def is_spamming(self, user_id):
        msgs = self.user_messages[user_id]
        if len(msgs) < SPAM_TRACK_MESSAGE_COUNT:
            return False

        if msgs[-1][1] - msgs[0][1] < SPAM_WINDOW_SECONDS:
            return True

        contents = [msg[0] for msg in msgs]
        if len(set(contents)) == 1:
            return True

        return False

    async def warn_user(self, message):
        user = message.author
        guild_id = message.guild.id 

        count = await self.on_message_warn(user.id, guild_id)
        
        await message.channel.send(
            f"⚠️ {user.mention}, please stop spamming! Warning `{count}`/{MAX_WARNINGS}.",
            delete_after=10
        )

        await enforce_punishments(
            member=user,
            count=count,
            channel=message.channel,
            logger=self.logger,
        )


async def setup(bot):
    await db.init()
    await bot.add_cog(AutoMod(bot))
    logging.getLogger("bot").info("Loaded automod cog.")