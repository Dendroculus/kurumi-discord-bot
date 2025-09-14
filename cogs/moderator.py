import discord
from discord.ext import commands
from discord import app_commands
from collections import defaultdict

class AuditLogView(discord.ui.View):
    def __init__(self, entries, ctx, per_page=10):
        super().__init__(timeout=180)
        self.entries = entries
        self.author = ctx.author
        self.ctx = ctx
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(entries) - 1) // per_page + 1)
        self.message = None
        self.update_buttons()
        
    def format_target(self, target):
        if hasattr(target, "name"):
            return target.name
        if isinstance(target, discord.PartialIntegration):
            return f"{target.name} (Integration)"
        if isinstance(target, discord.Object):
            return "Unknown Integration"
        try:
            return str(target)
        except:
            return "Unknown"

    def get_page_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_entries = self.entries[start:end]

        embed = discord.Embed(
            title=f"Audit Log (Page {self.current_page + 1}/{self.total_pages})",
            color=discord.Color.dark_red()
        )
        for entry in page_entries:
            user = str(entry.user)
            target = self.format_target(entry.target)
            action = str(entry.action).replace("AuditLogAction.", "")
            reason = entry.reason or "No reason"
            embed.add_field(name=f"{user}  →  {target}", value=f"`Action  : {action}`\n`Reason  : {reason}`", inline=False)

        return embed

    def update_buttons(self):
        for child in self.children:
            if child.label == "Previous":
                child.disabled = self.current_page == 0
            elif child.label == "Next":
                child.disabled = self.current_page >= self.total_pages - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.danger)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.danger)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

class Moderator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "warnings"):
            bot.warnings = defaultdict(int)

    @commands.hybrid_command(name="nuke", help="Moderator:Nuke the current channel (delete & recreate)")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(channel="The channel to nuke. Defaults to the current channel.")
    async def nuke(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target_channel = channel or ctx.channel
        await ctx.send(f"Nuking {target_channel.mention}... this may take a moment.")

        new_channel = await target_channel.clone(reason=f"Nuked by {ctx.author}")
        await target_channel.delete()

        embed = discord.Embed(
            description=f"💥 Channel `{target_channel.name}` has been nuked by {ctx.author.mention}",
            color=discord.Color.red()
        )
        embed.set_image(url="https://gifdb.com/images/high/kurumi-tokisaki-in-front-of-clock-vppfrrc7lacqxdox.gif")

        await new_channel.send(embed=embed)

    @commands.hybrid_command(name="mute", help="Moderator:Mute a member (adds 'Muted' role)")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(member="The member to mute", reason="The reason for the mute")
    async def mute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await ctx.send("Creating 'Muted' role...")
            muted_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, speak=False, send_messages=False)
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted. Reason: {reason}")

    @commands.hybrid_command(name="unmute", help="Moderator:Unmute a member")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(member="The member to unmute")
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await ctx.send(f"🔊 {member.mention} has been unmuted.")
        else:
            await ctx.send("❌ User is not muted.")

    @commands.hybrid_command(name="kick", help="Moderator:Kick a member")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} has been kicked. Reason: {reason}")

    @commands.hybrid_command(name="ban", help="Moderator:Ban a member")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="The reason for the ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} has been banned. Reason: {reason}")

    @commands.hybrid_command(name="warn", help="Moderator: Warn a user. 3 warnings will result in a kick")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.bot:
            return await ctx.send("🤖 You can't warn a bot.")

        guild_id = ctx.guild.id
        user_id = member.id
        automod = self.bot.get_cog("AutoMod")
        if automod:
            count = await automod.on_message_warn(user_id, guild_id)
        else:
            count = 1  

        await ctx.send(f"⚠️ {member.mention} has been warned. ({count}/10) Reason: {reason}")
        if automod:
            if count == 5:
                try:
                    await ctx.guild.kick(member, reason="Too many warnings (5)")
                    await ctx.send(f"👢 {member.mention} has been kicked for reaching 5 warnings.")
                except:
                    pass
            elif count >= 10:
                try:
                    await ctx.guild.ban(member, reason="Too many warnings (10)")
                    await ctx.send(f"⛔ {member.mention} has been banned for reaching 10 warnings.")
                except:
                    pass
                        
    async def banned_users_autocomplete(self, interaction, current: str):
        if not interaction.guild:
            return []
        bans = [ban async for ban in interaction.guild.bans()]
        return [
            discord.app_commands.Choice(
                name=f"{ban.user.name}#{ban.user.discriminator}",
                value=str(ban.user.id)
            )
            for ban in bans
            if current.lower() in f"{ban.user.name}#{ban.user.discriminator}".lower()
        ][:25] 
        
    async def clear_user_warnings(self, user_id: int, guild_id: int):
        automod = self.bot.get_cog("AutoMod")  
        if automod:
            await automod.reset_warnings(user_id, guild_id)

    @commands.hybrid_command(name="unban",help="Moderator: Unban a user and reset their warnings")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(user="Select the user to unban")
    @app_commands.autocomplete(user=banned_users_autocomplete)
    async def unban(self, ctx: commands.Context, *, user: str):
        banned_users = [ban async for ban in ctx.guild.bans()]
        target = None

        # Match by username#discriminator or by ID
        if user.isdigit():
            user_id = int(user)
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    target = ban_entry.user
                    break
        else:
            if "#" in user:
                name, discrim = user.split("#")
                for ban_entry in banned_users:
                    if ban_entry.user.name == name and ban_entry.user.discriminator == discrim:
                        target = ban_entry.user
                        break

        if not target:
            return await ctx.send(f"❌ No banned user found matching `{user}`.")

        try:
            await ctx.guild.unban(target)
            await self.clear_user_warnings(target.id, ctx.guild.id)
            await ctx.send(f"✅ Successfully unbanned {target.mention} and cleared their warnings.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban this user.")
        except Exception as e:
            await ctx.send(f"❌ Failed to unban: `{e}`")


    @commands.hybrid_command(name="lock", help="Moderator:Lock the current channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        overwrite.view_channel = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("🔒 Channel is now locked and hidden from @everyone.")

    @commands.hybrid_command(name="unlock", help="Moderator:Unlock the current channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Channel is now unlocked.")

    @commands.hybrid_command(name="deletechannel", help="Moderator:Delete a channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def deletechannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target_channel = channel or ctx.channel
        channel_name = target_channel.name

        if target_channel != ctx.channel:
            await ctx.send(f"🗑️ Channel `{channel_name}` deleted.", ephemeral=True)
        try:
            await ctx.author.send(f"You deleted the channel `{channel_name}`.")
        except discord.Forbidden:
            if target_channel == ctx.channel:
                await ctx.send("❌ Could not send you a DM.")

        await target_channel.delete()
        
    @commands.hybrid_command(name="createchannel", help="Moderator:Create a new channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def createchannel(self, ctx: commands.Context, name: str, category: discord.CategoryChannel = None):
        target_category = category or ctx.channel.category
        new_channel = await ctx.guild.create_text_channel(name=name, category=target_category)
        await ctx.send(f"✅ Channel `{new_channel.name}` created in `{target_category.name if target_category else 'No Category'}`.")
        
    @commands.hybrid_command(name="clearchat", help="Moderator: Clear chats of the current channel")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(limit="Number of messages to clear")
    async def clearchat(self, ctx: commands.Context, limit: int = 100):
        if limit > 500 : 
            limit = 500
        
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=limit)
        await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)

    @commands.hybrid_command(name="auditlog", description="View server audit logs")
    @commands.guild_only()
    @commands.has_permissions(view_audit_log=True)
    async def auditlog(self, ctx: commands.Context):
        if ctx.interaction is None:
            return await ctx.send("❌ Please use `/auditlog` (slash command) for better security.")
        entries = [entry async for entry in ctx.guild.audit_logs(limit=300)]
        if not entries:
            return await ctx.send("No audit log entries found.")

        view = AuditLogView(entries, ctx)
        await ctx.interaction.response.send_message(
            embed=view.get_page_embed(),
            view=view,
            ephemeral=True
        )

    
async def setup(bot):
    await bot.add_cog(Moderator(bot))
    print("📦 Loaded moderator cog.")
