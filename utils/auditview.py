import discord
class AuditLogView(discord.ui.View):
    """
    Paginated ephemeral view to browse audit log entries.

    Attributes:
        entries: list of AuditLogEntry objects (from discord.py).
        ctx: command context that invoked the view (used to restrict interactions to the author).
        per_page: number of entries per page to display.
        current_page: currently displayed page index.
    """
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
        """
        Produce a human-friendly representation of an audit log entry target.

        Handles multiple possible target types (Member/Role/Integration/Object) and falls back to str().
        """
        if hasattr(target, "name"):
            return target.name
        if isinstance(target, discord.PartialIntegration):
            return f"{target.name} (Integration)"
        if isinstance(target, discord.Object):
            return "Unknown Integration"
        try:
            return str(target)
        except Exception:
            return "Unknown"

    def get_page_embed(self):
        """
        Build a discord.Embed representing the current page of audit log entries.

        Each entry displays the acting user, the target, the action type, and the reason (if any).
        """
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
        """Enable/disable the pagination buttons according to the current page index."""
        for child in self.children:
            if child.label == "Previous":
                child.disabled = self.current_page == 0
            elif child.label == "Next":
                child.disabled = self.current_page >= self.total_pages - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.danger)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Show the previous audit log page.

        Only the original command author may use the pagination controls.
        """
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.danger)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Show the next audit log page.

        Only the original command author may use the pagination controls.
        """
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)