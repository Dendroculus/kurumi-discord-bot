from discord.ext import commands
from discord import app_commands, Interaction
import time
import logging

handled_errors = {}
logger = logging.getLogger("bot")

"""
errors.py

Centralized error handling cog for the bot.

Responsibilities:
- Deduplicate and debounce repetitive errors to avoid spamming users or logs.
- Provide friendly user-facing messages for common command and application command errors.
- Log unexpected/unhandled errors for diagnosis.

Important notes:
- `handled_errors` is an in-memory map used to suppress repeated identical errors for a short TTL.
- This module intentionally only handles presentation and logging; escalation or user banning is not performed here.
"""

def is_handled(key, ttl=60):
    """
    Determine whether a specific error (identified by `key`) has been handled recently.

    The function cleans up stale entries older than `ttl` seconds, checks if the
    provided key exists and was recorded within the TTL, and records the current
    time for the key if it was not already recent.

    Args:
        key: Hashable identifier for the error event (e.g., tuple containing guild/user/command).
        ttl: Time-to-live in seconds for suppression; defaults to 60 seconds.

    Returns:
        bool: True if the key was recently handled (and should be suppressed), False otherwise.
    """
    now = time.time()
    handled_errors.update({k: t for k, t in handled_errors.items() if now - t < ttl})

    if key in handled_errors and now - handled_errors[key] < ttl:
        return True
    handled_errors[key] = now
    return False


class ErrorHandler(commands.Cog):
    """
    Cog responsible for catching command and application command errors and responding appropriately.

    Behavior:
    - Listens to both text-command errors (on_command_error) and application/slash command errors (on_app_command_error).
    - Uses is_handled to debounce repeated errors identified by a key derived from guild/user/command.
    - Sends user-friendly ephemeral or channel messages for common error types (missing perms, bad args, etc.).
    - Logs unexpected exceptions for operators to investigate.

    The cog does not modify or reroute exceptions beyond logging and notifying users.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Listener for errors raised by text/hybrid commands.

        Args:
            ctx: Command context where the error occurred.
            error: The raised exception instance.
        """
        key = (ctx.guild.id if ctx.guild else 0, ctx.author.id, str(ctx.command))
        if is_handled(key):
            return

        if isinstance(error, commands.HybridCommandError):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("🚫 I don’t have the required permissions for that.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Check your input.")
        elif isinstance(error, commands.CommandNotFound):
            return
        else:
            await ctx.send("❌ An unexpected error occurred.")
            logger.exception("Unhandled error in '%s': %s", ctx.command, error)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """
        Listener for errors raised by application (slash) commands.

        Args:
            interaction: The Interaction that triggered the command.
            error: The raised AppCommandError instance.
        """
        key = (interaction.guild.id if interaction.guild else 0, interaction.user.id, str(interaction.command))
        if is_handled(key):
            return

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 You don't have permission to use this command.", ephemeral=True
            )
        elif isinstance(error, app_commands.CommandInvokeError):
            await interaction.response.send_message(
                "❌ Something went wrong with this slash command.", ephemeral=True
            )
            logger.exception("Slash command error", exc_info=getattr(error, "original", error))
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(
                "❌ Invalid argument. Check your input.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ An unexpected slash command error occurred.", ephemeral=True
            )
            logger.exception("Unhandled slash error", exc_info=error)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    logger.info("Loaded errors cog.")