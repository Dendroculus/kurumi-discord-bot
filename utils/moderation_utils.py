from __future__ import annotations

from datetime import timedelta
from typing import Optional
import logging
import discord
from utils import config


def _is_currently_timed_out(member: discord.Member) -> bool:
    until = getattr(member, "timed_out_until", None)
    if not until:
        return False
    from discord.utils import utcnow
    return until > utcnow()


async def enforce_punishments(
    member: discord.Member,
    count: int,
    channel: Optional[discord.abc.Messageable] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    logger = logger or logging.getLogger("bot")

    try:
        if count >= config.BAN_AT_WARNINGS:
            await member.guild.ban(member, reason=f"Too many warnings ({config.BAN_AT_WARNINGS})")
            if channel:
                await channel.send(f"⛔ {member.mention} has been banned for reaching {config.BAN_AT_WARNINGS} warnings.")
            return "ban"

        if count == config.KICK_AT_WARNINGS:
            await member.guild.kick(member, reason=f"Too many warnings ({config.KICK_AT_WARNINGS})")
            if channel:
                await channel.send(f"👢 {member.mention} has been kicked for reaching {config.KICK_AT_WARNINGS} warnings.")
            return "kick"

        if count >= config.TIMEOUT_AT_WARNINGS and not _is_currently_timed_out(member):
            until = discord.utils.utcnow() + timedelta(seconds=config.TIMEOUT_SECONDS_ON_THRESHOLD)
            await member.edit(timed_out_until=until, reason="Auto timeout due to warnings")
            if channel:
                await channel.send(
                    f"🔇 {member.mention} has been temporarily muted "
                    f"({config.TIMEOUT_SECONDS_ON_THRESHOLD}s) due to repeated warnings."
                )
            return "timeout"

    except discord.Forbidden:
        if channel:
            await channel.send("❌ I lack permissions to enforce the punishment.")
        logger.warning("Permission error while enforcing punishments for %s", member)
    except Exception as e:
        logger.exception("Failed to enforce punishments for %s: %s", member, e)

    return "none"