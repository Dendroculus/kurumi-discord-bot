import discord
from discord.ext import commands
from better_profanity import profanity
import io
import time
from typing import Optional
import logging
import random
from constants.configs import WELCOME_CHANNEL_NAME, GIF_ATTACHMENTS_URL, GIF_ASSETS
from constants.emojis import KurumiEmojis
import asyncio
from constants.assets import AssetService

"""
events.py

Event handling cog for the Kurumi Discord bot.

Responsibilities:
- Handle bot lifecycle events (on_ready) and member join/welcome flow.
- Monitor messages for profanity and delete offending messages.
- Respond to DMs and mentions with configurable cooldowns and optional GIF assets.
- Delegates asset loading to AssetService.

Integration expectations:
- utils.config must provide WELCOME_CHANNEL_NAME, and other configuration values.
- utils.assets.AssetService is used to retrieve binary assets.
- better_profanity.profanity is used to detect profanity in messages.
- The bot is expected to be a discord.ext.commands.Bot instance with application commands available for sync.
"""

class Events(commands.Cog):
    """
    Cog that handles various Discord events: ready, member join, and message handling.

    Key behaviors:
    - Uses AssetService to retrieve GIFs referenced by key names ("welcome", "mention", "dm").
    - Enforces per-user and per-channel cooldowns to avoid spamming responses for mentions and DMs.
    - Deletes messages that contain profanity and notifies the user in-channel.
    - Replies to direct messages with a private "this bot is for servers only" response.
    - Replies to mentions with a friendly embed and optional GIF.

    Attributes:
        bot: the bot instance.
        asset_service: Service for retrieving binary assets.
        mention_cooldown / dm_cooldown / global_cooldown / channel_cooldown:
            cooldown durations (in seconds) for different response types.
        mention_cooldowns, dm_cooldowns, global_cooldowns, channel_cooldowns:
            dicts mapping IDs to last-response timestamps.
        logger: logger instance used for diagnostics.
    """
    def __init__(self, bot: commands.Bot, asset_service: Optional[AssetService] = None):
        """
        Initialize the Events cog.

        Args:
            bot: The Bot instance this cog will be attached to.
            asset_service: Optional AssetService instance (dependency injection). 
                           If None, a new instance is created.
        """
        self.bot = bot
        self.asset_service = asset_service or AssetService()

        self.mention_cooldown = 30
        self.dm_cooldown = 3600
        self.global_cooldown = 2
        self.channel_cooldown = 10
        self.MAX_CACHE_SIZE = 5000

        self.mention_cooldowns: dict[int, float] = {}
        self.dm_cooldowns: dict[int, float] = {}
        self.global_cooldowns: dict[int, float] = {}
        self.channel_cooldowns: dict[int, float] = {}

        self.logger = logging.getLogger("bot")
        
    def _purge_dict(self, target_dict: dict, cooldown: float, current_time: float):
        """Helper to remove expired keys from a specific dictionary."""
        # Create a list of keys to delete first (safely iterating while modifying)
        expired = [k for k, v in target_dict.items() if current_time - v > cooldown]
        for k in expired:
            del target_dict[k]
            
    def _cleanup_expired(self, current_time: float):
        """Randomly cleans up expired keys to save memory."""
        self._purge_dict(self.mention_cooldowns, self.mention_cooldown, current_time)
        self._purge_dict(self.dm_cooldowns, self.dm_cooldown, current_time)
        self._purge_dict(self.global_cooldowns, self.global_cooldown, current_time)
        self._purge_dict(self.channel_cooldowns, self.channel_cooldown, current_time)

    def _enforce_max_size(self):
        """Emergency clear if the bot is being raided."""
        if len(self.mention_cooldowns) > self.MAX_CACHE_SIZE:
            self.mention_cooldowns.clear()
            self.global_cooldowns.clear()
            self.dm_cooldowns.clear()
            self.channel_cooldowns.clear()
            self.logger.warning("Cache hit max size! Forced clear performed.")

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
        
        if random.random() < 0.05:
            self._cleanup_expired(now)
        
        if len(self.mention_cooldowns) > self.MAX_CACHE_SIZE:  
            self._enforce_max_size()

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

    async def _send_response(self, destination, content=None, embed=None, file=None) -> bool:
        """
        Sends a message using the _handle_mention logic.
        """
        try:
            await destination.send(content=content, embed=embed, file=file)
            return True
        except discord.Forbidden:
            return False
        except discord.HTTPException as e:
            self.logger.exception(f"HTTP error sending to {destination}: {e}")
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
        Responds to a new member joining by sending a welcome message to the configured channel.

        Logic:
        - Locates the welcome channel by name (defined in WELCOME_CHANNEL_NAME).
        - If the 'welcome' GIF asset is available via AssetService, constructs a rich embed.
        - If the GIF asset is missing, falls back to a simple text-based welcome message.
        - Utilizes `_send_response` to safely handle message delivery and suppress permission errors.
        """
        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if not channel:
            return

        gif = self.asset_service.get_asset("welcome")
        if gif:
            file = self._file_from_bytes(GIF_ASSETS["Kurumi_1"], gif)
            embed = discord.Embed(
                title=f"{KurumiEmojis['KurumiLove']} Welcome!", 
                description=f"Welcome to the server, {member.mention}!", 
                color=discord.Color.purple()
            )
            embed.set_image(url=GIF_ATTACHMENTS_URL["Kurumi_URL_1"])
            
            await self._send_response(channel, embed=embed, file=file)
        else:
            await self._send_response(channel, content=f"Welcome to the server, {member.mention}!")
            
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
        Handles direct message interactions by enforcing cooldowns and sending a standard reply.

        Logic:
        - Checks the DM cooldown via `can_respond`. Returns False immediately if rate-limited.
        - Constructs a 'Private Server Only' embed to inform the user of bot limitations.
        - If the 'dm' GIF asset is available via AssetService, attaches it to the response.
        - Uses `_send_response` to handle delivery and exceptions.
        - Returns True if the logic proceeded to an attempted send.
        """
        if not self.can_respond(message.author.id, is_dm=True):
            return False

        gif = self.asset_service.get_asset("dm")
        embed = discord.Embed(
            title="Private Server Only",
            description="This bot is only available for private servers. Please contact the owner to invite it.",
            color=discord.Color.purple()
        )

        if gif:
            file = self._file_from_bytes(GIF_ASSETS["Kurumi_3"], gif)
            embed.set_image(url=GIF_ATTACHMENTS_URL["Kurumi_URL_3"])
            await self._send_response(message.author, embed=embed, file=file)
        else:
            await self._send_response(message.author, embed=embed)
            
        return True

    async def _handle_mention(self, message: discord.Message) -> None:
        """
        Responds to bot mentions in text channels with a greeting and visual asset.

        Logic:
        - Fetches the 'mention' GIF asset via AssetService if available.
        - Creates a friendly greeting embed.
        - Attaches the GIF if present, linking it via `GIF_ATTACHMENTS_URL`.
        - Delegates the actual sending to `_send_response` to manage permissions and HTTP errors safely.
        """
        gif = self.asset_service.get_asset("mention")
        embed = discord.Embed(description="Hello there, how can I help you today Master? ✨", color=discord.Color.purple())

        if gif:
            file = self._file_from_bytes(GIF_ASSETS["Kurumi_2"], gif)
            embed.set_image(url=GIF_ATTACHMENTS_URL["Kurumi_URL_2"])
            await self._send_response(message.channel, embed=embed, file=file)
        else:
            await self._send_response(message.channel, embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
    logging.getLogger("bot").info("Loaded events cog.")