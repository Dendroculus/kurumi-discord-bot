import discord
from typing import Any, Dict, List, Optional, Callable
from discord.ui import View, Select

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