import discord
from discord.ext import commands
from discord import app_commands, PermissionOverwrite
from collections import defaultdict
from typing import Optional
import re
from datetime import timedelta
import logging
from constants.configs import MAX_WARNINGS
from utils.database import db
from utils.moderationUtils import enforce_punishments
from constants.configs import NO_REASON
from utils.auditView import AuditLogView
"""
moderator.py

Moderator cog providing common moderation utilities and audit inspection helpers.

Responsibilities:
- Provide moderation commands: nuke, mute/unmute (timeouts), kick, ban, warn, unban.
- Channel and role management commands: lock/unlock channels, create/delete channels, add role permissions for locked channels.
- Role management: create, assign, rename, delete role-related actions are covered in manager.py; this cog focuses on moderator actions.
- Audit log viewing: paginated, ephemeral view of recent audit log entries for authorized users.
- Integrates with `utils.database.db` for warning persistence and `utils.moderation_utils.enforce_punishments`
  to apply escalation logic based on warning counts.

Notes:
- The cog expects the bot to have permission to perform the requested actions; permission errors are caught and reported.
- Time durations are parsed using compact strings like '10s', '5m', '1h', '1d'.
- This file only adds documentation; no logic or behavior has been modified.
"""

class Moderator(commands.Cog):
    """
    Moderator cog implementing core moderation commands and helpers.

    Commands included:
    - nuke: clone & delete a channel
    - mute/unmute: timeout/untimeout members
    - kick/ban/unban: basic member bans and unbans
    - warn: increment persisted warning count and apply punishments
    - lock/unlock: restrict channel viewing/sending to top role/admins
    - deletechannel/createchannel: manage text channels
    - clearchat: bulk message deletion
    - auditlog: ephemeral paginated audit log viewing
    - addlockedmember: allow a role to access an already-locked channel

    The cog also exposes parse_duration helper for compact duration strings.
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("bot")
        if not hasattr(bot, "warnings"):
            bot.warnings = defaultdict(int)

    def parse_duration(self, duration_str: str):
        """
        Parse a compact duration string like '10s', '5m', '1h', or '1d' into a timedelta.

        Returns:
            datetime.timedelta or None if parsing fails.
        """
        match = re.fullmatch(r"(\d+)([smhd])", duration_str)
        if not match:
            return None
        value, unit = int(match.group(1)), match.group(2)
        if unit == "s":
            return timedelta(seconds=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)

    @commands.hybrid_command(name="nuke", help="Moderator:Nuke the current channel (delete & recreate)")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(channel="The channel to nuke. Defaults to the current channel.")
    async def nuke(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Clone and delete the target channel (default: current channel), then post a short
        notification embed in the newly created channel.
        """
        if ctx.interaction:
            await ctx.defer()
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

    @commands.hybrid_command(name="mute", help="Moderator: Temporarily mute (timeout) a member")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to timeout", duration="Duration (e.g., 10s, 5m, 1h, 1d). Defaults to 10m.", reason="The reason for the timeout")
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = NO_REASON):
        """
        Apply a timeout (communication disable) to a member for a parsed duration.
        """
        delta = self.parse_duration(duration)
        if not delta:
            return await ctx.send("❌ Invalid duration. Use numbers followed by s, m, h, or d (e.g., `10s`, `5m`).")
        try:
            until = discord.utils.utcnow() + delta
            await member.edit(timed_out_until=until, reason=reason)
            await ctx.send(f"🔇 {member.mention} has been muted (timeout) for {duration}. Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to timeout this member.")
        except Exception as e:
            await ctx.send(f"❌ Failed to timeout: `{e}`")

    @commands.hybrid_command(name="unmute", help="Moderator: Remove timeout from a member")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to untimeout")
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Remove a timeout from a member."""
        try:
            await member.edit(timed_out_until=None, reason="Manual unmute")
            await ctx.send(f"🔊 {member.mention} has been unmuted.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify this member.")
        except Exception as e:
            await ctx.send(f"❌ Failed to unmute: `{e}`")

    @commands.hybrid_command(name="kick", help="Moderator:Kick a member")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = NO_REASON):
        """Kick a member from the guild with basic safety checks (self/owner/bot)."""
        if member == ctx.author:
            return await ctx.send("You can't kick yourself.")
        if member == ctx.guild.owner:
            return await ctx.send("You can't kick the server owner.")
        if member == ctx.bot.user:
            return await ctx.send("You can't make me kick myself.")
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} has been kicked. Reason: {reason}")
        

    @commands.hybrid_command(name="ban", help="Moderator:Ban a member")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="The reason for the ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = NO_REASON):
        """Ban a member from the guild with basic safety checks."""
        if member == ctx.author:
            return await ctx.send("You can't ban yourself.")
        if member == ctx.guild.owner:
            return await ctx.send("You can't ban the server owner.")
        if member == ctx.bot.user:
            return await ctx.send("You can't make me ban myself.")
        
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} has been banned. Reason: {reason}")

    @commands.hybrid_command(name="warn", help="Moderator: Warn a user. Escalation is automatic at thresholds")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = NO_REASON):
        """
        Issue a persistent warning to a member and run the same escalation logic used by AutoMod.

        Persists a warning count via utils.database.db.increase_warning and calls enforce_punishments.
        """
        if member.bot:
            return await ctx.send("🤖 You can't warn a bot.")

        count = await db.increase_warning(member.id, ctx.guild.id)
        await ctx.send(f"⚠️ {member.mention} has been warned. ({count}/{MAX_WARNINGS}) Reason: {reason}")

        # Apply the same consolidated punishment logic as AutoMod
        await enforce_punishments(
            member=member,
            count=count,
            channel=ctx.channel,
            logger=self.logger,
        )
                        
    async def banned_users_autocomplete(self, interaction, current: str):
        """
        Autocomplete helper returning recently banned users for the unban command.

        Returns up to 25 matching choices based on the current input.
        """
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
    
    @commands.hybrid_command(name="removewarnings", help="Moderator: Remove all warnings for a user")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="The member to remove warnings from")
    async def removewarnings(self, ctx: commands.Context, member: discord.Member):
        """
        Remove all warnings for a user.
        """
        await db.reset_warnings(member.id, ctx.guild.id)
        await ctx.send(f"All warnings for {member.mention} have been removed.")
    
    @commands.hybrid_command(name="unban",help="Moderator: Unban a user and reset their warnings")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(user="Select the user to unban")
    @app_commands.autocomplete(user=banned_users_autocomplete)
    async def unban(self, ctx: commands.Context, *, user: str):
        """
        Unban a user by ID or username#discriminator and reset their persisted warnings.
        """
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
            await db.reset_warnings(target.id, ctx.guild.id)
            await ctx.send(f"Successfully unbanned {target.mention} and cleared their warnings.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban this user.")
        except Exception as e:
            await ctx.send(f"❌ Failed to unban: `{e}`")


    @commands.hybrid_command(name="lock", help="Moderator: Lock the current channel for everyone except top role and admins")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        """
        Lock the current text channel by setting restrictive permission overwrites.

        The default role is denied view/send; the guild's top role and administrators retain access.
        """
        channel = ctx.channel
        guild = ctx.guild

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("❌ This command must be used in a text channel.")

        top_role = guild.roles[-1]

        overwrites = {
            guild.default_role: PermissionOverwrite(view_channel=False, send_messages=False),
            top_role: PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for member in guild.members:
            if member.guild_permissions.administrator or member == guild.owner:
                overwrites[member] = PermissionOverwrite(view_channel=True, send_messages=True)

        await channel.edit(overwrites=overwrites, reason=f"Locked by {ctx.author}")
        await ctx.send("🔒 Channel locked: only top role and admins (including admin bots) can view/send.", ephemeral=True)

    @commands.hybrid_command(name="unlock", help="Moderator:Unlock the current channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        """Restore send_messages permission for the default role to unlock the channel."""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Channel is now unlocked.")

    @commands.hybrid_command(name="deletechannel", help="Moderator:Delete a channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def deletechannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Delete the specified channel (or current channel). Notifies the command author via DM when possible.
        """
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
        """Create a new text channel optionally under a specified category."""
        target_category = category or ctx.channel.category
        new_channel = await ctx.guild.create_text_channel(name=name, category=target_category)
        await ctx.send(f"Channel `{new_channel.name}` created in `{target_category.name if target_category else 'No Category'}`.")
        
    @commands.hybrid_command(name="clearchat", help="Moderator: Clear chats of the current channel")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(limit="Number of messages to clear")
    async def clearchat(self, ctx: commands.Context, limit: int = 100):
        """
        Bulk delete recent messages in the current channel up to the provided limit.
        Caps the limit to 500 to avoid excessive purges.
        """
        if limit > 500 : 
            limit = 500
        
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=limit)
        await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)

    @commands.hybrid_command(name="auditlog", description="View server audit logs")
    @commands.guild_only()
    @commands.has_permissions(view_audit_log=True)
    async def auditlog(self, ctx: commands.Context):
        """
        Ephemeral command to fetch recent audit log entries and present them in a paginated view.

        For security, prefers slash invocation (checks ctx.interaction) and returns an ephemeral response.
        """
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

    @commands.hybrid_command(name="addlockedmember")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def addlockedmember(
        self,
        ctx: commands.Context,
        role: Optional[discord.Role] = None,
        send_messages: bool = True
    ):
        """
        Grant a role access to a channel that has been locked with the `lock` command.

        Args:
            role: Role to grant access to.
            send_messages: Whether the role should also be allowed to send messages.
        """
        channel = ctx.channel

        if role is None:
            return await ctx.send("❌ Please provide a role (e.g. /addlockedmember role:@Moderators).")

        try:
            await channel.set_permissions(role, view_channel=True, send_messages=send_messages)
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to edit channel permissions.")
        except Exception as e:
            return await ctx.send(f"❌ Failed to set permissions: `{e}`")

        await ctx.send(f"Role {role.mention} was given access to this channel.")
        
async def setup(bot):
    await bot.add_cog(Moderator(bot))
    logging.getLogger("bot").info("Loaded events cog.")