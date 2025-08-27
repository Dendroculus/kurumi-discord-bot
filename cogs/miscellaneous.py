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
    @commands.guild_only()
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

                # Build select menu options
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

                async def select_callback(interaction: discord.Interaction):
                    mal_id = interaction.data["values"][0]
                    anime_data = next(a for a in results if str(a["mal_id"]) == mal_id)

                    # Info
                    synopsis = anime_data.get("synopsis") or "No synopsis available."
                    if len(synopsis) > 4096:
                        synopsis = synopsis[:4093] + "..."

                    title = anime_data.get("title")
                    url = anime_data.get("url")

                    embed = discord.Embed(
                        title=title,
                        url=url,
                        description=synopsis,
                        color=discord.Color.blurple()
                    )

                    # Thumbnail (small top-right)
                    image_url = anime_data.get("images", {}).get("jpg", {}).get("image_url")
                    if image_url:
                        embed.set_thumbnail(url=image_url)

                    # Big banner (bottom image)
                    banner_url = anime_data.get("images", {}).get("jpg", {}).get("large_image_url")
                    if banner_url:
                        embed.set_image(url=banner_url)

                    # Fields (like AniList)
                    embed.add_field(name="Episodes", value=anime_data.get("episodes", "N/A"), inline=True)
                    embed.add_field(name="Status", value=anime_data.get("status", "N/A"), inline=True)
                    embed.add_field(name="Aired", value=f"{anime_data.get('aired', {}).get('string', 'N/A')}", inline=True)

                    embed.add_field(name="Studio", value=anime_data.get("studios", [{}])[0].get("name", "N/A"), inline=True)
                    embed.add_field(name="Source", value=anime_data.get("source", "N/A"), inline=True)
                    embed.add_field(name="Score", value=anime_data.get("score", "N/A"), inline=True)

                    # Genres
                    genres = ", ".join([g["name"] for g in anime_data.get("genres", [])]) or "N/A"
                    embed.add_field(name="Genres", value=genres, inline=False)

      
                    embed.set_footer(
                    text="Powered by Jikan API",
                    icon_url="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png"
                    )
                    await interaction.response.edit_message(embed=embed, view=None)

                select = Select(placeholder="Choose an anime...", options=options)
                select.callback = select_callback
                view = View()
                view.add_item(select)

                await ctx.send("Select an anime from the search results:", view=view)
                
    @commands.hybrid_command(name="animecharacter", help="Miscellaneous: Search for an anime character by name")
    @app_commands.describe(query="The name of the anime character to search for")
    async def animecharacter(self, ctx: commands.Context, *, query: str):
        async with aiohttp.ClientSession() as session:
            url = f"https://api.jikan.moe/v4/characters?q={query}&limit=5"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch character info right now.")
                data = await resp.json()
                results = data.get("data")
                if not results:
                    return await ctx.send(f"❌ No results found for `{query}`.")

                options = []
                for char in results:
                    name = char.get("name")
                    kanji = char.get("name_kanji") or "N/A"
                    options.append(discord.SelectOption(
                        label=name[:100],
                        description=f"Kanji: {kanji}"[:100],
                        value=str(char["mal_id"])
                    ))

                async def select_callback(interaction: discord.Interaction):
                    mal_id = interaction.data["values"][0]

                    # Fetch full details
                    async with aiohttp.ClientSession() as session2:
                        detail_url = f"https://api.jikan.moe/v4/characters/{mal_id}/full"
                        async with session2.get(detail_url) as resp2:
                            if resp2.status != 200:
                                return await interaction.response.send_message("❌ Could not fetch details.", ephemeral=True)
                            char_data = (await resp2.json()).get("data", {})

                    name = char_data.get("name")
                    kanji = char_data.get("name_kanji") or "N/A"
                    about = char_data.get("about") or ""

                    # Smart truncation at nearest period before 300 chars
                    desc = about.strip().replace("\n", " ")
                    if len(desc) > 300:
                        cutoff = desc[:300].rfind(".")
                        if cutoff != -1:
                            desc = desc[:cutoff+1]  # keep the period
                        else:
                            desc = desc[:300] + "..."

                    # Extract details
                    fields = {}
                    for line in about.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            key, val = key.strip().lower(), val.strip()
                            if key in ["age", "birthday", "zodiac", "height", "hobbies"]:
                                fields[key.capitalize()] = val

                    # Voice Actor
                    seiyuu = "N/A"
                    for v in char_data.get("voices", []):
                        if v.get("language") == "Japanese":
                            seiyuu = v["person"]["name"]
                            break

                    # Anime appearances
                    anime_list = [a["anime"]["title"] for a in char_data.get("anime", [])]
                    anime_tags = ""
                    if anime_list:
                        anime_tags = " ".join([f"`{a}`" for a in anime_list[:4]])
                        if len(anime_list) > 4:
                            anime_tags += " ..."
                    else:
                        anime_tags = "`N/A`"

                    image_url = char_data.get("images", {}).get("jpg", {}).get("image_url")

                    # AniList-style embed
                    embed = discord.Embed(
                        title=name,
                        description=desc,
                        color=discord.Color.blurple()
                    )

                    # Small thumbnail top right
                    if image_url:
                        embed.set_thumbnail(url=image_url)

                    # Info block like AniList
                    info_left = ""
                    if "Age" in fields: info_left += f"**Age:** {fields['Age']}\n"
                    if "Height" in fields: info_left += f"**Height:** {fields['Height']}\n"
                    if "Birthday" in fields: info_left += f"**Birthday:** {fields['Birthday']}\n"

                    info_right = f"**Kanji:** {kanji}\n**Seiyuu:** {seiyuu}\n"

                    if info_left:
                        embed.add_field(name="Info", value=info_left, inline=True)
                    if info_right:
                        embed.add_field(name="Details", value=info_right, inline=True)

                    # Anime tags at bottom like genres
                    embed.add_field(name="📺 Anime Appearances", value=anime_tags, inline=False)

                    # Footer with MAL icon
                    embed.set_footer(
                        text="Provided by Jikan API • MyAnimeList",
                        icon_url="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png"
                    )

                    await interaction.response.edit_message(embed=embed, view=None)

                select = Select(placeholder="Choose a character...", options=options)
                select.callback = select_callback
                view = View()
                view.add_item(select)
                await ctx.send("🔎 Select a character from the search results:", view=view)


async def setup(bot):
    await bot.add_cog(Misc(bot))
    print("📦 Loaded miscellaneous cog.")
