import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Optional
import asyncio
import logging
from utils.animeHelper import (
    build_anime_embed, 
    build_character_embed, 
    build_anime_options, 
    build_character_select_options, 
    GenericSelectView)

from constants.configs import ANILIST_API, ANILIST_SEARCH_QUERY, ANILIST_CHARACTER_SEARCH_QUERY


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
            
    async def fetch_animal(self, ctx: commands.Context, api_url: str, animal_type: str, title: str, color: discord.Color, json_response_key: str):
        """Helper function to fetch a random animal image."""
        await self._defer_if_slash(ctx)

        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return await ctx.send(f"❌ Couldn't fetch a {animal_type} right now.")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send(f"❌ An error occurred while fetching a {animal_type}.")
        
        if isinstance(data, list): # CHECK: some APIs return a list at the top level or not
            image_url = data[0][json_response_key]
        else:
            image_url = data[json_response_key]

        embed = discord.Embed(title=title, color=color)
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

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
        """Fetch a random cat image and send it as an embed."""
        await self.fetch_animal(
            ctx,
            api_url="https://api.thecatapi.com/v1/images/search",
            animal_type="cat",
            title="🐱 Meow!",
            color=discord.Color.purple(),
            json_response_key="url"
        )

    @commands.hybrid_command(name="dogs", help="Miscellaneous: Get a random dog image")
    async def dogs(self, ctx: commands.Context):
        """Fetch a random dog image and send it as an embed."""
        await self.fetch_animal(
            ctx,
            api_url="https://dog.ceo/api/breeds/image/random",
            animal_type="dog",
            title="🐶 Woof!",
            color=discord.Color.purple(),
            json_response_key="message"
        )

    @commands.hybrid_command(name="rabbits", help="Miscellaneous: Get a random rabbit image")
    async def rabbits(self, ctx: commands.Context):
        """Fetch a random rabbit image and send it as an embed."""
        await self.fetch_animal(
            ctx,
            api_url="https://rabbit-api-two.vercel.app/api/random",
            animal_type="rabbit",
            title="🐰 Cluck!",
            color=discord.Color.purple(),
            json_response_key="url"
        )

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
    logging.getLogger("bot").info("Loaded miscellaneous cog.")