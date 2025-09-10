from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import time
import sqlite3
import os

COG_PATH = os.path.dirname(os.path.abspath(__file__))  
ROOT_PATH = os.path.dirname(COG_PATH)                  
DB_PATH = os.path.join(ROOT_PATH, "data", "automod.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(lambda: deque(maxlen=5))  # last 5 messages
        self.muted_users = set()
        self.recently_warned = set()  # prevent duplicate spam triggers
        self.conn = sqlite3.connect(DB_PATH)
        self.c = self.conn.cursor()
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """)
        self.conn.commit()

    async def on_message_warn(self, user_id: int, guild_id: int):
        self.c.execute("""
        INSERT INTO warnings (user_id, guild_id, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, guild_id) DO UPDATE SET count = count + 1
        """, (user_id, guild_id))
        self.conn.commit()

        self.c.execute("SELECT count FROM warnings WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        count = self.c.fetchone()[0]
        return min(count, 10)

    async def get_warnings(self, user_id: int, guild_id: int):
        self.c.execute("SELECT count FROM warnings WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        result = self.c.fetchone()
        return result[0] if result else 0

    async def reset_warnings(self, user_id: int, guild_id: int):
        self.c.execute("UPDATE warnings SET count=0 WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        self.conn.commit()

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
                asyncio.create_task(self.clear_recent_warn(guild_id, user_id))

    async def clear_recent_warn(self, guild_id, user_id):
        await asyncio.sleep(5)
        self.recently_warned.discard((guild_id, user_id))

    def is_spamming(self, user_id):
        msgs = self.user_messages[user_id]
        if len(msgs) < 5:
            return False

        if msgs[-1][1] - msgs[0][1] < 5:
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

        await message.channel.send(f"⚠️ {user.mention}, please stop spamming! Warning `{count}`/10.")

        try:
            if count >= 3 and user_id not in self.muted_users:
                self.muted_users.add(user_id)
                await user.timeout(duration=60, reason="Spamming (Auto-mute)")
                await message.channel.send(f"🔇 {user.mention} has been temporarily muted (60s).")
                asyncio.create_task(self.clear_muted(user_id, 60))

            if count == 5:
                await guild.kick(user, reason="Too many warnings (5)")
                await message.channel.send(f"👢 {user.mention} has been **kicked** for reaching 5 warnings.")

            if count == 10:
                await guild.ban(user, reason="Too many warnings (10)")
                await message.channel.send(f"⛔ {user.mention} has been **banned** for reaching 10 warnings.")
        except Exception as e:
            print(f"[Automod Error] Failed action on {user}: {e}")

    async def clear_muted(self, user_id, delay):
        await asyncio.sleep(delay)
        self.muted_users.discard(user_id)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
    print("📦 Loaded automod cog.")
