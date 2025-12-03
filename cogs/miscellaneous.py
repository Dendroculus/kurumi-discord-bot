import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import aiohttp
from typing import Any, Dict, List, Optional
import asyncio

    
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

ANILIST_CHARACTER_SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 5) {
    characters(search: $search) {
      id
      name {
        full
        native
      }
      description
      image {
        large
        medium
      }
      gender
      dateOfBirth {
        year
        month
        day
      }
      age
      bloodType
      siteUrl
      favourites
      media(perPage: 4, sort: POPULARITY_DESC) {
        nodes {
          title {
            romaji
            english
          }
        }
      }
    }
  }
}
"""

class CharacterSelectView(View):
    def __init__(self, items: List[discord.SelectOption], characters: List[Dict[str, Any]]):
        super().__init__()
        self.by_id = {str(c["id"]): c for c in characters}
        select = Select(placeholder="Choose a character...", options=items)
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        """Handle character selection from dropdown."""
        await interaction.response.defer()
        
        char_id = interaction.data["values"][0]
        char_data = self.by_id.get(char_id)
        
        if not char_data:
            return await interaction.followup.send("❌ Character not found.", ephemeral=True)

        embed = self._build_character_embed(char_data)
        await interaction. edit_original_response(embed=embed, view=None)

    @staticmethod
    def _clean_description(desc: str) -> str:
        """Clean and truncate character description."""
        if not desc:
            return "No description available."
        
        # Remove HTML tags and BBCode
        cleaned = desc.replace("<br>", "\n").replace("<i>", "*").replace("</i>", "*")
        cleaned = cleaned.replace("~!", "||").replace("! ~", "||")  # AniList spoiler tags
        
        # Truncate to 300 chars
        if len(cleaned) > 300:
            cut_pos = cleaned[:300].rfind(".")
            if cut_pos != -1:
                return cleaned[:cut_pos + 1]
            return cleaned[:297] + "..."
        return cleaned

    @staticmethod
    def _format_date(date_obj: Optional[Dict[str, Optional[int]]]) -> str:
        """Format birth date."""
        if not date_obj:
            return "N/A"
        
        year = date_obj.get("year") or "?"
        month = date_obj.get("month") or "?"
        day = date_obj.get("day") or "?"
        
        return f"{year}-{month:02d}-{day:02d}" if all([year != "?", month != "?", day != "?"]) else "N/A"

    @staticmethod
    def _format_media_list(media_nodes: List[Dict[str, Any]]) -> str:
        """Format anime/manga appearances."""
        if not media_nodes:
            return "`N/A`"
        
        titles = []
        for node in media_nodes[:4]:
            title = node.get("title", {}).get("english") or node.get("title", {}).get("romaji") or "Unknown"
            titles.append(f"`{title}`")
        
        result = " ".join(titles)
        if len(media_nodes) > 4:
            result += " ..."
        return result

    def _build_character_embed(self, cd: Dict[str, Any]) -> discord.Embed:
        """Build character embed from AniList data."""
        name = cd.get("name", {}).get("full") or "Unknown"
        native = cd.get("name", {}).get("native") or "N/A"
        description = self._clean_description(cd.get("description"))
        url = cd.get("siteUrl")
        
        embed = discord.Embed(
            title=name,
            url=url,
            description=description,
            color=discord.Color.blurple()
        )
        
        # Thumbnail
        image_url = cd.get("image", {}).get("large") or cd.get("image", {}).get("medium")
        if image_url:
            embed.set_thumbnail(url=image_url)
        
        # Info fields
        gender = cd.get("gender") or "N/A"
        age = cd.get("age") or "N/A"
        blood_type = cd.get("bloodType") or "N/A"
        birthday = self._format_date(cd.get("dateOfBirth"))
        
        info_text = f"**Gender:** {gender}\n**Age:** {age}\n**Birthday:** {birthday}\n**Blood Type:** {blood_type}"
        embed.add_field(name="📋 Info", value=info_text, inline=True)
        
        # Native name and favorites
        details_text = f"**Native:** {native}\n**Favorites:** {cd.get('favourites', 'N/A')}"
        embed.add_field(name="📊 Details", value=details_text, inline=True)
        
        # Media appearances
        media_nodes = cd.get("media", {}).get("nodes", [])
        media_text = self._format_media_list(media_nodes)
        embed.add_field(name="📺 Appearances", value=media_text, inline=False)
        
        embed.set_footer(
            text="Provided by AniList",
            icon_url="https://anilist.co/img/icons/android-chrome-512x512.png"
        )
        
        return embed
    
class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _defer_if_slash(ctx: commands.Context) -> None:
        interaction = getattr(ctx, "interaction", None)
        if interaction is not None and not interaction.response.is_done():
            await interaction.response.defer()

    @staticmethod
    async def _reply_ephemeral(interaction: discord.Interaction, content: str) -> None:
        if not interaction.response.is_done():
            await interaction.response.send_message(content, ephemeral=True)
        else:
            await interaction.followup.send(content, ephemeral=True)

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
                    if not anime_data:
                        return await Misc._reply_ephemeral(interaction, "❌ Selected item not found anymore. Please run the command again.")
                    embed = Misc._build_anime_embed(anime_data)
                    await interaction.response.edit_message(embed=embed, view=None)

                select.callback = _on_select
                self.add_item(select)

        await ctx.send("Select an anime from the search results:", view=AnimeSelectView(options, results))

    @commands. hybrid_command(name="animecharacter", help="Miscellaneous: Search for an anime character by name")
    @app_commands. describe(query="The name of the anime character to search for")
    async def animecharacter(self, ctx: commands.Context, *, query: str):
        await self._defer_if_slash(ctx)

        try:
            variables = {"search": query}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ANILIST_API,
                    json={"query": ANILIST_CHARACTER_SEARCH_QUERY, "variables": variables}
                ) as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Could not fetch character info right now.")
                    data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("❌ An error occurred while fetching character info.")

        results = data.get("data", {}).get("Page", {}).get("characters", []) or []
        
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        options = self._build_character_select_options(results)
        view = CharacterSelectView(options, results)
        await ctx.send("🔎 Select a character from the search results:", view=view)


    def _build_character_select_options(self, results: List[Dict[str, Any]]) -> List[discord.SelectOption]:
        """Build select menu options from character search results."""
        options: List[discord.SelectOption] = []
        for char in results:
            name = char.get("name", {}).get("full") or "Unknown"
            native = char.get("name", {}).get("native") or ""
            
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    description=f"Native: {native}"[:100] if native else "Character",
                    value=str(char["id"]),
                )
            )
        return options

async def setup(bot):
    await bot.add_cog(Misc(bot))