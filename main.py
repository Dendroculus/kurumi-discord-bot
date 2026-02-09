import discord
from discord.ext import commands
import time
import aiohttp  
from constants.configs import DISCORD_TOKEN
from utils.loggingConfig import setup_logging

logger = setup_logging()  
start_time = time.time()  
warnings = {}  

intents = discord.Intents.default()  
intents.members = True  
intents.message_content = True  

class KurumiBot(commands.AutoShardedBot):  
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        self.session: aiohttp.ClientSession = None

    async def setup_hook(self):
        print("Running setup_hook...")  
        
        self.session = aiohttp.ClientSession()
        print("✅ HTTP Client Session initialized.")

        extensions = [
            "cogs.automod",  
            "cogs.information",  
            "cogs.moderator",  
            "cogs.miscellaneous",  
            "cogs.manager",  
            "cogs.events",  
            "cogs.errors",  
            "cogs.antiScam",  
        ]
        
        for ext in extensions:  
            try:
                await self.load_extension(ext)  
            except Exception as e:
                print(f"❌ Failed to load extension {ext}: {e}")  

    async def close(self):
        if self.session:
            await self.session.close()
            print("🛑 HTTP Client Session closed.")
        await super().close()

if __name__ == "__main__":  
    bot = KurumiBot()  
    bot.run(DISCORD_TOKEN)  