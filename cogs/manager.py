import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
from datetime import timedelta
import re

class InvitePages(ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.index = 0

        self.page_btn = ui.Button(label=f"{self.index + 1}/{len(self.embeds)}", style=discord.ButtonStyle.secondary, disabled=True)
        self.prev_btn = ui.Button(label="◀", style=discord.ButtonStyle.danger)
        self.next_btn = ui.Button(label="▶", style=discord.ButtonStyle.danger)

        self.prev_btn.callback = self.go_prev
        self.next_btn.callback = self.go_next

        self.add_item(self.prev_btn)
        self.add_item(self.page_btn)
        self.add_item(self.next_btn)

    async def go_prev(self, interaction: Interaction):
        self.index = (self.index - 1) % len(self.embeds)
        self.page_btn.label = f"{self.index + 1}/{len(self.embeds)}"
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    async def go_next(self, interaction: Interaction):
        self.index = (self.index + 1) % len(self.embeds)
        self.page_btn.label = f"{self.index + 1}/{len(self.embeds)}"
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)
        
color_choices = [
    app_commands.Choice(name="🔴 Red", value="#ff0000"),
    app_commands.Choice(name="🟢 Green", value="#00ff00"),
    app_commands.Choice(name="🔵 Blue", value="#0000ff"),
    app_commands.Choice(name="🟣 Purple", value="#800080"),
    app_commands.Choice(name="🟡 Yellow", value="#ffff00"),
    app_commands.Choice(name="⚫ Black", value="#000000"),
    app_commands.Choice(name="⚪ White", value="#ffffff"),
    app_commands.Choice(name="🩷 Pink", value="#ff69b4"),
    app_commands.Choice(name="🟤 Brown", value="#8b4513"),
    app_commands.Choice(name="🧡 Orange", value="#ffa500"),
]

class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="slowmode", help="Manager:Set slowmode for a channel")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(seconds="The slowmode delay in seconds (0 to disable)", channel="The channel to apply slowmode to")
    async def slowmode(self, ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        target_channel = channel or ctx.channel
        if seconds < 0 or seconds > 21600:
            return await ctx.send("⚠️ Slowmode must be between 0 and 21600 seconds.")
        await target_channel.edit(slowmode_delay=seconds)
        await ctx.send(f"🐢 Slowmode in {target_channel.mention} set to **{seconds}**s.")

    @commands.hybrid_command(name="invites", help="Manager:View all active server invites")
    @commands.has_permissions(administrator=True)
    async def invites(self, ctx: commands.Context):
        invites = await ctx.guild.invites()
        embeds = []

        for inv in invites:
            embed = discord.Embed(title="📨 Server Invites", color=discord.Color.red())
            embed.add_field(name="**👤 Inviter**", value=f"{inv.inviter.mention}\n`{inv.inviter}`", inline=True)
            embed.add_field(name="**🔗 Invite code**", value=f"`{inv.code}`\n{inv.uses} uses", inline=True)
            embed.set_thumbnail(url=inv.inviter.display_avatar.url)
            embeds.append(embed)

        if not embeds:
            await ctx.send("No invites found.")
            return

        view = InvitePages(embeds)
        await ctx.send(embed=embeds[0], view=view)

    @commands.hybrid_command(name="createinvite", help="Manager:Create a new invite link")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel to create invite for", max_uses="Max uses (0 = unlimited)", max_age="Expiry time in seconds (0 = never)")
    async def createinvite(self, ctx: commands.Context, channel: discord.TextChannel = None, max_uses: int = 0, max_age: int = 0):
        channel = channel or ctx.channel
        invite = await channel.create_invite(max_uses=max_uses, max_age=max_age)
        await ctx.send(f"✅ Created invite link: {invite.url}")

    @commands.hybrid_command(name="deleteinvite", help="Manager:Delete an existing invite link or all invites")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(code="Select an invite code or 'all' to delete all invites")
    async def deleteinvite(self, ctx: commands.Context, code: str):
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
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to rename", new_name="The new name for the role")
    async def rolename(self, ctx: commands.Context, role: discord.Role, *, new_name: str):
        try:
            await role.edit(name=new_name)
            await ctx.send(f"✏️ Renamed role to `{new_name}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that role.")

    @commands.hybrid_command(name="setnick", help="Manager:Change a member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(member="The member to change the nickname of", nickname="The new nickname for the member")
    async def setnick(self, ctx: commands.Context, member: discord.Member, *, nickname: str):
        try:
            await member.edit(nick=nickname)
            await ctx.send(f"✏️ Nickname for {member.mention} changed to `{nickname}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change that user's nickname.")

    @commands.hybrid_command(name="modules", help="Manager:List available modules")
    async def modules(self, ctx: commands.Context):
        await ctx.send("📦 **Modules:**\n• Moderation\n• Information\n• Manager")

    # helper
    def parse_duration(self, duration_str):
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
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to timeout", duration="Duration (e.g., 10s, 5m, 1h, 1d)", reason="Reason for timeout")
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        delta = self.parse_duration(duration)  # use cog helper
        if not delta:
            await ctx.reply("❌ Invalid format. Use numbers followed by s, m, h, or d (e.g., `10s`, `5m`).")
            return

        try:
            until_time = discord.utils.utcnow() + delta
            await member.edit(timed_out_until=until_time, reason=reason)
            await ctx.reply(f"✅ {member.mention} has been timed out for {duration}.")
        except discord.Forbidden:
            await ctx.reply("❌ I don't have permission to timeout this member.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to timeout: `{e}`")

    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        roles = [role for role in interaction.guild.roles if current.lower() in role.name.lower()]
        return [
            app_commands.Choice(name=role.name, value=role.name)
            for role in roles[:25]
        ]

    @commands.hybrid_command(name="addrole", help="Manager:Add a new role or assign it to a user")
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role_name="The name of the role to create or assign", member="The member to assign the role to (optional)")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def addrole(self, ctx: commands.Context, role_name: str, member: discord.Member = None):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        
        if not role:
            try:
                role = await ctx.guild.create_role(name=role_name)
                await ctx.send(f"🎉 Role `{role_name}` created.")
            except discord.Forbidden:
                return await ctx.send("❌ I don't have permission to create roles.")

        if member:
            try:
                await member.add_roles(role)
                await ctx.send(f"✅ Role `{role.name}` assigned to {member.mention}.")
            except discord.Forbidden:
                await ctx.send(f"❌ I don't have permission to assign roles to that member.")
        else:
            await ctx.send(f"✅ Role `{role_name}` is ready. Mention a member to assign it.")


    @commands.hybrid_command(name="delrole", help="Manager:Remove a role from members or delete it")
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(
        role="The role to modify",
        action="Choose what to do with the role",
        member="The member to remove the role from (only if choosing 'choose')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Remove from all members", value="remove_all"),
        app_commands.Choice(name="Remove from specific member", value="choose"),
        app_commands.Choice(name="Delete role completely", value="delete")
    ])
    async def delrole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        action: app_commands.Choice[str],
        member: discord.Member = None
    ):
        try:
            if action.value == "remove_all":
                removed_count = 0
                for m in role.members:
                    await m.remove_roles(role)
                    removed_count += 1
                await ctx.send(f"✅ Removed `{role.name}` from all {removed_count} members.")
            
            elif action.value == "choose":
                if not member:
                    return await ctx.send("❌ You must select a member to remove this role from.")
                if role not in member.roles:
                    return await ctx.send(f"❌ {member.mention} does not have the `{role.name}` role.")
                await member.remove_roles(role)
                await ctx.send(f"✅ Removed `{role.name}` from {member.mention}.")
            
            elif action.value == "delete":
                await role.delete()
                await ctx.send(f"🗑️ Role `{role.name}` has been deleted.")

        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to modify this role.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.hybrid_command(name="listmods", help="Manager:List all moderators")
    async def listmods(self, ctx: commands.Context):
        mod_roles = [role.mention for role in ctx.guild.roles if role.permissions.manage_messages and not role.is_default()]
        if mod_roles:
            await ctx.send("🛡️ Moderator Roles:\n" + "\n".join(mod_roles))
        else:
            await ctx.send("No moderator roles found.")

    @commands.hybrid_command(name="nick", help="Manager:Change bot nickname")
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(new_nick="The new nickname for the bot")
    async def nick(self, ctx: commands.Context, *, new_nick: str):
        try:
            await ctx.guild.me.edit(nick=new_nick)
            await ctx.send(f"✅ Changed nickname to `{new_nick}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change my nickname.")

    @commands.hybrid_command(name="rolecolor", help="Manager: Change a role's color")
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to change the color of", color="The new color to apply")
    @app_commands.choices(color=color_choices)
    async def rolecolor(self, ctx: commands.Context, role: discord.Role, color: app_commands.Choice[str]):
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

async def setup(bot):
    await bot.add_cog(Manager(bot))
    print("📦 Loaded manager cog.")