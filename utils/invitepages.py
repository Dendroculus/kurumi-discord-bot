import discord
from discord import ui, Interaction

class InvitePages(ui.View):
    """
    Simple paginated view for a list of embeds.
    """
    def __init__(self, embeds):
        super().__init__(timeout=180) # Good practice to have a timeout
        self.embeds = embeds
        self.index = 0

        # Only create buttons if there are actually multiple pages
        if len(self.embeds) > 1:
            self.page_btn = ui.Button(
                label=f"{self.index + 1}/{len(self.embeds)}", 
                style=discord.ButtonStyle.secondary, 
                disabled=True
            )
            # Changed style to secondary (Gray) for a cleaner look
            self.prev_btn = ui.Button(label="◀", style=discord.ButtonStyle.secondary)
            self.next_btn = ui.Button(label="▶", style=discord.ButtonStyle.secondary)

            self.prev_btn.callback = self.go_prev
            self.next_btn.callback = self.go_next

            self.add_item(self.prev_btn)
            self.add_item(self.page_btn)
            self.add_item(self.next_btn)

    async def go_prev(self, interaction: Interaction):
        """Go to the previous embed page (wraps to the end)."""
        self.index = (self.index - 1) % len(self.embeds)
        self.page_btn.label = f"{self.index + 1}/{len(self.embeds)}"
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    async def go_next(self, interaction: Interaction):
        """Go to the next embed page (wraps to the start)."""
        self.index = (self.index + 1) % len(self.embeds)
        self.page_btn.label = f"{self.index + 1}/{len(self.embeds)}"
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)