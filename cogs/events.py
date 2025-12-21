import discord
from discord.ext import commands
from better_profanity import profanity
import io
import time
from typing import Optional
import logging
from constants.configs import WELCOME_CHANNEL_NAME, ASSETS_DIR
import asyncio

"""
events.py

Event handling cog for the Kurumi Discord bot.

Responsibilities:
- Handle bot lifecycle events (on_ready) and member join/welcome flow.
- Monitor messages for profanity and delete offending messages.
- Respond to DMs and mentions with configurable cooldowns and optional GIF assets.
- Preloads small binary assets (GIFs) from a configured assets directory to avoid
  file I/O on every event.

Integration expectations:
- utils.config must provide ASSETS_DIR (path-like), WELCOME_CHANNEL_NAME, and other configuration values.
- better_profanity.profanity is used to detect profanity in messages.
- The bot is expected to be a discord.ext.commands.Bot instance with application commands available for sync.
"""

class Events(commands.Cog):
    """
    Cog that handles various Discord events: ready, member join, and message handling.

    Key behaviors:
    - Preloads assets (GIFs) referenced by key names ("welcome", "mention", "dm") into memory.
    - Enforces per-user and per-channel cooldowns to avoid spamming responses for mentions and DMs.
    - Deletes messages that contain profanity and notifies the user in-channel.
    - Replies to direct messages with a private "this bot is for servers only" response.
    - Replies to mentions with a friendly embed and optional GIF.

    Attributes:
        bot: the bot instance.
        mention_cooldown / dm_cooldown / global_cooldown / channel_cooldown:
            cooldown durations (in seconds) for different response types.
        mention_cooldowns, dm_cooldowns, global_cooldowns, channel_cooldowns:
            dicts mapping IDs to last-response timestamps.
        gifs: mapping of asset key -> bytes for preloaded GIFs.
        logger: logger instance used for diagnostics.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialize the Events cog.

        Args:
            bot: The Bot instance this cog will be attached to.
        """
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
        self.logger = logging.getLogger("bot")
        self._preload_assets()

    def _preload_assets(self) -> None:
        """
        Load configured asset files into memory.

        Looks up file names relative to config.ASSETS_DIR. Missing assets are logged
        at WARNING level; unexpected errors during load are logged at ERROR level.
        """
        base_path = ASSETS_DIR
        files = {
            "welcome": "kurumi1.gif",
            "mention": "kurumi2.gif",
            "dm": "kurumi3.gif",
        }
        for key, fname in files.items():
            path = base_path / fname
            try:
                with open(path, "rb") as f:
                    self.gifs[key] = f.read()
            except FileNotFoundError:
                self.logger.warning("Asset missing: %s (key=%s)", path, key)
            except Exception as e:
                self.logger.exception("Error loading asset %s: %s", path, e)

    def _file_from_bytes(self, name: str, bytes_data: bytes) -> discord.File:
        """
        Create a discord.File from in-memory bytes.

        Args:
            name: filename to present to Discord clients.
            bytes_data: raw bytes to wrap.

        Returns:
            discord.File: file object suitable for sending in messages.
        """
        return discord.File(io.BytesIO(bytes_data), filename=name)

    def _now(self) -> float:
        """Return the current time as a float timestamp (wrapper around time.time)."""
        return time.time()

    def _update_global(self, user_id: int) -> None:
        """Record the current time as the last global response time for a user."""
        self.global_cooldowns[user_id] = self._now()

    def can_respond(self, user_id: int, *, is_dm: bool = False, channel_id: Optional[int] = None) -> bool:
        """
        Determine whether the bot should respond to a mention or DM for a specific user.

        Rules:
        - Enforce a per-user global cooldown to prevent bursts across channels.
        - Optionally enforce a per-channel cooldown.
        - Enforce separate cooldowns for mentions vs DMs.
        - If responding is allowed, update relevant cooldown timestamps.

        Args:
            user_id: ID of the user initiating the interaction.
            is_dm: True if this is a direct message; False for mentions.
            channel_id: Optional channel id for per-channel cooldown checks.

        Returns:
            bool: True if the bot may respond, False otherwise.
        """
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
        """
        Event fired when the bot is fully ready.

        - Attempts to set a playful custom activity (silently ignores failures).
        - Logs successful login.
        - Attempts to sync application commands and logs the number synced; unexpected
          errors during sync are logged for investigation.
        """
        try:
            await self.bot.change_presence(activity=discord.CustomActivity(name="ara ara konnichiwa"))
        except Exception:
            pass
        self.logger.info("Logged in as %s", self.bot.user)
        try:
            synced = await self.bot.tree.sync()
            self.logger.info("Synced %d slash commands.", len(synced))
        except Exception as e:
            self.logger.exception("Failed to sync slash commands: %s", e)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Welcome new members in the configured welcome channel.

        If a preloaded welcome GIF exists, the bot sends an embed with the GIF attached;
        otherwise it falls back to a plain text welcome message. Permission errors are
        silently ignored; other exceptions are logged.
        """
        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
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
                self.logger.exception("Failed welcome send: %s", e)
        else:
            try:
                await channel.send(f"Welcome to the server, {member.mention}!")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Central message handler for moderation and simple interactions.

        Behavior:
        - Ignores bot messages.
        - If the message is a recognized command (context valid), does nothing here.
        - For DMs, delegates to _handle_dm.
        - If profanity is detected, attempts to delete the message and notify the user.
        - If the bot is mentioned (and message is not a reply), checks cooldowns and may respond.
        """
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if message.guild is None:
            await self._handle_dm(message)
            return

        # Run the CPU-bound profanity check in a thread to avoid blocking the event loop.
        try:
            contains = await asyncio.to_thread(profanity.contains_profanity, message.content)
        except Exception as e:
            # If the thread-based check raised unexpectedly, log and skip profanity handling.
            self.logger.exception("Profanity check failed: %s", e)
            contains = False

        if contains:
            try:
                await message.delete()
                try:
                    await message.channel.send(f"🚫 {message.author.mention}, watch your language!", delete_after=5)
                except Exception:
                    pass
            except discord.Forbidden:
                pass
            except Exception as e:
                self.logger.exception("Failed to delete profanity message: %s", e)
            return

        if self.bot.user.mentioned_in(message) and not message.reference:
            if self.can_respond(message.author.id, is_dm=False, channel_id=message.channel.id):
                await self._handle_mention(message)

    async def _handle_dm(self, message: discord.Message) -> bool:
        """
        Respond to a direct message with a private embed explaining the bot is server-only.

        Sends a GIF if preloaded; handles Forbidden/HTTP exceptions gracefully and
        returns True when a response was sent or attempted.

        Args:
            message: the DM message received.

        Returns:
            bool: True if a DM response was sent or attempted, False if rate-limited.
        """
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
                self.logger.exception("DM send HTTP error: %s", e)
                return True
            return True
        else:
            try:
                await message.author.send(embed=embed)
            except Exception:
                pass
            return True

    async def _handle_mention(self, message: discord.Message) -> None:
        """
        Reply to a mention in a guild channel with a friendly embed and optional GIF.

        Args:
            message: The message that mentioned the bot.
        """
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
                self.logger.exception("Mention send HTTP error: %s", e)
        else:
            try:
                await message.channel.send(embed=embed)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
    logging.getLogger("bot").info("Loaded events cog.")