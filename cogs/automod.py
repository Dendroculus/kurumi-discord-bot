from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import time
import logging
from utils import config                  
from utils.database import db            
from utils.moderation_utils import enforce_punishments  

"""
automod.py

Automated moderation cog for the Kurumi Discord bot.

Responsibilities:
- Track recent messages for users to detect spam patterns.
- Warn users who are spamming and escalate punishments via the moderation utilities.
- Maintain lightweight in-memory tracking structures and background tasks for time-based operations.

Expectations / Integration Points:
- Expects `utils.config` to provide configuration constants:
    - SPAM_TRACK_MESSAGE_COUNT: number of recent messages to track per user
    - SPAM_WINDOW_SECONDS: time window to consider for spam detection
    - MAX_WARNINGS: maximum warning count before escalations (used only in messages)
- Expects `utils.database.db` to provide async methods:
    - increase_warning(user_id, guild_id) -> int
    - get_warnings(user_id, guild_id)
    - reset_warnings(user_id, guild_id)
    - init() used in setup to ensure DB ready
- Expects `utils.moderation_utils.enforce_punishments` to accept:
    - member, count, channel, logger and handle escalation (mute/kick/ban/etc.)

Notes:
- This module only adds documentation; no code logic was modified.
"""

class AutoMod(commands.Cog):
    """
    Cog that implements simple automated moderation (anti-spam and warnings).

    Behavior overview:
    - Keeps a per-user deque of recent (content, timestamp) tuples limited by
      config.SPAM_TRACK_MESSAGE_COUNT.
    - Detects spam when either enough messages occur within config.SPAM_WINDOW_SECONDS
      or when the recent tracked messages are identical.
    - When spam is detected, issues a warning (incrementing a persisted counter)
      and calls enforce_punishments to apply escalation logic.
    - Prevents immediate duplicate warnings using a short-lived recently_warned set
      keyed by (guild_id, user_id).

    Attributes:
        bot: the discord bot instance.
        user_messages: defaultdict(user_id -> deque[(content, timestamp)]).
        recently_warned: set of (guild_id, user_id) to debounce repeated warns.
        _bg_tasks: set of tracked background asyncio.Task objects.
        logger: logger instance for recording automod actions.
    """
    def __init__(self, bot):
        """
        Initialize the AutoMod cog.

        Args:
            bot: The discord.Bot / commands.Bot instance this cog is attached to.
        """
        self.bot = bot
        self.user_messages = defaultdict(lambda: deque(maxlen=config.SPAM_TRACK_MESSAGE_COUNT))
        self.recently_warned = set()
        self._bg_tasks = set()
        self.logger = logging.getLogger("bot")

    def _track_task(self, coro):
        """
        Create and track a background asyncio Task.

        The returned Task will be added to self._bg_tasks until it completes.

        Args:
            coro: coroutine to schedule as a background task.

        Returns:
            asyncio.Task: the scheduled task.
        """
        task = asyncio.create_task(coro)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return task

    async def on_message_warn(self, user_id: int, guild_id: int) -> int:
        """
        Increment the stored warning count for a user in a guild.

        This delegates to the database abstraction and returns the new warning count.

        Args:
            user_id: Discord user id.
            guild_id: Discord guild id.

        Returns:
            int: the updated total warning count for the user.
        """
        return await db.increase_warning(user_id, guild_id)

    async def get_warnings(self, user_id: int, guild_id: int):
        """
        Retrieve the current number of warnings for a user in a guild.

        Args:
            user_id: Discord user id.
            guild_id: Discord guild id.

        Returns:
            Value returned by db.get_warnings (implementation-defined, typically int).
        """
        return await db.get_warnings(user_id, guild_id)

    async def reset_warnings(self, user_id: int, guild_id: int):
        """
        Reset persisted warnings for a user in a guild.

        Args:
            user_id: Discord user id.
            guild_id: Discord guild id.
        """
        await db.reset_warnings(user_id, guild_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listener for message events used to detect spam.

        Behavior:
        - Ignores messages from bots and messages outside of guilds (DMs).
        - Appends (content, timestamp) to the user's deque.
        - Calls is_spamming to detect spam; if detected and not recently warned,
          warns the user and schedules a short debounce window via clear_recent_warn.

        Args:
            message: discord.Message instance.
        """
        if message.author.bot or not message.guild:
            return

        now = time.time()
        user_id = message.author.id
        guild_id = message.guild.id

        self.user_messages[user_id].append((message.content, now))

        if self.is_spamming(user_id) and (guild_id, user_id) not in self.recently_warned:
            self.recently_warned.add((guild_id, user_id))
            try:
                await self.warn_user(message)
            finally:
                self._track_task(self.clear_recent_warn(guild_id, user_id))

    async def clear_recent_warn(self, guild_id, user_id):
        """
        Remove a (guild_id, user_id) tuple from the recently_warned set after a short delay.

        This acts as a debounce to avoid warning the same user repeatedly within a short period.

        Args:
            guild_id: guild id where the warning occurred.
            user_id: user id who was warned.
        """
        await asyncio.sleep(5)
        self.recently_warned.discard((guild_id, user_id))

    def is_spamming(self, user_id):
        """
        Heuristic to determine whether the given user is spamming.

        Spam detection rules:
        - If fewer than SPAM_TRACK_MESSAGE_COUNT messages have been recorded, not spam.
        - If the oldest and newest tracked messages fall within SPAM_WINDOW_SECONDS, consider spam.
        - If all tracked message contents are identical, consider spam.

        Args:
            user_id: Discord user id to evaluate.

        Returns:
            bool: True if the user is considered spamming, False otherwise.
        """
        msgs = self.user_messages[user_id]
        if len(msgs) < config.SPAM_TRACK_MESSAGE_COUNT:
            return False

        if msgs[-1][1] - msgs[0][1] < config.SPAM_WINDOW_SECONDS:
            return True

        contents = [msg[0] for msg in msgs]
        if len(set(contents)) == 1:
            return True

        return False

    async def warn_user(self, message):
        """
        Issue a warning to a user for spamming and call the punishment enforcer.

        Steps:
        - Increment the persisted warning count for the user.
        - Send a user-facing warning message to the channel including current/maximum warnings.
        - Call enforce_punishments to allow escalation based on the new warning count.

        Args:
            message: discord.Message that triggered the warning.
        """
        user = message.author
        guild = message.guild
        user_id = user.id
        guild_id = guild.id

        count = await self.on_message_warn(user_id, guild_id)
        await message.channel.send(f"⚠️ {user.mention}, please stop spamming! Warning `{count}`/{config.MAX_WARNINGS}.")

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