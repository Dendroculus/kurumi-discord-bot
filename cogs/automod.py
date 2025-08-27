from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import time

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Use bot.warnings instead of local self.user_warnings
        if not hasattr(bot, "warnings"):
            bot.warnings = defaultdict(int)

        self.user_messages = defaultdict(lambda: deque(maxlen=5))  # Track last 5 messages
        self.muted_users = set()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        now = time.time()
        user_id = message.author.id
        self.user_messages[user_id].append((message.content, now))

        # Spam detection: repeated messages or very fast messages
        if self.is_spamming(user_id):
            await self.warn_user(message)

    def is_spamming(self, user_id):
        msgs = self.user_messages[user_id]
        if len(msgs) < 5:
            return False

        # Check if all 5 messages were within 5 seconds
        if msgs[-1][1] - msgs[0][1] < 5:
            return True

        # Check if all 5 messages are identical
        contents = [msg[0] for msg in msgs]
        if len(set(contents)) == 1:
            return True

        return False

    async def warn_user(self, message):
        user = message.author
        guild = message.guild

        # Use shared warnings dict
        warnings = self.bot.warnings

        if warnings[user.id] >= 10:
            return  # Already banned or maxed

        warnings[user.id] = min(warnings[user.id] + 1, 10)
        count = warnings[user.id]

        await message.channel.send(f"⚠️ {user.mention}, please stop spamming! Warning `{count}`/10.")

        if count == 10:
            try:
                await guild.ban(user, reason="Too many warnings (10)")
                await message.channel.send(f"⛔ {user.mention} has been **banned** for reaching 10 warnings.")
            except:
                pass

        elif count == 5:
            try:
                await guild.kick(user, reason="Too many warnings (5)")
                await message.channel.send(f"👢 {user.mention} has been **kicked** for reaching 5 warnings.")
            except:
                pass

        elif count >= 3 and user.id not in self.muted_users:
            try:
                self.muted_users.add(user.id)
                await user.timeout(duration=60, reason="Spamming (Auto-mute)")  # timeout for 60 seconds
                await message.channel.send(f"🔇 {user.mention} has been temporarily muted (60s).")
                await asyncio.sleep(60)
                self.muted_users.discard(user.id)
            except:
                pass

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
    print("📦 Loaded automod cog.")