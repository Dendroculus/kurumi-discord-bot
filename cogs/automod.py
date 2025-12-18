from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import time
import logging
from typing import Dict, Tuple

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

- A periodic background cleanup task (_periodic_cleanup) that runs every
  few minutes to remove stale entries from in-memory tracking structures so
  they don't grow unbounded.
- Adds cog_unload to cancel background tasks when the cog is unloaded.

Expectations / Integration Points:
- Expects `utils.config` to provide configuration constants:
    - SPAM_TRACK_MESSAGE_COUNT: number of recent messages to track per user
    - SPAM_WINDOW_SECONDS: time window to consider for spam detection
    - MAX_WARNINGS: maximum warning count before escalations (used only in messages)
    - (optional) AUTOMOD_CLEANUP_INTERVAL_SECONDS: how often cleanup runs (default 300)
    - (optional) AUTOMOD_MESSAGE_AGE_SECONDS: how old messages can be before removal
- Expects `utils.database.db` to provide async methods:
    - increase_warning(user_id, guild_id) -> int
    - get_warnings(user_id, guild_id)
    - reset_warnings(user_id, guild_id)
    - init() used in setup to ensure DB ready
- Expects `utils.moderation_utils.enforce_punishments` to accept:
    - member, count, channel, logger and handle escalation (mute/kick/ban/etc.)
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
    - Prevents immediate duplicate warnings using a short-lived recently_warned dict
      keyed by (guild_id, user_id) -> expiry_timestamp, and a background cleanup
      task removes stale entries periodically.
    - Provides cog_unload to cancel background tasks cleanly when the cog is removed.

    Attributes:
        bot: the discord bot instance.
        user_messages: defaultdict(user_id -> deque[(content, timestamp)]).
        recently_warned: dict[(guild_id, user_id) -> expiry_timestamp] to debounce warns.
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
        self.user_messages: Dict[int, deque] = defaultdict(lambda: deque(maxlen=config.SPAM_TRACK_MESSAGE_COUNT))
        # Map (guild_id, user_id) -> expiry_timestamp
        self.recently_warned: Dict[Tuple[int, int], float] = {}
        self._bg_tasks = set()
        self.logger = logging.getLogger("bot")

        # Background task defaults (can be overridden via config)
        self._cleanup_interval = getattr(config, "AUTOMOD_CLEANUP_INTERVAL_SECONDS", 300)  # every 5 minutes
        # Age after which tracked messages are considered stale and can be removed.
        # Default to a few times the spam window to be conservative.
        self._message_age = getattr(
            config,
            "AUTOMOD_MESSAGE_AGE_SECONDS",
            max(getattr(config, "SPAM_WINDOW_SECONDS", 60) * 4, 300),
        )

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

    def _start_background_tasks(self):
        """
        Start background tasks used by the cog.

        Called after the cog is added to the bot (setup).
        """
        # Start the periodic cleanup task
        self._track_task(self._periodic_cleanup())

    async def on_message_warn(self, user_id: int, guild_id: int) -> int:
        """
        Increment the stored warning count for a user in a guild.

        This delegates to the database abstraction and returns the new warning count.
        """
        return await db.increase_warning(user_id, guild_id)

    async def get_warnings(self, user_id: int, guild_id: int):
        """
        Retrieve the current number of warnings for a user in a guild.
        """
        return await db.get_warnings(user_id, guild_id)

    async def reset_warnings(self, user_id: int, guild_id: int):
        """
        Reset persisted warnings for a user in a guild.
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
        """
        if message.author.bot or not message.guild:
            return

        now = time.time()
        user_id = message.author.id
        guild_id = message.guild.id

        self.user_messages[user_id].append((message.content, now))

        key = (guild_id, user_id)

        # Expire recently_warned entries inline to avoid false positives
        expiry = self.recently_warned.get(key)
        if expiry is not None and expiry <= now:
            # expired, remove it
            self.recently_warned.pop(key, None)
            expiry = None

        if self.is_spamming(user_id) and key not in self.recently_warned:
            # Set a short debounce expiry. Keep in sync with clear_recent_warn's sleep.
            debounce_seconds = 5
            self.recently_warned[key] = now + debounce_seconds
            try:
                await self.warn_user(message)
            finally:
                # schedule a cleanup task that will remove the key after debounce_seconds
                self._track_task(self.clear_recent_warn(guild_id, user_id, debounce_seconds))

    async def clear_recent_warn(self, guild_id, user_id, delay: float):
        """
        Remove a (guild_id, user_id) tuple from the recently_warned map after `delay` seconds.

        This acts as a debounce to avoid warning the same user repeatedly within a short period.
        """
        try:
            await asyncio.sleep(delay)
            self.recently_warned.pop((guild_id, user_id), None)
        except asyncio.CancelledError:
            # Task was cancelled (likely during cog unload); ensure entry is removed to avoid stale state.
            self.recently_warned.pop((guild_id, user_id), None)
            raise

    def is_spamming(self, user_id):
        """
        Heuristic to determine whether the given user is spamming.
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

    async def _periodic_cleanup(self):
        """
        Periodically remove stale in-memory tracking data.

        This background task runs indefinitely until cancelled. On each interval:
        - Trims old message entries from user message deques.
        - Removes users whose message deques become empty.
        - Clears expired entries from the recently_warned map.

        Cancellation is expected during cog unload and is re-raised to allow
        proper task shutdown.
        """
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                now = time.time()
                cutoff = now - self._message_age

                self._cleanup_user_messages(cutoff)
                self._cleanup_recently_warned(now)

        except asyncio.CancelledError:
            raise


    def _cleanup_user_messages(self, cutoff: float):
        """
        Remove outdated message records from per-user deques.

        Messages older than the cutoff timestamp are removed from the left
        of each deque. If a deque becomes empty, the corresponding user entry
        is removed to keep memory usage bounded.
        """
        for user_id, dq in list(self.user_messages.items()):  # noqa: B020
            self._trim_deque(dq, cutoff)
            if not dq:
                self.user_messages.pop(user_id, None)


    def _trim_deque(self, dq, cutoff: float):
        """
        Trim old entries from a deque in-place.

        Continuously removes entries from the left while their timestamp is
        older than the cutoff. Concurrent modifications are safely ignored.
        """
        try:
            while dq and dq[0][1] < cutoff:
                dq.popleft()
        except IndexError:
            pass


    def _cleanup_recently_warned(self, now: float):
        """
        Remove expired entries from the recently_warned tracking map.

        Any entry whose expiry timestamp is less than or equal to the current
        time is removed.
        """
        for key, expiry in list(self.recently_warned.items()):  # noqa: B020
            if expiry <= now:
                self.recently_warned.pop(key, None)


    def cog_unload(self):
        """
        Called when the cog is unloaded. Cancel background tasks to stop periodic cleanup
        and any pending clear_recent_warn tasks, then clear tracked state.
        """
        # Cancel background tasks
        for task in list(self._bg_tasks): # noqa: B020
            task.cancel()

        # Optionally, clear in-memory structures to free memory immediately
        self.user_messages.clear()
        self.recently_warned.clear()


async def setup(bot):
    await db.init()
    cog = AutoMod(bot)
    await bot.add_cog(cog)
    # start background tasks after the cog is added
    cog._start_background_tasks()
    logging.getLogger("bot").info("Loaded automod cog.")