import discord
from discord.ext import commands
from discord import app_commands
from better_profanity import profanity

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.CustomActivity(name="ara ara konnichiwa"))
        print(f'✅ Logged in as {self.bot.user}')

        try:
            synced = await self.bot.tree.sync()
            print(f"🔄 Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(member.guild.text_channels, name="💬general")
        if not channel:
            return

        try:
            with open("assets/kurumi1.gif", "rb") as f:
                file = discord.File(f, filename="kurumi1.gif")
                embed = discord.Embed(
                    title="💖 Welcome!",
                    description=f"Welcome to the server, {member.mention}!",
                    color=discord.Color.purple()
                )
                embed.set_image(url="attachment://kurumi1.gif")
                await channel.send(file=file, embed=embed)
        except FileNotFoundError:
            print("❌ kurumi1.gif not found for welcome message.")
        except Exception as e:
            print(f"❌ Failed to send welcome message: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # DMs
        if message.guild is None:
            try:
                with open("assets/kurumi3.gif", "rb") as gif:
                    file = discord.File(gif, filename="kurumi3.gif")
                    embed = discord.Embed(
                        title="Private Server Only",
                        description="😉 This bot is only available for private servers. Please contact the owner to invite it.",
                        color=discord.Color.purple()
                    )
                    embed.set_image(url="attachment://kurumi3.gif")
                    await message.author.send(embed=embed, file=file)
            except discord.Forbidden:
                pass
            return

        # Profanity
        if profanity.contains_profanity(message.content):
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention}, watch your language!", delete_after=5)
            return

        # Mention without reply
        if self.bot.user.mentioned_in(message) and not message.reference:
            try:
                with open("assets/kurumi2.gif", "rb") as gif:
                    file = discord.File(gif, filename="kurumi2.gif")
                    embed = discord.Embed(
                        description="Hello there, how can I help you today Master? ✨",
                        color=discord.Color.purple()
                    )
                    embed.set_image(url="attachment://kurumi2.gif")
                    await message.channel.send(file=file, embed=embed)
            except FileNotFoundError:
                await message.channel.send("Hello there, how can I help you today Master? ✨ (Image not found)")
            return

        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Check your input.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Unknown command. Use `!commands` to see available commands.")
        elif isinstance(error, commands.HybridCommandError) and isinstance(error.original, app_commands.CommandInvokeError):
            await ctx.send("❌ An error occurred with this slash command.")
            print(error.original.original)
        else:
            print(f"Unhandled error in '{ctx.command}': {error}")
            await ctx.send("❌ An unexpected error occurred.")

    @commands.Cog.listener()
    async def block_dms(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("❌ This bot can only be used in servers.")
            return False
        return True


async def setup(bot):
    await bot.add_cog(Events(bot))
    print("📦 Loaded Events cog.")
