import traceback
import uuid
import time
import logging
from discord.ext import commands
from discord import app_commands, Interaction

# In-memory debounce cache
handled_errors = {}
logger = logging.getLogger("bot")

"""
errors.py

Centralized error handling cog for the bot.

Responsibilities:
- Deduplicate and debounce repetitive errors to avoid spamming users or logs.
- Provide friendly user-facing messages with unique error codes for debugging.
- Log unexpected/unhandled errors with full tracebacks for diagnosis.

Important notes:
- `handled_errors` is an in-memory map used to suppress repeated identical errors for a short TTL.
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
    # Clean up stale keys
    keys_to_remove = [k for k, t in handled_errors.items() if now - t > ttl]
    for k in keys_to_remove:
        del handled_errors[k]

    if key in handled_errors and now - handled_errors[key] < ttl:
        return True
    handled_errors[key] = now
    return False


class ErrorHandler(commands.Cog):
    """
    Cog responsible for catching command and application command errors and responding appropriately.

    Behavior:
    - Listens to both text-command errors (on_command_error) and application/slash command errors.
    - Uses is_handled to debounce repeated errors.
    - Generates a unique UUID error code for unexpected exceptions to help track logs.
    - Logs full tracebacks for unexpected errors.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Listener for errors raised by text/hybrid commands.
        """
        # Ignore if command has its own error handler
        if hasattr(ctx.command, 'on_error'):
            return

        # Get original exception if available
        error = getattr(error, 'original', error)
        
        # Debounce key
        key = (ctx.guild.id if ctx.guild else 0, ctx.author.id, str(ctx.command))
        if is_handled(key):
            return

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("🚫 I don’t have the required permissions for that.")
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`.")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Check your input.")
            return

        error_code = uuid.uuid4().hex[:8]
        logger.error(f"Unexpected Error [{error_code}] in command '{ctx.command}': {error}")
        logger.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))
        
        await ctx.send(f"❌ An unexpected error occurred. Error Code: `{error_code}`")

    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """
        Listener for errors raised by application (slash) commands.
        """
        original_error = getattr(error, 'original', error)

        key = (interaction.guild.id if interaction.guild else 0, interaction.user.id, str(interaction.command))
        if is_handled(key):
            return

        if isinstance(error, app_commands.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.followup.send("🚫 You don't have permission to use this command.", ephemeral=True)
            return

        if isinstance(error, app_commands.TransformerError):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Invalid argument. Check your input.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Invalid argument. Check your input.", ephemeral=True)
            return

        error_code = uuid.uuid4().hex[:8]
        logger.error(f"Unexpected Slash Command Error [{error_code}]: {original_error}")
        logger.error("".join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__)))

        msg = f"❌ An unexpected error occurred. Error Code: `{error_code}`"
        
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    bot.tree.on_error = ErrorHandler(bot).on_app_command_error
    logger.info("Loaded errors cog.")