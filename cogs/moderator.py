import discord
from discord.ext import commands
from discord import app_commands
from collections import defaultdict

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

    @commands.hybrid_command(name="warn", help="Moderator:Warn a user. 3 warnings will result in a kick")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.bot:
            return await ctx.send("🤖 You can't warn a bot.")

        warnings = self.bot.warnings
        warnings[member.id] = min(warnings[member.id] + 1, 10)  # cap at 10
        count = warnings[member.id]

        await ctx.send(f"⚠️ {member.mention} has been warned. ({count}/10) Reason: {reason}")

        if count == 3:
            try:
                await member.kick(reason="Reached 3 warnings")
                await ctx.send(f"👢 {member.mention} has been kicked for reaching 3 warnings.")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to kick this user.")

        elif count == 10:
            try:
                await member.ban(reason="Reached 10 warnings")
                await ctx.send(f"⛔ {member.mention} has been banned for reaching 10 warnings.")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to ban this user.")


    @commands.hybrid_command(name="unban", help="Moderator:Unban a user by ID or username#discriminator")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(user="The ID or username#discriminator of the user to unban")
    async def unban(self, ctx: commands.Context, *, user: str):
        banned_users = await ctx.guild.bans()
        target = None

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
            await ctx.send(f"✅ Successfully unbanned {target.mention}.")
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
        if limit > 100 : 
            limit = 100
        
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=limit)
        await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)


async def setup(bot):
    await bot.add_cog(Moderator(bot))
    print("📦 Loaded moderator cog.")
