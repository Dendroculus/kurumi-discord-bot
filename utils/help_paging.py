import discord
from discord.ui import View, Button
from constants.configs import PREFIX
from constants.emojis import KurumiEmojis

class HelpPages:
    """
    Helper class to generate and manage help pages for the bot's commands.
    """
    @staticmethod
    def generate_prefix_pages(bot_instance, categories):
        """
        Generate help pages categorizing commands by their help string prefix.
        """
        for command in bot_instance.commands:
            if command.hidden or not command.help:
                continue
            try:
                category, desc = command.help.split(":", 1)
                category = category.strip().capitalize()
                desc = desc.strip()
                if category in categories:
                    categories[category].append(
                        f"  `{PREFIX}{command.name}` — {desc}"
                    )
            except ValueError:
                continue
    
    @staticmethod
    def generate_slash_pages(bot_instance, categories):
        """
        Generate help pages for app commands (slash commands).
        """
        prefix_names = [cmd.name for cmd in bot_instance.commands] 
        """
        prefix_names : Ensures only slash-only commands are added, since some commands only support slash
        """
        for command in bot_instance.tree.get_commands():
            if not command.description:
                continue
            try:
                if command.name in prefix_names:
                    continue
                category, desc = command.description.split(":", 1)
                category = category.strip().capitalize()
                desc = desc.strip()
                if category in categories:
                    categories[category].append(
                        f"  `/{command.name}` — {desc}"
                    )
            except ValueError:
                continue
    
    @staticmethod
    def generate_help_pages(bot_instance):
        categories = {
            "Information": [],
            "Manager": [],
            "Moderator": [],
            "Miscellaneous": []
        }
        HelpPages.generate_prefix_pages(bot_instance, categories)
        HelpPages.generate_slash_pages(bot_instance, categories)

        pages = []
        for category, cmds in categories.items():
            if not cmds:
                continue
            embed = discord.Embed(
                title=f"{KurumiEmojis["KurumiLove"]} {category} Commands",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=str(bot_instance.user.display_avatar.url))
            embed.description = "\n".join(cmds)
            pages.append(embed)

        return pages


class HelpView(View):
    """
    Interactive paginated view for displaying help pages with previous/next/delete controls.

    Usage:
    - Instantiate with `pages` (list of discord.Embed) and the requesting `author`.
    - The view enforces that only the original author may use the navigation buttons.
    - The Delete button removes the message (owner-only).
    """
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

        # Assign callbacks to button interactions
        self.prev_btn.callback = self.prev_button
        self.next_btn.callback = self.next_button
        self.delete_button.callback = self.handle_delete
        
        self.add_item(self.prev_btn)
        self.add_item(self.page_btn)
        self.add_item(self.next_btn)
        self.add_item(self.delete_button)

        self._update_buttons()

    def _update_buttons(self):
        """Enable/disable navigation buttons and update the page indicator label."""
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == len(self.pages) - 1
        self.page_btn.label = f"{self.current_page + 1}/{len(self.pages)}"

    async def on_timeout(self):
        """Disable all child controls when the view times out and edit the message to apply the change."""
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def prev_button(self, interaction: discord.Interaction):
        """
        Navigate to the previous page.

        Only the original author may operate the controls.
        """
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def next_button(self, interaction: discord.Interaction):
        """
        Navigate to the next page.

        Only the original author may operate the controls.
        """
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't use these buttons.", ephemeral=True)
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        
    async def handle_delete(self, interaction: discord.Interaction):
        """
        Delete the message containing the help view.

        Only the original author may delete the message. The interaction is deferred
        before performing the deletion to provide a responsive UX.
        """
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ You can't delete this message.", ephemeral=True)
        await interaction.response.defer()
        await interaction.message.delete()