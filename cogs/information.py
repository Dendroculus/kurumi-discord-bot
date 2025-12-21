import discord
import time
import logging
import os
from discord.ext import commands
from discord import app_commands
from utils.help_paging import HelpPages, HelpView
from constants.configs import PREFIX, GIF_ATTACHMENTS_URL, GIF_ASSETS
from constants.emojis import CustomEmojis

"""
information.py

Provides informational and utility commands for the Kurumi Discord bot.

Responsibilities:
- Generate context-aware help pages from registered commands and present them in a paginated View.
- Provide basic server and bot information commands:
  - membercount: show current server member count
  - serverstats: detailed server statistics embed
  - member: list members in a given role (capped)
  - ping: show bot latency
  - help: interactive/help pages (hybrid command)
  - info: bot information and uptime

Integration expectations:
- Commands should include a help string in the format "Category: Description" for inclusion in help pages.
- utils.config should provide PREFIX used to format shown command usage.
- Assets directory contains "kurumi.gif" used by the info command; when missing, sending the file will raise as usual.
"""

start_time = time.time()

        
class Information(commands.Cog):
    """
    Cog exposing informational commands about the server and the bot.

    Commands:
    - membercount: Display total members in the guild.
    - serverstats: Send an embed with several guild statistics.
    - member: List members belonging to a role (max 90 shown).
    - ping: Show bot latency in milliseconds.
    - help: Show categorized command list (interactive).
    - info: Show bot identity, uptime, and other metadata.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="membercount", help="Information:Shows total member count in the server")
    @commands.guild_only()
    async def membercount(self, ctx: commands.Context):
        """Send a short message with the guild's member count."""
        await ctx.send(f"👥 This server has **{ctx.guild.member_count}** members.")
            
    @commands.hybrid_command(name="serverstats", help="Information:Shows server statistics")
    @commands.guild_only()
    async def serverstats(self, ctx: commands.Context):
        """Send an embed containing several useful server statistics."""
        guild = ctx.guild
        embed = discord.Embed(title=f"Server Stats — {guild.name}", color=discord.Color.purple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name=f"{CustomEmojis["Crown"]} Owner", value=guild.owner, inline=True)
        embed.add_field(name=f"{CustomEmojis["Members"]} Members", value=guild.member_count, inline=True)
        embed.add_field(name=f"{CustomEmojis["Roles"]} Roles", value=len(guild.roles), inline=True)
        embed.add_field(name=f"{CustomEmojis["TextChannels"]} Text Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name=f"{CustomEmojis["VoiceChannels"]} Voice Channels", value=len(guild.voice_channels), inline=True)
        embed.add_field(name=f"{CustomEmojis["Calendar"]} Created On", value=discord.utils.format_dt(guild.created_at, style='F'), inline=False)

        await ctx.send(embed=embed)

        
    @commands.hybrid_command(name="member", help="Information:List members in a role (max 90)")
    @commands.guild_only()
    @app_commands.describe(role="The role to list members from")
    async def member(self, ctx: commands.Context, role: discord.Role):
        """
        List members in the provided role, up to a safe cap to avoid overly long messages.

        Args:
            ctx: command context.
            role: discord.Role whose members will be listed.
        """
        if not role.members:
            return await ctx.send(f"❌ No members found in the `{role.name}` role.")

        members_to_show = role.members[:90]        
        member_list = "\n".join(f"• {member.mention}" for member in members_to_show)

        embed = discord.Embed(
            title=f"📋 Members in '{role.name}'",
            description=member_list,
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", help="Information:Shows bot latency")
    async def ping(self, ctx: commands.Context):
        """Respond with the bot's websocket latency in milliseconds."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! `{latency}ms`")

    @commands.hybrid_command( name="help",  help="Information:Shows this command list",  description="Shows a list of available commands.")
    @app_commands.describe(category="Choose a category to view")
    @app_commands.choices(category=[
        app_commands.Choice(name="Information", value="information"),
        app_commands.Choice(name="Moderator", value="moderator"),
        app_commands.Choice(name="Manager", value="manager"),
        app_commands.Choice(name="Miscellaneous", value="miscellaneous"),
    ])
    async def commands_hybrid(self, ctx: commands.Context, category: app_commands.Choice[str] = None):
        """
        Display the help pages or a single category.

        If a category is provided and found, a single page is sent. Otherwise an
        interactive HelpView is created to allow the user to navigate pages.
        """
        pages = HelpPages.generate_help_pages(self.bot)
        if not pages:
            return await ctx.send("No commands available to show.")

        if category:
            target_page_index = -1
            for i, page in enumerate(pages):
                if category.value in page.title.lower():
                    target_page_index = i
                    break
            if target_page_index != -1:
                page = pages[target_page_index]
                page.set_footer(text=f"Showing category: {category.name}")
                await ctx.send(embed=page)
            else:
                await ctx.send(f"❌ Could not find the category: {category.name}")
        else:
            view = HelpView(pages, ctx.author)
            message = await ctx.send(embed=pages[0], view=view)
            view.message = message

    @commands.hybrid_command(name="info", help="Information:Shows bot information")
    async def info(self, ctx):
        """
        Show bot information including uptime, server count, prefix, and other metadata.

        Reads the 'kurumi.gif' asset from the repository's assets directory and sends it
        alongside the embed. If the file is missing, the File constructor will raise
        as normal; the command intentionally does not swallow that error.
        """
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="🌹 Kurumi Info",
            description="Your personal assistant with a yandere twist.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=GIF_ATTACHMENTS_URL["Kurumi_URL"])  

        embed.add_field(name=f"{CustomEmojis["Bot"]} Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name=f"{CustomEmojis["ID"]} ID", value=self.bot.user.id, inline=True)
        embed.add_field(name=f"{CustomEmojis["Creator"]} Creator", value="Soumetsu.#8818", inline=True)
        embed.add_field(name=f"{CustomEmojis["Wrench"]} Prefix", value=f"`{PREFIX}`", inline=True)
        embed.add_field(name=f"{CustomEmojis["Globe"]} Servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name=f"{CustomEmojis["Clock"]} Uptime", value=uptime_str, inline=True)
        file = discord.File(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", GIF_ASSETS["Kurumi"]),filename=GIF_ASSETS["Kurumi"])

        await ctx.send(file=file, embed=embed)
    
async def setup(bot):
    await bot.add_cog(Information(bot))
    logging.getLogger("bot").info("Loaded information cog.")