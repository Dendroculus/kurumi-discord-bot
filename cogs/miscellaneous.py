import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
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
                    
    @commands.hybrid_command(name="anime", help="Miscellaneous: Search for an anime by name")
    @app_commands.describe(query="The name of the anime to search for")
    async def anime(self, ctx: commands.Context, *, query: str):
        """Fetch anime info from MyAnimeList via Jikan API"""
        async with aiohttp.ClientSession() as session:
            url = f"https://api.jikan.moe/v4/anime?q={query}&limit=5"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch anime info right now.")
                data = await resp.json()
                results = data.get("data")
                if not results:
                    return await ctx.send(f"❌ No results found for `{query}`.")

                # Build options for select menu
                options = []
                for anime in results:
                    title = anime.get("title")
                    episodes = anime.get("episodes", "N/A")
                    season = anime.get("season") or "N/A"
                    options.append(discord.SelectOption(
                        label=title[:100],
                        description=f"Episodes: {episodes} | Season: {season}"[:100],
                        value=str(anime["mal_id"])
                    ))

                # Define select callback
                async def select_callback(interaction: discord.Interaction):
                    mal_id = interaction.data["values"][0]
                    anime_data = next(a for a in results if str(a["mal_id"]) == mal_id)
                    synopsis = anime_data.get("synopsis") or "No synopsis available"
                    if len(synopsis) > 1024:
                        synopsis = synopsis[:1021] + "..."
                    embed = discord.Embed(
                        title=anime_data.get("title"),
                        url=anime_data.get("url"),
                        description=synopsis,
                        color=discord.Color.purple()
                    )
                    image_url = anime_data.get("images", {}).get("jpg", {}).get("image_url")
                    if image_url:
                        embed.set_thumbnail(url=image_url)
                    embed.add_field(name="Score", value=anime_data.get("score", "N/A"), inline=True)
                    embed.add_field(name="Episodes", value=anime_data.get("episodes", "N/A"), inline=True)
                    embed.add_field(name="Status", value=anime_data.get("status", "N/A"), inline=True)
                    await interaction.response.edit_message(embed=embed, view=None)

                # Create select menu
                select = Select(placeholder="Choose an anime...", options=options)
                select.callback = select_callback
                view = View()
                view.add_item(select)
                await ctx.send("Select an anime from the search results:", view=view)

async def setup(bot):
    await bot.add_cog(Misc(bot))
    print("📦 Loaded miscellaneous cog.")
