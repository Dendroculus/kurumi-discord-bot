from discord.ext import commands
from discord import app_commands, Interaction


handled_errors = set()

def make_key(ctx_or_interaction, is_slash=False):
    guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else 0
    user_id = ctx_or_interaction.user.id if is_slash else ctx_or_interaction.author.id
    command_name = str(ctx_or_interaction.command) if is_slash else str(ctx_or_interaction.command)
    return (guild_id, user_id, command_name, is_slash)  # include is_slash to separate domains

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        key = make_key(ctx, is_slash=False)
        if key in handled_errors:
            return
        handled_errors.add(key)

        if isinstance(error, commands.HybridCommandError):
            return  

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument.")
        elif isinstance(error, commands.CommandNotFound):
            if not ctx.message.content.startswith("/"):
                await ctx.send("❌ Unknown command.")
        else:
            await ctx.send("❌ Unexpected error.")
            print(error)

        handled_errors.remove(key)  

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        key = make_key(interaction, is_slash=True)
        if key in handled_errors:
            return
        handled_errors.add(key)

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        elif isinstance(error, app_commands.CommandInvokeError):
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
            print(error.original)
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message("❌ Invalid argument.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Unexpected slash command error.", ephemeral=True)
            print(error)

        handled_errors.remove(key)  


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    print("📦 Loaded error handler cog.")

