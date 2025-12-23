import discord
import time
import logging
import io
from discord.ext import commands
from discord import app_commands
from utils.helpPaging import HelpPages, HelpView
from constants.configs import PREFIX, GIF_ATTACHMENTS_URL, GIF_ASSETS
from constants.emojis import CustomEmojis
from utils.discordHelpers import create_choices

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
        
    @staticmethod
    def add_embed_fields(embed, fields: list[tuple[str, any, bool]]):
        """
        A helper function to add multiple fields to a discord.Embed.
        fields: list of tuples (emoji_key, label, value, inline)
        """
        for emoji_key, label, value, inline in fields:
            embed.add_field(name=f"{CustomEmojis[emoji_key]} {label}", value=value, inline=inline)

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

        fields = [
            ("Crown", "Owner", guild.owner, True),
            ("Members", "Members", guild.member_count, True),
            ("Roles", "Roles", len(guild.roles), True),
            ("TextChannels", "Text Channels", len(guild.text_channels), True),
            ("VoiceChannels", "Voice Channels", len(guild.voice_channels), True),
            ("Calendar", "Created On", discord.utils.format_dt(guild.created_at, style='F'), False),
        ]
        self.add_embed_fields(embed=embed, fields=fields)

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
    @app_commands.choices(category=create_choices({
        "Information": "information",
        "Moderator": "moderator",
        "Manager": "manager",
        "Miscellaneous": "miscellaneous",
    }))
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

        fields = [
            ("Bot", "Bot Name", self.bot.user.name, True),
            ("ID", "ID", self.bot.user.id, True),
            ("Creator", "Creator", "Soumetsu.#8818", True),
            ("Wrench", "Prefix", f"`{PREFIX}`", True),
            ("Globe", "Servers", f"{len(self.bot.guilds)}", True),
            ("Clock", "Uptime", uptime_str, True),
        ]
        self.add_embed_fields(embed=embed, fields=fields)

        events_cog = self.bot.get_cog("Events")
        
        if events_cog and "info" in events_cog.gifs :
            gif_bytes = events_cog.gifs["info"]
            file = discord.File(io.BytesIO(gif_bytes), filename=GIF_ASSETS["Kurumi"])
            await ctx.send(file=file, embed=embed)
        else:
            await ctx.send(embed=embed) # fallback 
    
    
async def setup(bot):
    await bot.add_cog(Information(bot))
    logging.getLogger("bot").info("Loaded information cog.")