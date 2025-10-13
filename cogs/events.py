import discord
from discord.ext import commands
from better_profanity import profanity
import os
import io
import time
from typing import Optional

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.mention_cooldown = 30       
        self.dm_cooldown = 3600          
        self.global_cooldown = 2         
        self.channel_cooldown = 10      

        self.mention_cooldowns: dict[int, float] = {}
        self.dm_cooldowns: dict[int, float] = {}
        self.global_cooldowns: dict[int, float] = {}
        self.channel_cooldowns: dict[int, float] = {}

        self.gifs: dict[str, bytes] = {}
        self._preload_assets()

    def _preload_assets(self) -> None:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        files = {
            "welcome": "kurumi1.gif",
            "mention": "kurumi2.gif",
            "dm": "kurumi3.gif",
        }
        for key, fname in files.items():
            path = os.path.join(base_path, fname)
            try:
                with open(path, "rb") as f:
                    self.gifs[key] = f.read()
            except FileNotFoundError:
                print(f"❌ Asset missing: {path} (key={key})")
            except Exception as e:
                print(f"❌ Error loading asset {path}: {e}")

    def _file_from_bytes(self, name: str, bytes_data: bytes) -> discord.File:
        return discord.File(io.BytesIO(bytes_data), filename=name)

    def _now(self) -> float:
        return time.time()

    def _update_global(self, user_id: int) -> None:
        self.global_cooldowns[user_id] = self._now()

    def can_respond(self, user_id: int, *, is_dm: bool = False, channel_id: Optional[int] = None) -> bool:
        now = self._now()

        last_global = self.global_cooldowns.get(user_id, 0)
        if now - last_global < self.global_cooldown:
            return False

        if channel_id is not None:
            last_chan = self.channel_cooldowns.get(channel_id, 0)
            if now - last_chan < self.channel_cooldown:
                return False

        if is_dm:
            last = self.dm_cooldowns.get(user_id, 0)
            allowed = (now - last) >= self.dm_cooldown
        else:
            last = self.mention_cooldowns.get(user_id, 0)
            allowed = (now - last) >= self.mention_cooldown

        if allowed:
            self._update_global(user_id)
            if channel_id is not None:
                self.channel_cooldowns[channel_id] = now
            if is_dm:
                self.dm_cooldowns[user_id] = now
            else:
                self.mention_cooldowns[user_id] = now
            return True

        return False

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.bot.change_presence(activity=discord.CustomActivity(name="ara ara konnichiwa"))
        except Exception:
            pass
        print(f"✅ Logged in as {self.bot.user}")
        try:
            synced = await self.bot.tree.sync()
            print(f"🔄 Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(member.guild.text_channels, name="💬-general")
        if not channel:
            return

        gif = self.gifs.get("welcome")
        if gif:
            file = self._file_from_bytes("kurumi1.gif", gif)
            embed = discord.Embed(title="💖 Welcome!", description=f"Welcome to the server, {member.mention}!", color=discord.Color.purple())
            embed.set_image(url="attachment://kurumi1.gif")
            try:
                await channel.send(file=file, embed=embed)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"❌ Failed welcome send: {e}")
        else:
            try:
                await channel.send(f"Welcome to the server, {member.mention}!")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if message.guild is None:
            await self._handle_dm(message)
            return

        if profanity.contains_profanity(message.content):
            try:
                await message.delete()
                try:
                    await message.channel.send(f"🚫 {message.author.mention}, watch your language!", delete_after=5)
                except Exception:
                    pass
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"❌ Failed to delete profanity message: {e}")
            return

        if self.bot.user.mentioned_in(message) and not message.reference:
            if self.can_respond(message.author.id, is_dm=False, channel_id=message.channel.id):
                await self._handle_mention(message)
            return

    async def _handle_dm(self, message: discord.Message) -> bool:
        if not self.can_respond(message.author.id, is_dm=True):
            return False

        gif = self.gifs.get("dm")
        embed = discord.Embed(
            title="Private Server Only",
            description="😉 This bot is only available for private servers. Please contact the owner to invite it.",
            color=discord.Color.purple()
        )

        if gif:
            file = self._file_from_bytes("kurumi3.gif", gif)
            embed.set_image(url="attachment://kurumi3.gif")
            try:
                await message.author.send(embed=embed, file=file)
            except discord.Forbidden:
                return True
            except discord.HTTPException as e:
                print(f"❌ DM send HTTP error: {e}")
                return True
            return True
        else:
            try:
                await message.author.send(embed=embed)
            except Exception:
                pass
            return True

    async def _handle_mention(self, message: discord.Message) -> None:
        gif = self.gifs.get("mention")
        embed = discord.Embed(description="Hello there, how can I help you today Master? ✨", color=discord.Color.purple())

        if gif:
            file = self._file_from_bytes("kurumi2.gif", gif)
            embed.set_image(url="attachment://kurumi2.gif")
            try:
                await message.channel.send(embed=embed, file=file)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                print(f"❌ Mention send HTTP error: {e}")
        else:
            try:
                await message.channel.send(embed=embed)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
    print("📦 Loaded events cog.")