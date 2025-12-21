import discord
from typing import Any, Dict, List, Callable, Optional
from utils.textutils import TextUtils
from discord.ui import View, Select

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