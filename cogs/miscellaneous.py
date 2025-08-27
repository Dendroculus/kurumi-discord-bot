import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="avatar", help="Miscellaneous: Show avatar of a user")
    @app_commands.describe(user="The user to get the avatar of. Defaults to you.")
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        target = user or ctx.author
        embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.purple())
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="cats", help="Miscellaneous: Shows a random cat image")
    async def cats(self, ctx: commands.Context):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐱 Meow!", color=discord.Color.purple())
                    embed.set_image(url=data[0]["url"])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("😿 Couldn't fetch a cat right now.", ephemeral=True)

    @commands.hybrid_command(name="dogs", help="Miscellaneous: Get a random dog image")
    async def dogs(self, ctx: commands.Context):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐶 Woof!", color=discord.Color.purple())
                    embed.set_image(url=data["message"])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Couldn't fetch a dog right now.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Misc(bot))
    print("📦 Loaded miscellaneous cog.")