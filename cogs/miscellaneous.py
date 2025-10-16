import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import aiohttp

ANILIST_API = "https://graphql.anilist.co"

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
        if ctx.interaction:
            await ctx.defer()
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
        if ctx.interaction:
            await ctx.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐶 Woof!", color=discord.Color.purple())
                    embed.set_image(url=data["message"])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Couldn't fetch a dog right now.", ephemeral=True)
                    
    @commands.hybrid_command(name="rabbits", help="Miscellaneous: Get a random rabbit image")
    async def rabbits(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rabbit-api-two.vercel.app/api/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐰 Cluck!", color=discord.Color.purple())
                    embed.set_image(url=data["url"])    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Couldn't fetch a rabbit right now.", ephemeral=True)
                    
    @commands.hybrid_command(name="anime", help="Miscellaneous: Search for an anime by name (AniList)")
    async def anime(self, ctx: commands.Context, *, query: str):
        if ctx.interaction:
            await ctx.defer()

        query_str = """
        query ($search: String) {
        Page(perPage: 5) {
            media(search: $search, type: ANIME) {
            id
            title {
                romaji
                english
                native
            }
            description(asHtml: false)
            episodes
            status
            duration
            startDate { year month day }
            endDate { year month day }
            season
            averageScore
            popularity
            favourites
            format
            source
            studios(isMain: true) {
                nodes {
                name
                }
            }
            genres
            coverImage {
                large
                medium
            }
            bannerImage
            siteUrl
            }
        }
        }
        """

        variables = {"search": query}

        async with aiohttp.ClientSession() as session:
            async with session.post(ANILIST_API, json={"query": query_str, "variables": variables}) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch anime info right now.")
                data = await resp.json()

        results = data.get("data", {}).get("Page", {}).get("media", [])
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        # Build select menu options
        options = []
        for anime in results:
            title = anime["title"]["english"] or anime["title"]["romaji"]
            episodes = anime.get("episodes") or "N/A"
            season = anime.get("season") or "N/A"
            options.append(discord.SelectOption(
                label=title[:100],
                description=f"Episodes: {episodes} | Season: {season}"[:100],
                value=str(anime["id"])
            ))

        async def select_callback(interaction: discord.Interaction):
            anime_id = int(interaction.data["values"][0])
            anime_data = next(a for a in results if a["id"] == anime_id)

            title = anime_data["title"]["english"] or anime_data["title"]["romaji"]
            url = anime_data.get("siteUrl")
            description = anime_data.get("description") or "No description available."
            description = description.replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
            if len(description) > 4096:
                description = description[:4093] + "..."

            embed = discord.Embed(
                title=title,
                url=url,
                description=description,
                color=discord.Color.blurple()
            )

            if anime_data.get("coverImage", {}).get("medium"):
                embed.set_thumbnail(url=anime_data["coverImage"]["medium"])

            if anime_data.get("bannerImage"):
                embed.set_image(url=anime_data["bannerImage"])

            embed.add_field(name="Episodes", value=anime_data.get("episodes", "N/A"), inline=True)
            embed.add_field(name="Status", value=anime_data.get("status", "N/A").title(), inline=True)

            start = anime_data.get("startDate", {})
            end = anime_data.get("endDate", {})
            start_str = f"{start.get('year','N/A')}-{start.get('month','??')}-{start.get('day','??')}" if start.get("year") else "N/A"
            end_str = f"{end.get('year','N/A')}-{end.get('month','??')}-{end.get('day','??')}" if end.get("year") else "N/A"
            embed.add_field(name="Start Date", value=start_str, inline=True)
            embed.add_field(name="End Date", value=end_str, inline=True)

            embed.add_field(name="Duration", value=f"{anime_data.get('duration', 'N/A')} min/ep", inline=True)
            embed.add_field(name="Studio", value=anime_data["studios"]["nodes"][0]["name"] if anime_data["studios"]["nodes"] else "N/A", inline=True)
            embed.add_field(name="Source", value=anime_data.get("source", "N/A"), inline=True)

            embed.add_field(name="Score", value=f"{anime_data.get('averageScore', 'N/A')}%", inline=True)
            embed.add_field(name="Popularity", value=str(anime_data.get('popularity', "N/A")), inline=True)
            embed.add_field(name="Favourites", value=str(anime_data.get('favourites', "N/A")), inline=True)
            genres = anime_data.get("genres", [])
            if genres:
                genres = " ".join(f"`{g}`" for g in genres)
            else:
                genres = "N/A"

            embed.add_field(name="Genres", value=genres, inline=False)
            embed.set_footer(
                text="Provided by AniList",
                icon_url="https://anilist.co/img/icons/android-chrome-512x512.png"
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
        if ctx.interaction:
            await ctx.defer()
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

                async with aiohttp.ClientSession() as session2:
                    detail_url = f"https://api.jikan.moe/v4/characters/{mal_id}/full"
                    async with session2.get(detail_url) as resp2:
                        if resp2.status != 200:
                            return await interaction.response.send_message("❌ Could not fetch details.", ephemeral=True)
                        char_data = (await resp2.json()).get("data", {})

                name = char_data.get("name")
                kanji = char_data.get("name_kanji") or "N/A"
                about = char_data.get("about") or ""

                cleaned_lines = []
                for line in about.split("\n"):
                    lower_line = line.lower()
                    if any(k in lower_line for k in ["age:", "height:", "birthday:", "hair color:", "eye color:"]):
                        continue
                    cleaned_lines.append(line.strip())
                desc = " ".join(cleaned_lines)
                desc = desc.replace("<br>", " ").replace("<i>", "").replace("</i>", "")
                if len(desc) > 300:
                    cutoff = desc[:300].rfind(".")
                    desc = desc[:cutoff+1] if cutoff != -1 else desc[:300] + "..."

                fields = {}
                for line in about.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key, val = key.strip().lower(), val.strip()
                        if key in ["age", "birthday", "height", "hair color"]:
                            fields[key.capitalize()] = val

                seiyuu = "N/A"
                for v in char_data.get("voices", []):
                    if v.get("language") == "Japanese":
                        seiyuu = v["person"]["name"]
                        break

                anime_list = [a["anime"]["title"] for a in char_data.get("anime", [])]
                anime_tags = ""
                if anime_list:
                    anime_tags = " ".join([f"`{a}`" for a in anime_list[:4]])
                    if len(anime_list) > 4:
                        anime_tags += " ..."
                else:
                    anime_tags = "`N/A`"

                image_url = char_data.get("images", {}).get("jpg", {}).get("image_url")

                embed = discord.Embed(
                    title=name,
                    description=desc,
                    color=discord.Color.blurple()
                )
                if image_url:
                    embed.set_thumbnail(url=image_url)

                info_left = ""
                if "Age" in fields: info_left += f"**Age:** {fields['Age']}\n"
                if "Height" in fields: info_left += f"**Height:** {fields['Height']}\n"
                if "Birthday" in fields: info_left += f"**Birthday:** {fields['Birthday']}\n"
                if "Hair color" in fields: info_left += f"**Hair Color:** {fields['Hair color']}\n"

                info_right = f"**Kanji:** {kanji}\n**Seiyuu:** {seiyuu}\n"

                if info_left:
                    embed.add_field(name="Info", value=info_left, inline=True)
                if info_right:
                    embed.add_field(name="Details", value=info_right, inline=True)

                embed.add_field(name="📺 Anime Appearances", value=anime_tags, inline=False)

                embed.set_footer(
                    text="Provided by Jikan API",
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
