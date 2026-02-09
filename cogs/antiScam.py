import os
import re
import time
import logging
import aiohttp
import discord
from collections import OrderedDict
from typing import List, Set, Tuple, Optional
from discord.ext import commands
from constants.configs import CACHE_MAX_SIZE, CACHE_TTL_SECONDS, SAFE_BROWSING_URL, MAX_WARNINGS
from utils.moderationUtils import enforce_punishments

class SafeBrowsingClient:
    """
    Handles interactions with the Google Safe Browsing API.
    
    Attributes:
        api_key (str): The Google API key derived from environment variables.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
        if not self.api_key:
            logging.getLogger("bot").warning("GOOGLE_SAFE_BROWSING_API_KEY not found in environment.")

    async def check_urls(self, urls: List[str], session: aiohttp.ClientSession) -> Set[str]:
        """
        Queries the API to determine if any of the provided URLs are malicious.

        Args:
            urls: A list of URL strings to check.
            session: The shared aiohttp ClientSession to use for the request.

        Returns:
            A set of URLs identified as threats.
        """
        if not urls or not self.api_key:
            return set()

        payload = {
            "client": {"clientId": "kurumi-bot", "clientVersion": "1.0.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls]
            }
        }

        params = {'key': self.api_key}

        try:
            async with session.post(SAFE_BROWSING_URL, json=payload, params=params) as resp:
                if resp.status != 200:
                    logging.getLogger("bot").error(f"Safe Browsing API returned {resp.status}")
                    return set()
                
                data = await resp.json()
                matches = data.get('matches', [])
                return {match['threat']['url'] for match in matches}

        except Exception as e:
            logging.getLogger("bot").error(f"Failed to check URLs: {e}")
            return set()


class AntiScam(commands.Cog):
    """
    Moderation Cog for detecting and removing phishing or malicious links.

    Implements an LRU (Least Recently Used) cache to minimize API latency and quota usage.
    """

    def __init__(self, bot: commands.Bot, scanner: Optional[SafeBrowsingClient] = None):
        self.bot = bot
        self.logger = logging.getLogger("bot")
        # Dependency Injection: Use provided scanner or instantiate a default one
        self.scanner = scanner or SafeBrowsingClient()
        
        self.cache: OrderedDict[str, Tuple[bool, float]] = OrderedDict()
        
        self.url_pattern = re.compile(
            r'https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?'
        )

    def _check_cache(self, url: str) -> Optional[bool]:
        """ Checks the cache for the URL's safety status. """
        if url not in self.cache:
            return None

        is_safe, timestamp = self.cache[url]
        
        if time.time() - timestamp > CACHE_TTL_SECONDS:
            del self.cache[url]
            return None

        self.cache.move_to_end(url)
        return is_safe

    def _update_cache(self, urls: List[str], bad_urls: Set[str]):
        """ Updates the cache with the results from the API scan. """
        now = time.time()
        for url in urls:
            is_bad = url in bad_urls
            self.cache[url] = (not is_bad, now)
            self.cache.move_to_end(url)

        while len(self.cache) > CACHE_MAX_SIZE:
            self.cache.popitem(last=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        found_urls = self.url_pattern.findall(message.content)
        if not found_urls:
            return

        urls_to_scan = []
        confirmed_threats = set()

        for url in found_urls:
            cached_status = self._check_cache(url)
            if cached_status is False:
                confirmed_threats.add(url)
            elif cached_status is None:
                urls_to_scan.append(url)

        # Use self.bot.session instead of a local session
        if urls_to_scan and hasattr(self.bot, 'session') and self.bot.session:
            api_threats = await self.scanner.check_urls(urls_to_scan, self.bot.session)
            confirmed_threats.update(api_threats)
            self._update_cache(urls_to_scan, api_threats)

        if confirmed_threats:
            await self._punish(message, confirmed_threats)

    async def _punish(self, message: discord.Message, threats: Set[str]):
        """
        Executes moderation actions:
        1. Deletes the scam link.
        2. Adds a warning to the user's record (synced with AutoMod).
        3. Enforces punishments (Mute/Kick/Ban) if warning threshold is reached.
        """
        try:
            await message.delete()
        except discord.NotFound:
            self.logger.debug(f"Failed to delete message {message.id} - it was already deleted.")
        except discord.Forbidden:
            self.logger.error(f"Failed to delete message {message.id} - Missing 'Manage Messages' permission.")

        self.logger.warning(
            f"SCAM DETECTED: User {message.author.id} in Guild {message.guild.id}. Links: {threats}"
        )

        automod = self.bot.get_cog("AutoMod")
        if automod:
            count = await automod.on_message_warn(message.author.id, message.guild.id)
            
            embed = discord.Embed(
                title="🛡️ Security Alert",
                description=(
                    f"{message.author.mention}, malicious link detected!\n"
                    f"Warning `{count}`/{MAX_WARNINGS}."
                ),
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed, delete_after=10)

            await enforce_punishments(
                member=message.author,
                count=count,
                channel=message.channel,
                logger=self.logger
            )
        else:
            self.logger.error("AutoMod cog not found! Cannot enforce punishments.")
            await message.channel.send(f"🛡️ {message.author.mention}, link removed.", delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiScam(bot))
    logging.getLogger("bot").info("Loaded AntiScam cog.")