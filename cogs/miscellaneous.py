import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import aiohttp
from typing import Any, Dict, List, Optional

ANILIST_API = "https://graphql.anilist.co"
ANILIST_SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 5) {
    media(search: $search, type: ANIME) {
      id
      title { romaji english native }
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
      studios(isMain: true) { nodes { name } }
      genres
      coverImage { large medium }
      bannerImage
      siteUrl
    }
  }
}
"""

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _defer_if_slash(ctx: commands.Context) -> None:
        interaction = getattr(ctx, "interaction", None)
        if interaction is not None and not interaction.response.is_done():
            await interaction.response.defer()

    @staticmethod
    def _sanitize(description: str, limit: int = 4096) -> str:
        desc = (description or "No description available.").replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
        if len(desc) > limit:
            return desc[: limit - 3] + "..."
        return desc

    @staticmethod
    def _format_date(d: Dict[str, Optional[int]]) -> str:
        if d and d.get("year"):
            return f"{d.get('year','N/A')}-{d.get('month','??')}-{d.get('day','??')}"
        return "N/A"

    @staticmethod
    def _opt(value: Any, fallback: str = "N/A") -> str:
        return str(value) if value not in (None, "", []) else fallback

    @staticmethod
    def _genres_to_text(genres: List[str]) -> str:
        if not genres:
            return "N/A"
        return " ".join(f"`{g}`" for g in genres)

    @staticmethod
    def _build_anime_embed(anime: Dict[str, Any]) -> discord.Embed:
        title = anime["title"]["english"] or anime["title"]["romaji"]
        url = anime.get("siteUrl")
        description = Misc._sanitize(anime.get("description", ""))

        embed = discord.Embed(title=title, url=url, description=description, color=discord.Color.blurple())

        cover_medium = anime.get("coverImage", {}).get("medium")
        if cover_medium:
            embed.set_thumbnail(url=cover_medium)

        banner = anime.get("bannerImage")
        if banner:
            embed.set_image(url=banner)

        embed.add_field(name="Episodes", value=Misc._opt(anime.get("episodes")), inline=True)
        status = Misc._opt(anime.get("status")).title() if anime.get("status") else "N/A"
        embed.add_field(name="Status", value=status, inline=True)

        start_str = Misc._format_date(anime.get("startDate", {}))
        end_str = Misc._format_date(anime.get("endDate", {}))
        embed.add_field(name="Start Date", value=start_str, inline=True)
        embed.add_field(name="End Date", value=end_str, inline=True)

        embed.add_field(name="Duration", value=f"{Misc._opt(anime.get('duration'))} min/ep", inline=True)
        studio = anime.get("studios", {}).get("nodes", [])
        embed.add_field(name="Studio", value=studio[0]["name"] if studio else "N/A", inline=True)
        embed.add_field(name="Source", value=Misc._opt(anime.get("source")), inline=True)

        embed.add_field(name="Score", value=f"{Misc._opt(anime.get('averageScore'))}%", inline=True)
        embed.add_field(name="Popularity", value=Misc._opt(anime.get("popularity")), inline=True)
        embed.add_field(name="Favourites", value=Misc._opt(anime.get("favourites")), inline=True)

        embed.add_field(name="Genres", value=Misc._genres_to_text(anime.get("genres", [])), inline=False)
        embed.set_footer(text="Provided by AniList", icon_url="https://anilist.co/img/icons/android-chrome-512x512.png")
        return embed

    @staticmethod
    def _anime_options(results: List[Dict[str, Any]]) -> List[discord.SelectOption]:
        options: List[discord.SelectOption] = []
        for anime in results:
            title = anime["title"]["english"] or anime["title"]["romaji"]
            episodes = anime.get("episodes") or "N/A"
            season = anime.get("season") or "N/A"
            options.append(
                discord.SelectOption(
                    label=title[:100],
                    description=f"Episodes: {episodes} | Season: {season}"[:100],
                    value=str(anime["id"]),
                )
            )
        return options

    @commands.hybrid_command(name="avatar", help="Miscellaneous: Show avatar of a user")
    @app_commands.describe(user="The user to get the avatar of. Defaults to you.")
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        target = user or ctx.author
        embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.purple())
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="cats", help="Miscellaneous: Shows a random cat image")
    async def cats(self, ctx: commands.Context):
        await self._defer_if_slash(ctx)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                if resp.status != 200:
                    return await ctx.send("😿 Couldn't fetch a cat right now.", ephemeral=True)
                data = await resp.json()
        embed = discord.Embed(title="🐱 Meow!", color=discord.Color.purple())
        embed.set_image(url=data[0]["url"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dogs", help="Miscellaneous: Get a random dog image")
    async def dogs(self, ctx: commands.Context):
        await self._defer_if_slash(ctx)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Couldn't fetch a dog right now.", ephemeral=True)
                data = await resp.json()
        embed = discord.Embed(title="🐶 Woof!", color=discord.Color.purple())
        embed.set_image(url=data["message"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rabbits", help="Miscellaneous: Get a random rabbit image")
    async def rabbits(self, ctx: commands.Context):
        await self._defer_if_slash(ctx)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rabbit-api-two.vercel.app/api/random") as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Couldn't fetch a rabbit right now.", ephemeral=True)
                data = await resp.json()
        embed = discord.Embed(title="🐰 Cluck!", color=discord.Color.purple())
        embed.set_image(url=data["url"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="anime", help="Miscellaneous: Search for an anime by name (AniList)")
    async def anime(self, ctx: commands.Context, *, query: str):
        await self._defer_if_slash(ctx)

        variables = {"search": query}
        async with aiohttp.ClientSession() as session:
            async with session.post(ANILIST_API, json={"query": ANILIST_SEARCH_QUERY, "variables": variables}) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch anime info right now.")
                data = await resp.json()

        results = data.get("data", {}).get("Page", {}).get("media", []) or []
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        options = self._anime_options(results)

        class AnimeSelectView(View):
            def __init__(self, items: List[discord.SelectOption], entries: List[Dict[str, Any]]):
                super().__init__()
                self.by_id = {str(e["id"]): e for e in entries}
                select = Select(placeholder="Choose an anime...", options=items)
                async def _on_select(interaction: discord.Interaction):
                    anime_id = interaction.data["values"][0]
                    anime_data = self.by_id.get(anime_id)
                    embed = Misc._build_anime_embed(anime_data)
                    await interaction.response.edit_message(embed=embed, view=None)
                select.callback = _on_select
                self.add_item(select)

        await ctx.send("Select an anime from the search results:", view=AnimeSelectView(options, results))

    @commands.hybrid_command(name="animecharacter", help="Miscellaneous: Search for an anime character by name")
    @app_commands.describe(query="The name of the anime character to search for")
    async def animecharacter(self, ctx: commands.Context, *, query: str):
        await self._defer_if_slash(ctx)

        async with aiohttp.ClientSession() as session:
            url = f"https://api.jikan.moe/v4/characters?q={query}&limit=5"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch character info right now.")
                data = await resp.json()

        results = data.get("data") or []
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        options: List[discord.SelectOption] = []
        for char in results:
            name = char.get("name") or "Unknown"
            kanji = char.get("name_kanji") or "N/A"
            options.append(discord.SelectOption(
                label=name[:100],
                description=f"Kanji: {kanji}"[:100],
                value=str(char["mal_id"])
            ))

        class CharacterSelectView(View):
            def __init__(self, items: List[discord.SelectOption]):
                super().__init__()
                select = Select(placeholder="Choose a character...", options=items)
                async def _on_select(interaction: discord.Interaction):
                    mal_id = interaction.data["values"][0]
                    detail_url = f"https://api.jikan.moe/v4/characters/{mal_id}/full"
                    async with aiohttp.ClientSession() as s2:
                        async with s2.get(detail_url) as resp2:
                            if resp2.status != 200:
                                return await interaction.response.send_message("❌ Could not fetch details.", ephemeral=True)
                            char_data = (await resp2.json()).get("data", {}) or {}

                    embed = self._build_character_embed(char_data)
                    await interaction.response.edit_message(embed=embed, view=None)
                select.callback = _on_select
                self.add_item(select)

            @staticmethod
            def _clean_about(about: str) -> str:
                if not about:
                    return ""
                cleaned = []
                for line in about.split("\n"):
                    lower = line.lower()
                    if any(k in lower for k in ["age:", "height:", "birthday:", "hair color:", "eye color:"]):
                        continue
                    cleaned.append(line.strip())
                text = " ".join(cleaned).replace("<br>", " ").replace("<i>", "").replace("</i>", "")
                if len(text) > 300:
                    cut = text[:300].rfind(".")
                    return (text[:cut + 1] if cut != -1 else text[:300]) + ("..." if cut == -1 else "")
                return text

            @staticmethod
            def _extract_fields(about: str) -> Dict[str, str]:
                fields: Dict[str, str] = {}
                if not about:
                    return fields
                for line in about.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key, val = key.strip().lower(), val.strip()
                        if key in ["age", "birthday", "height", "hair color"]:
                            fields[key.capitalize()] = val
                return fields

            def _build_character_embed(self, cd: Dict[str, Any]) -> discord.Embed:
                name = cd.get("name") or "Unknown"
                kanji = cd.get("name_kanji") or "N/A"
                about = cd.get("about") or ""
                desc = self._clean_about(about)

                fields = self._extract_fields(about)
                seiyuu = "N/A"
                for v in cd.get("voices", []) or []:
                    if v.get("language") == "Japanese":
                        seiyuu = v["person"]["name"]
                        break

                anime_list = [a["anime"]["title"] for a in cd.get("anime", []) or []]
                if anime_list:
                    anime_tags = " ".join(f"`{a}`" for a in anime_list[:4]) + (" ..." if len(anime_list) > 4 else "")
                else:
                    anime_tags = "`N/A`"

                image_url = cd.get("images", {}).get("jpg", {}).get("image_url")

                embed = discord.Embed(title=name, description=desc, color=discord.Color.blurple())
                if image_url:
                    embed.set_thumbnail(url=image_url)

                info_left = []
                if "Age" in fields: info_left.append(f"**Age:** {fields['Age']}")
                if "Height" in fields: info_left.append(f"**Height:** {fields['Height']}")
                if "Birthday" in fields: info_left.append(f"**Birthday:** {fields['Birthday']}")
                if "Hair color" in fields: info_left.append(f"**Hair Color:** {fields['Hair color']}")

                info_right = f"**Kanji:** {kanji}\n**Seiyuu:** {seiyuu}\n"

                if info_left:
                    embed.add_field(name="Info", value="\n".join(info_left), inline=True)
                embed.add_field(name="Details", value=info_right, inline=True)

                embed.add_field(name="📺 Anime Appearances", value=anime_tags, inline=False)
                embed.set_footer(
                    text="Provided by Jikan API",
                    icon_url="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png"
                )
                return embed

        await ctx.send("🔎 Select a character from the search results:", view=CharacterSelectView(options))

async def setup(bot):
    await bot.add_cog(Misc(bot))