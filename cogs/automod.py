from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import time
import logging
from utils import config                  
from utils.database import db            
from utils.moderation_utils import enforce_punishments  

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(lambda: deque(maxlen=config.SPAM_TRACK_MESSAGE_COUNT))
        self.recently_warned = set()
        self._bg_tasks = set()
        self.logger = logging.getLogger("bot")

    def _track_task(self, coro):
        task = asyncio.create_task(coro)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return task

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

        self.user_messages[user_id].append((message.content, now))

        if self.is_spamming(user_id) and (guild_id, user_id) not in self.recently_warned:
            self.recently_warned.add((guild_id, user_id))
            try:
                await self.warn_user(message)
            finally:
                self._track_task(self.clear_recent_warn(guild_id, user_id))

    async def clear_recent_warn(self, guild_id, user_id):
        await asyncio.sleep(5)
        self.recently_warned.discard((guild_id, user_id))

    def is_spamming(self, user_id):
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