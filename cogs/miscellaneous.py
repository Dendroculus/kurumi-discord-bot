import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import aiohttp
from typing import Any, Dict, List, Optional, Callable, Awaitable
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


"""
miscellaneous.py

Collection of utility commands and AniList-backed search functionality.

Responsibilities:
- Provide friendly embeds and search flows for anime and characters using the AniList GraphQL API.
- Offer small miscellaneous commands that fetch images from public APIs (cats, dogs, rabbits).
- Contain helpers for cleaning and formatting text, dates, and select-based UI interactions.

Notes:
- Network calls are performed via an internal aiohttp.ClientSession created by the cog.
- The GenericSelectView bridges a Select UI and an embed builder callback to show detailed results.
- TextUtils centralizes common formatting and truncation logic for safe embed content.
"""


class TextUtils:
    """Utility helpers for text, dates, and formatting used by embed builders."""

    @staticmethod
    def clean_description(
        desc: Optional[str],
        limit: int = 4096,
        preserve_spoilers: bool = False,
        short_truncate: Optional[int] = None,
    ) -> str:
        """
        Clean HTML-like tags from AniList descriptions and optionally truncate.

        Args:
            desc: raw description text (may contain simple tags like <br>, <i>).
            limit: hard upper bound for returned string length (suitable for embed descriptions).
            preserve_spoilers: if True, attempt to convert AniList-style spoilers into Discord spoilers.
            short_truncate: if set, performs a softer semantic truncation at sentence boundary near this length.

        Returns:
            A cleaned, safely truncated string suitable for use as an embed description.
        """
        if not desc:
            desc = "No description available."

        cleaned = (
            desc.replace("<br>", "\n")
            .replace("<i>", "")
            .replace("</i>", "")
        )

        # Spoilers (only when requested, e.g. for characters)
        if preserve_spoilers:
            cleaned = cleaned.replace("~!", "||").replace("! ~", "||")

        # Hard safety limit for Embed description
        if len(cleaned) > limit:
            cleaned = cleaned[: limit - 3] + "..."

        # Optional shorter semantic truncation (e.g. 300 chars for character desc)
        if short_truncate is not None and len(cleaned) > short_truncate:
            cut_pos = cleaned[:short_truncate].rfind(".")
            if cut_pos != -1:
                return cleaned[: cut_pos + 1]
            return cleaned[: short_truncate - 3] + "..."

        return cleaned

    @staticmethod
    def format_date_full(d: Optional[Dict[str, Optional[int]]]) -> str:
        """
        Format a full date dict as YYYY-MM-DD, or 'N/A' when incomplete/missing.

        Expects dicts with keys 'year', 'month', 'day'. Returns 'N/A' unless all parts are present.
        """
        if not d:
            return "N/A"

        year = d.get("year")
        month = d.get("month")
        day = d.get("day")

        if not (year and month and day):
            return "N/A"

        return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def format_date_loose(d: Optional[Dict[str, Optional[int]]]) -> str:
        """
        Looser date formatter that tolerates partial dates and returns a YYYY-M-D style string.

        Missing month/day will appear as '??' to indicate unknown parts.
        """
        if d and d.get("year"):
            year = d.get("year", "N/A")
            month = d.get("month", "??")
            day = d.get("day", "??")
            return f"{year}-{month}-{day}"
        return "N/A"

    @staticmethod
    def opt(value: Any, fallback: str = "N/A") -> str:
        """Return a stringified value or a fallback when the value is None/empty."""
        return str(value) if value not in (None, "", []) else fallback

    @staticmethod
    def genres_to_text(genres: List[str]) -> str:
        """Convert a list of genre strings into a concise formatted inline text block."""
        if not genres:
            return "N/A"
        return " ".join(f"`{g}`" for g in genres)


class GenericSelectView(View):
    """
    Generic select view that:
    - Accepts pre-built SelectOptions and corresponding raw entries.
    - Maps the option value (id) back to the raw entry.
    - Uses an embed_builder callback to produce the detailed embed for the chosen entry.
    """

    def __init__(
        self,
        items: List[discord.SelectOption],
        entries: List[Dict[str, Any]],
        embed_builder: Callable[[Dict[str, Any]], discord.Embed],
        placeholder: str = "Choose an option...",
        timeout: Optional[float] = 180.0,
    ):
        """
        Args:
            items: list of discord.SelectOption to show to the user.
            entries: list of raw data dicts; each dict must contain an 'id' key.
            embed_builder: callable that accepts a single entry and returns a discord.Embed.
            placeholder: select placeholder text.
            timeout: optional view timeout in seconds.
        """
        super().__init__(timeout=timeout)
        self.by_id = {str(e["id"]): e for e in entries}
        self.embed_builder = embed_builder

        select = Select(placeholder=placeholder, options=items)
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        """Handle a user's selection by building and editing the original response with the chosen embed."""
        await interaction.response.defer()

        selected_id = interaction.data["values"][0]
        data = self.by_id.get(selected_id)

        if not data:
            return await interaction.followup.send(
                "❌ Selected item not found anymore. Please run the command again.",
                ephemeral=True,
            )

        embed = self.embed_builder(data)
        await interaction.edit_original_response(embed=embed, view=None)


# ---------- Character embed helpers ----------

def build_character_embed(cd: Dict[str, Any]) -> discord.Embed:
    """Build a rich character embed from AniList character data dictionary."""
    name = cd.get("name", {}).get("full") or "Unknown"
    native = cd.get("name", {}).get("native") or "N/A"

    description = TextUtils.clean_description(
        cd.get("description"),
        limit=4096,
        preserve_spoilers=True,
        short_truncate=300,
    )

    url = cd.get("siteUrl")

    embed = discord.Embed(
        title=name,
        url=url,
        description=description,
        color=discord.Color.blurple(),
    )

    image_url = cd.get("image", {}).get("large") or cd.get("image", {}).get("medium")
    if image_url:
        embed.set_thumbnail(url=image_url)

    gender = cd.get("gender") or "N/A"
    age = cd.get("age") or "N/A"
    blood_type = cd.get("bloodType") or "N/A"
    birthday = TextUtils.format_date_full(cd.get("dateOfBirth"))

    info_text = (
        f"**Gender:** {gender}\n"
        f"**Age:** {age}\n"
        f"**Birthday:** {birthday}\n"
        f"**Blood Type:** {blood_type}"
    )
    embed.add_field(name="📋 Info", value=info_text, inline=True)

    details_text = f"**Native:** {native}\n**Favorites:** {cd.get('favourites', 'N/A')}"
    embed.add_field(name="📊 Details", value=details_text, inline=True)

    media_nodes = cd.get("media", {}).get("nodes", [])
    media_text = format_character_media_list(media_nodes)
    embed.add_field(name="📺 Appearances", value=media_text, inline=False)

    embed.set_footer(
        text="Provided by AniList",
        icon_url="https://anilist.co/img/icons/android-chrome-512x512.png",
    )

    return embed


def format_character_media_list(media_nodes: List[Dict[str, Any]]) -> str:
    """Format the list of media appearances for character embeds into a short string."""
    if not media_nodes:
        return "`N/A`"

    titles = []
    for node in media_nodes[:4]:
        title = (
            node.get("title", {}).get("english")
            or node.get("title", {}).get("romaji")
            or "Unknown"
        )
        titles.append(f"`{title}`")

    result = " ".join(titles)
    if len(media_nodes) > 4:
        result += " ..."
    return result


def build_character_select_options(results: List[Dict[str, Any]]) -> List[discord.SelectOption]:
    """Convert character search results into SelectOption instances for a Select menu."""
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


def build_anime_embed(anime: Dict[str, Any]) -> discord.Embed:
    """Construct an embed presenting anime details from AniList media data."""
    title = anime["title"]["english"] or anime["title"]["romaji"]
    url = anime.get("siteUrl")
    description = TextUtils.clean_description(anime.get("description", ""))

    embed = discord.Embed(
        title=title,
        url=url,
        description=description,
        color=discord.Color.blurple(),
    )

    cover_medium = anime.get("coverImage", {}).get("medium")
    if cover_medium:
        embed.set_thumbnail(url=cover_medium)

    banner = anime.get("bannerImage")
    if banner:
        embed.set_image(url=banner)

    embed.add_field(name="Episodes", value=TextUtils.opt(anime.get("episodes")), inline=True)
    status = TextUtils.opt(anime.get("status")).title() if anime.get("status") else "N/A"
    embed.add_field(name="Status", value=status, inline=True)

    start_str = TextUtils.format_date_loose(anime.get("startDate", {}))
    end_str = TextUtils.format_date_loose(anime.get("endDate", {}))
    embed.add_field(name="Start Date", value=start_str, inline=True)
    embed.add_field(name="End Date", value=end_str, inline=True)

    embed.add_field(
        name="Duration",
        value=f"{TextUtils.opt(anime.get('duration'))} min/ep",
        inline=True,
    )

    studio = anime.get("studios", {}).get("nodes", [])
    embed.add_field(
        name="Studio",
        value=studio[0]["name"] if studio else "N/A",
        inline=True,
    )
    embed.add_field(name="Source", value=TextUtils.opt(anime.get("source")), inline=True)

    embed.add_field(name="Score", value=f"{TextUtils.opt(anime.get('averageScore'))}%", inline=True)
    embed.add_field(name="Popularity", value=TextUtils.opt(anime.get("popularity")), inline=True)
    embed.add_field(name="Favourites", value=TextUtils.opt(anime.get("favourites")), inline=True)

    embed.add_field(
        name="Genres",
        value=TextUtils.genres_to_text(anime.get("genres", [])),
        inline=False,
    )
    embed.set_footer(
        text="Provided by AniList",
        icon_url="https://anilist.co/img/icons/android-chrome-512x512.png",
    )
    return embed


def build_anime_options(results: List[Dict[str, Any]]) -> List[discord.SelectOption]:
    """Create SelectOption choices from anime search results for use in a Select menu."""
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

class Misc(commands.Cog):
    """
    Miscellaneous fun and utility commands.

    Highlights:
    - Image fetchers: cats, dogs, rabbits
    - AniList-backed search: anime, animecharacter (uses GraphQL)
    - Avatar command for users
    - Uses an internal aiohttp.ClientSession; the session is closed on cog unload.
    """
    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._session_close_task: Optional[asyncio.Task] = None

    def cog_unload(self) -> None:
        """Ensure the aiohttp session is closed when the cog is unloaded (schedules close as a background task)."""
        if not self.session.closed:
            self._session_close_task = asyncio.create_task(self.session.close())

    @staticmethod
    async def _defer_if_slash(ctx: commands.Context) -> None:
        """
        Helper used by hybrid commands to defer interactions when invoked as a slash command.

        This prevents the interaction from timing out while an HTTP request is in progress.
        """
        interaction = getattr(ctx, "interaction", None)
        if interaction is not None and not interaction.response.is_done():
            await interaction.response.defer()

    @staticmethod
    async def _reply_ephemeral(interaction: discord.Interaction, content: str) -> None:
        """Send an ephemeral reply to an interaction, using followup if the initial response is already sent."""
        if not interaction.response.is_done():
            await interaction.response.send_message(content, ephemeral=True)
        else:
            await interaction.followup.send(content, ephemeral=True)


    @commands.hybrid_command(name="avatar", help="Miscellaneous: Show avatar of a user")
    @app_commands.describe(user="The user to get the avatar of. Defaults to you.")
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        """Show the avatar image for the specified user or the command author."""
        target = user or ctx.author
        embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.purple())
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="cats", help="Miscellaneous: Shows a random cat image")
    async def cats(self, ctx: commands.Context):
        """Fetch a random cat image from a public API and send it in an embed."""
        await self._defer_if_slash(ctx)

        try:
            async with self.session.get("https://api.thecatapi.com/v1/images/search") as resp:
                if resp.status != 200:
                    return await ctx.send("😿 Couldn't fetch a cat right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("😿 An error occurred while fetching a cat.")

        embed = discord.Embed(title="🐱 Meow!", color=discord.Color.purple())
        embed.set_image(url=data[0]["url"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dogs", help="Miscellaneous: Get a random dog image")
    async def dogs(self, ctx: commands.Context):
        """Fetch a random dog image and send it as an embed."""
        await self._defer_if_slash(ctx)

        try:
            async with self.session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Couldn't fetch a dog right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("❌ An error occurred while fetching a dog.")

        embed = discord.Embed(title="🐶 Woof!", color=discord.Color.purple())
        embed.set_image(url=data["message"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rabbits", help="Miscellaneous: Get a random rabbit image")
    async def rabbits(self, ctx: commands.Context):
        """Fetch a random rabbit image and send it as an embed."""
        await self._defer_if_slash(ctx)

        try:
            async with self.session.get("https://rabbit-api-two.vercel.app/api/random") as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Couldn't fetch a rabbit right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("❌ An error occurred while fetching a rabbit.")

        embed = discord.Embed(title="🐰 Cluck!", color=discord.Color.purple())
        embed.set_image(url=data["url"])
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="anime", help="Miscellaneous: Search for an anime by name (AniList)")
    async def anime(self, ctx: commands.Context, *, query: str):
        """Search AniList for anime matching the query and present a selectable list to the user."""
        await self._defer_if_slash(ctx)

        variables = {"search": query}
        try:
            async with self.session.post(
                ANILIST_API,
                json={"query": ANILIST_SEARCH_QUERY, "variables": variables},
            ) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch anime info right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("❌ An error occurred while fetching anime info.")

        results = data.get("data", {}).get("Page", {}).get("media", []) or []
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        options = build_anime_options(results)
        view = GenericSelectView(
            items=options,
            entries=results,
            embed_builder=build_anime_embed,
            placeholder="Choose an anime...",
        )
        await ctx.send("Select an anime from the search results:", view=view)

    @commands.hybrid_command(name="animecharacter", help="Miscellaneous: Search for an anime character by name")
    @app_commands.describe(query="The name of the anime character to search for")
    async def animecharacter(self, ctx: commands.Context, *, query: str):
        """Search AniList for characters matching the query and present a selectable result list."""
        await self._defer_if_slash(ctx)

        try:
            variables = {"search": query}
            async with self.session.post(
                ANILIST_API,
                json={"query": ANILIST_CHARACTER_SEARCH_QUERY, "variables": variables},
            ) as resp:
                if resp.status != 200:
                    return await ctx.send("❌ Could not fetch character info right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("❌ An error occurred while fetching character info.")

        results = data.get("data", {}).get("Page", {}).get("characters", []) or []
        if not results:
            return await ctx.send(f"❌ No results found for `{query}`.")

        options = build_character_select_options(results)
        view = GenericSelectView(
            items=options,
            entries=results,
            embed_builder=build_character_embed,
            placeholder="Choose a character...",
        )
        await ctx.send("🔎 Select a character from the search results:", view=view)


async def setup(bot):
    await bot.add_cog(Misc(bot))