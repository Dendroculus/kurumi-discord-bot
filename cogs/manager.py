import logging
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Attachment
from datetime import timedelta
import re
from typing import Optional
from utils.colorChoices import color_choices
from utils.invitePages import InvitePages
from constants.configs import LARGE_SERVER_MEMBER_THRESHOLD, INVITES_CONFIRM_TIMEOUT, INVITES_DISPLAY_LIMIT
from utils.discordHelpers import create_choices

"""
manager.py

Server manager cog providing utilities for server administrators.

Responsibilities:
- Create and manage invites, roles, and channel settings.
- Provide interactive utilities such as emoji creation and paginated invite displays.
- Expose management commands with appropriate permission checks and helpful UX.

Key classes and functions:
- InvitePages: simple paginated view for browsing embeds (used for invites output).
- Manager: Cog exposing hybrid commands to manage slowmode, invites, roles, nicknames, timeouts, channel names, and role colors.

Notes:
- Commands use both text/hybrid and application command conveniences (autocomplete, choices).
- This module intentionally does not alter Discord objects beyond the explicit administrative actions; permission errors are handled and reported to the invoking user.
- The `invites` command includes a safety path for large servers: it warns the caller and requires confirmation
  before proceeding, and only displays up to a configured maximum number of invites to avoid huge memory/time usage.
"""

class Manager(commands.Cog):
    """
    Management cog exposing administrative commands for server maintainers.

    Commands include:
    - slowmode: set channel slowmode delay
    - invites/createinvite/deleteinvite: manage server invites
    - rolename/setnick: edit roles and nicknames
    - timeout: apply moderation timeouts by duration string
    - createrole/assignrole/delrole: create, assign, and remove/delete roles
    - listmods: list roles with moderation permissions
    - nick: change the bot's nickname
    - rolecolor: change a role's color using predefined choices
    - renamechannel: rename a text channel
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="slowmode", help="Manager:Set slowmode for a channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(seconds="The slowmode delay in seconds (0 to disable)", channel="The channel to apply slowmode to")
    async def slowmode(self, ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        """Set the slowmode delay for a text channel (0 to disable)."""
        target_channel = channel or ctx.channel
        if seconds < 0 or seconds > 21600:
            return await ctx.send("⚠️ Slowmode must be between 0 and 21600 seconds.")
        await target_channel.edit(slowmode_delay=seconds)
        await ctx.send(f"🐢 Slowmode in {target_channel.mention} set to **{seconds}**s.")

    @commands.hybrid_command(name="invites", help="Manager: View all active server invites")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def invites(self, ctx: commands.Context):
        """List active server invites in a compact table view (Safe for large servers)."""
        
        if ctx.guild.member_count > LARGE_SERVER_MEMBER_THRESHOLD:
            if ctx.interaction:
                await ctx.defer(ephemeral=True)
            
            confirm_msg = await ctx.send(
                f"⚠️ **Large Server Detected** ({ctx.guild.member_count} members).\n"
                f"Fetching invites might take a moment. Reply `yes` within {INVITES_CONFIRM_TIMEOUT}s to proceed."
            )

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'

            try:
                await self.bot.wait_for('message', check=check, timeout=INVITES_CONFIRM_TIMEOUT)
            except TimeoutError:
                return await ctx.send("❌ Timed out. Cancelled invite fetch.")
            
            try:
                await confirm_msg.delete()
            except Exception:
                pass

        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        try:
            invites = await ctx.guild.invites()
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to view invites.")
        except Exception as e:
            return await ctx.send(f"❌ Error fetching invites: `{e}`")

        if not invites:
            return await ctx.send("No active invites found.")

        original_count = len(invites)
        if len(invites) > INVITES_DISPLAY_LIMIT:
            invites = invites[:INVITES_DISPLAY_LIMIT]
            limit_warning = f" (Showing first {INVITES_DISPLAY_LIMIT} of {original_count})"
        else:
            limit_warning = f" ({original_count})"

        chunk_size = 10
        chunks = [invites[i:i + chunk_size] for i in range(0, len(invites), chunk_size)]

        embeds = []

        for chunk in chunks:
            embed = discord.Embed(
                title=f"Server Invites{limit_warning}",
                color=discord.Color.from_rgb(114, 137, 218)
            )
            
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)

            description_lines = []
            
            for inv in chunk:
                link_str = f"[{inv.code}]({inv.url})"
                inviter_str = inv.inviter.mention if inv.inviter else "`System/Unknown`"
                
                description_lines.append(f"{link_str} created by {inviter_str}")

            embed.description = "\n".join(description_lines)
            
            if len(chunks) > 1:
                embed.set_footer(text=f"Page {len(embeds) + 1}/{len(chunks)}")
                
            embeds.append(embed)

        view = InvitePages(embeds)
        await ctx.send(embed=embeds[0], view=view)


    @commands.hybrid_command(name="createinvite", help="Manager:Create a new invite link")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel to create invite for", max_uses="Max uses (0 = unlimited)", max_age="Expiry time in seconds (0 = never)")
    async def createinvite(self, ctx: commands.Context, channel: discord.TextChannel = None, max_uses: int = 0, max_age: int = 0):
        """Create a new invite for a channel with optional max uses and expiry."""
        channel = channel or ctx.channel
        invite = await channel.create_invite(max_uses=max_uses, max_age=max_age)
        await ctx.send(f"Created invite link: {invite.url}")

    @commands.hybrid_command(name="deleteinvite", help="Manager:Delete an existing invite link or all invites")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(code="Select an invite code or 'all' to delete all invites")
    async def deleteinvite(self, ctx: commands.Context, code: str):
        """Delete a specific invite by code or delete all invites when 'all' is provided."""
        if ctx.interaction:
            await ctx.defer()
        invites = await ctx.guild.invites()

        if code.lower() == "all":
            if not invites:
                return await ctx.send("ℹ️ There are no invites to delete.")
            for invite in invites:
                await invite.delete()
            return await ctx.send("🗑️ Successfully deleted **all** invite links.")

        target = discord.utils.get(invites, code=code)
        if not target:
            return await ctx.send("❌ Invite code not found or not deletable.")

        await target.delete()
        await ctx.send(f"🗑️ Successfully deleted invite `{code}`.")

    @deleteinvite.autocomplete('code')
    async def autocomplete_invite_code(self, interaction: discord.Interaction, current: str):
        """
        Autocomplete handler for invite codes.

        Returns a list of matching invite code choices based on current input.
        """
        try:
            invites = await interaction.guild.invites()
            if not invites:
                return [app_commands.Choice(name="No invites found", value="")]

            choices = [
                app_commands.Choice(name=f"{invite.code} — {invite.inviter}", value=invite.code)
                for invite in invites if current.lower() in invite.code.lower()
            ][:24]  # Limit to 24 codes

            if "all".startswith(current.lower()):
                choices.insert(0, app_commands.Choice(name="Delete ALL invites", value="all"))

            return choices or [app_commands.Choice(name="No matching invites", value="")]
        except Exception as e:
            print(f"Autocomplete error: {e}")
            return [app_commands.Choice(name="❌ Error retrieving invites", value="")]

    @commands.hybrid_command(name="rolename", help="Manager:Change a role's name")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to rename", new_name="The new name for the role")
    async def rolename(self, ctx: commands.Context, role: discord.Role, *, new_name: str):
        """Rename a role to a new name, handling permission errors gracefully."""
        try:
            await role.edit(name=new_name)
            await ctx.send(f"✏️ Renamed role to `{new_name}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that role.")

    @commands.hybrid_command(name="setnick", help="Manager:Change a member's nickname")
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(member="The member to change the nickname of", nickname="The new nickname for the member")
    async def setnick(self, ctx: commands.Context, member: discord.Member, *, nickname: str):
        """Change a member's nickname (requires manage_nicknames permission)."""
        try:
            await member.edit(nick=nickname)
            await ctx.send(f"✏️ Nickname for {member.mention} changed to `{nickname}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change that user's nickname.")

    def parse_duration(self, duration_str):
        """
        Parse a compact duration string into a timedelta.

        Accepted formats: <number>[s|m|h|d], e.g. "10s", "5m", "1h", "1d".

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

    @commands.hybrid_command(name="timeout", help="Manager:Timeout a user")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to timeout", duration="Duration (e.g., 10s, 5m, 1h, 1d)", reason="Reason for timeout")
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """
        Apply a communication timeout (mute) to a member for a parsed duration.

        Duration must be in the compact format accepted by parse_duration.
        """
        delta = self.parse_duration(duration)  
        if not delta:
            await ctx.reply("❌ Invalid format. Use numbers followed by s, m, h, or d (e.g., `10s`, `5m`).")
            return

        try:
            until_time = discord.utils.utcnow() + delta
            await member.edit(timed_out_until=until_time, reason=reason)
            await ctx.reply(f"{member.mention} has been timed out for {duration}.")
        except discord.Forbidden:
            await ctx.reply("❌ I don't have permission to timeout this member.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to timeout: `{e}`")

    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        """
        Autocomplete helper that returns role names matching the current input.

        Returns up to 25 choices.
        """
        roles = [role for role in interaction.guild.roles if current.lower() in role.name.lower()]
        return [
            app_commands.Choice(name=role.name, value=role.name)
            for role in roles[:25]
        ]

    @commands.hybrid_command(name="createrole", help="Manager: Create a new role (with optional color)")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(
        role_name="The name of the role to create",
        color="Optional preset color for the role"
    )
    @app_commands.choices(color=color_choices)
    async def createrole(self, ctx: commands.Context, role_name: str, color: Optional[app_commands.Choice[str]] = None):
        """
        Create a role in the guild. Optionally apply a preset color selection.

        If the role already exists, informs the caller instead of creating a duplicate.
        """
        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            try:
                colour = discord.Color(int(color.value.lstrip("#"), 16)) if color else discord.Color.default()
                role = await guild.create_role(name=role_name, colour=colour)
                await ctx.send(f"Role `{role_name}` created{' with ' + color.name if color else ''} color.")
            except discord.Forbidden:
                return await ctx.send("❌ I don't have permission to create roles.", ephemeral=True)
            except Exception as e:
                return await ctx.send(f"❌ Failed to create role: `{e}`", ephemeral=True)
        else:
            await ctx.send(f"ℹRole `{role_name}` already exists.")
    
    @commands.hybrid_command(name="assignrole", help="Manager: Assign an existing role to a user")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(
        role_name="The name of the existing role to assign",
        member="The member to assign the role to (mention or ID)"
    )
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def assignrole(self, ctx: commands.Context, role_name: str, member: Optional[discord.Member] = None):
        """Assign an existing role (by name) to a specified member."""
        guild = ctx.guild
        if guild is None:
            return await ctx.send("❌ This command must be used in a server.")

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            return await ctx.send(f"❌ Role `{role_name}` not found.", ephemeral=True)

        if not member:
            return await ctx.send("❌ Please specify a member to assign the role to.", ephemeral=True)

        try:
            await member.add_roles(role)
            await ctx.send(f"Role `{role.name}` assigned to {member.mention}.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to assign roles to {member.mention}.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Failed to assign role: `{e}`", ephemeral=True)


    @commands.hybrid_command(name="delrole", help="Manager:Remove a role from members or delete it")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(
        role="The role to modify",
        action="Choose what to do with the role",
        member="The member to remove the role from (only if choosing 'choose')"
    )
    @app_commands.choices(action=create_choices({
        "Remove from all members": "remove_all",
        "Remove from specific member": "choose",
        "Delete role completely": "delete"
    }))
    async def delrole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        action: app_commands.Choice[str],
        member: discord.Member = None
    ):
        """
        Modify a role based on the selected action:
        - remove_all: remove role from every member who has it.
        - choose: remove role from a specific provided member.
        - delete: delete the role from the guild.
        """
        try:
            if action.value == "remove_all":
                removed_count = 0
                for m in role.members:
                    await m.remove_roles(role)
                    removed_count += 1
                await ctx.send(f"Removed `{role.name}` from all {removed_count} members.", ephemeral=True)
            
            elif action.value == "choose":
                if not member:
                    return await ctx.send("❌ You must select a member to remove this role from.", ephemeral=True)
                if role not in member.roles:
                    return await ctx.send(f"❌ {member.mention} does not have the `{role.name}` role.", ephemeral=True)
                await member.remove_roles(role)
                await ctx.send(f"Removed `{role.name}` from {member.mention}.", ephemeral=True)
            
            elif action.value == "delete":
                await role.delete()
                await ctx.send(f"Role `{role.name}` has been deleted.", ephemeral=True)

        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to modify this role.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", ephemeral=True)

    @commands.hybrid_command(name="listmods", help="Manager:List all moderators")
    @commands.guild_only()
    async def listmods(self, ctx: commands.Context):
        """List roles that have message moderation permissions (manage_messages)."""
        mod_roles = [role.mention for role in ctx.guild.roles if role.permissions.manage_messages and not role.is_default()]
        if mod_roles:
            await ctx.send("🛡️ Moderator Roles:\n" + "\n".join(mod_roles))
        else:
            await ctx.send("No moderator roles found.")

    @commands.hybrid_command(name="nick", help="Manager:Change bot nickname")
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(new_nick="The new nickname for the bot")
    async def nick(self, ctx: commands.Context, *, new_nick: str):
        """Change the bot's nickname in the guild (requires manage_nicknames)."""
        try:
            await ctx.guild.me.edit(nick=new_nick)
            await ctx.send(f"Changed nickname to `{new_nick}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change my nickname.")

    @commands.hybrid_command(name="rolecolor", help="Manager: Change a role's color")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to change the color of", color="The new color to apply")
    @app_commands.choices(color=color_choices)
    async def rolecolor(self, ctx: commands.Context, role: discord.Role, color: app_commands.Choice[str]):
        """Change a role's color according to a preset color choice and report the change with an embed."""
        try:
            hex_value = color.value.lstrip("#")
            hex_color = discord.Color(int(hex_value, 16))
            await role.edit(color=hex_color)

            embed = discord.Embed(
                title="🌈 Role Color Changed",
                description=f"`{role.name}` is now `{color.name}` ({color.value})",
                color=hex_color
            )
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that role.")
            
    @commands.hybrid_command(name="renamechannel", help="Manager: Rename a channel")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(channel="The channel to rename", new_name="The new name for the channel")
    async def renamechannel(self, ctx:commands.Context, channel: discord.TextChannel, *, new_name: str):
        """Rename a text channel; reports permission errors to the caller."""
        try:
            await channel.edit(name=new_name)
            await ctx.send(f"✏️ Renamed channel to `{new_name}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that channel.")

    @app_commands.command(name="createemoji", description="Manager: Create a custom emoji")
    @app_commands.guild_only()
    @app_commands.describe(
        image="Image file for the emoji (PNG/JPG/GIF, max 256KB)",
    )
    @app_commands.checks.has_permissions(manage_emojis=True)
    async def createemoji(
        self, 
        interaction: Interaction, 
        image: Attachment, 
        name: str,
        ):
        """
        Create a custom emoji from an uploaded image file.
        """
        file_extension = [ "jpeg", "png", "gif", "webp", "avif", "jpg"]
        
        extension = image.filename.split(".")[-1].lower()
        if image.size > 256 * 1024:
            return await interaction.response.send_message("Please upload an image file smaller than 256KB.", ephemeral=True)
            
        if extension not in file_extension:
            return await interaction.response.send_message(f"Unsupported file format. Supported file format : {', '.join(file_extension).upper()} images.", ephemeral=True)
        
        await interaction.response.defer()
        
        image_bytes = await image.read()
        try:
            emoji = await interaction.guild.create_custom_emoji(name=name, image=image_bytes)
            await interaction.followup.send(f"Created emoji: <:{emoji.name}:{emoji.id}>", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to create emojis in this server.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create emoji: `{e}`", ephemeral=True)
        
async def setup(bot):
    await bot.add_cog(Manager(bot))
    logging.getLogger("bot").info("Loaded manager cog.")