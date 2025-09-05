import discord
from discord.ext import commands
import time
import os
from dotenv import load_dotenv

start_time = time.time()
warnings = {}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


def get_command_description(help_text):
    if help_text and ":" in help_text:
        return help_text.split(":", 1)[1].strip()
    return help_text or "No description available."

class KurumiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)

    async def setup_hook(self):
        print("Running setup_hook...")
        extensions = [
            "cogs.automod",
            "cogs.information",
            "cogs.moderator",
            "cogs.miscellaneous",
            "cogs.manager",
            "cogs.events",
            "cogs.errors"
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)  
            except Exception as e:
                print(f"❌ Failed to load extension {ext}: {e}")
    
if __name__ == '__main__':
    bot = KurumiBot()
    
    
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

