import discord
import time
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
from discord.ui import View, Button
import os

# Track when bot starts
start_time = time.time()
        
def generate_help_pages(bot_instance):
    categories = {"Information": [], "Manager": [], "Moderator": [], "Miscellaneous": []}
    
    all_commands = bot_instance.commands
    
    for command in all_commands:
        if command.hidden or not command.help:
            continue
        try:
            category, desc = command.help.split(":", 1)
            category = category.strip().capitalize()
            desc = desc.strip()
            if category in categories:
                categories[category].append(f"  `!{command.name}` — {desc}")
        except ValueError:
            continue
            
    pages = []
    for cat, cmds in categories.items():
        if not cmds:
            continue
        embed = discord.Embed(title=f"<:kurulove:1414905093878190180> {cat} Commands", color=discord.Color.purple())
        embed.set_thumbnail(url=str(bot_instance.user.display_avatar.url))
        embed.description = "\n".join(cmds)
        pages.append(embed)
    return pages

class HelpView(View):
    def __init__(self, pages, author):
        super().__init__(timeout=None)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None

        self.page_btn = Button(
            label=f"{self.current_page + 1}/{len(self.pages)}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )

        self.prev_btn = Button(label="<", style=discord.ButtonStyle.danger)
        self.next_btn = Button(label=">", style=discord.ButtonStyle.danger)
        self.delete_button = Button(label="Delete", style=discord.ButtonStyle.danger)

        self.prev_btn.callback = self.prev_button
        self.next_btn.callback = self.next_button
        self.delete_button.callback = self.handle_delete
        
        self.add_item(self.prev_btn)
        self.add_item(self.page_btn)
        self.add_item(self.next_btn)
        self.add_item(self.delete_button)

        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == len(self.pages) - 1
        self.page_btn.label = f"{self.current_page + 1}/{len(self.pages)}"

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def prev_button(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def next_button(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        
    async def handle_delete(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't delete this message.", ephemeral=True)
        await interaction.response.defer()
        await interaction.message.delete()
        
class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="membercount", help="Information:Shows total member count in the server")
    @commands.guild_only()
    async def membercount(self, ctx: commands.Context):
        await ctx.send(f"👥 This server has **{ctx.guild.member_count}** members.")
        
    @commands.hybrid_command(name="serverstats", help="Information:Shows server statistics")
    @commands.guild_only()
    async def serverstats(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"📊 Server Stats — {guild.name}", color=discord.Color.purple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👑 Owner", value=guild.owner, inline=True)
        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="📜 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="💬 Text Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Voice Channels", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="📅 Created On", value=discord.utils.format_dt(guild.created_at, style='F'), inline=False)
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="member", help="Information:List members in a role (max 90)")
    @commands.guild_only()
    @app_commands.describe(role="The role to list members from")
    async def member(self, ctx: commands.Context, role: discord.Role):
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
        pages = generate_help_pages(self.bot)
        if not pages:
            return await ctx.send("No commands available to show.")

        if category:
            target_page_index = -1
            for i, page in enumerate(pages):
                if page.title.lower().startswith(f"📜 {category.name.lower()}"):
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
    async def info(self, ctx: commands.Context):
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="🌹 Kurumi Info",
            description="Your personal assistant with a yandere twist.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="attachment://kurumi.gif")  

        embed.add_field(name="🆔 Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name="📌 ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="👤 Creator", value="Soumetsu.#8818", inline=True)
        embed.add_field(name="🔧 Prefix", value="`!`", inline=True)
        embed.add_field(name="🌐 Servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)

        file = discord.File(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "kurumi.gif"), filename="kurumi.gif")

        await ctx.send(file=file, embed=embed)

        
async def setup(bot):
    await bot.add_cog(Information(bot))
    print("📦 Loaded information cog.")
