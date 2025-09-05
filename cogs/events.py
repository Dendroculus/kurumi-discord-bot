import discord
from discord.ext import commands
from discord import app_commands
from better_profanity import profanity
import os

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
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "kurumi1.gif")
        try:
            with open(file_path, "rb") as f:
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
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "kurumi3.gif")
            try:
                with open(file_path, "rb") as gif:
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
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "kurumi2.gif")
            try:
                with open(file_path, "rb") as gif:
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
    async def on_message(self, message: discord.Message):
        return

    
async def setup(bot):
    await bot.add_cog(Events(bot))
    print("📦 Loaded Events cog.")


