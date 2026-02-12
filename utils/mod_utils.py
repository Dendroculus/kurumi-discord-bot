"""
This module provides utility functions for enforcing automatic punishments
based on the number of warnings a Discord member has received.
"""
from __future__ import annotations
from datetime import timedelta
from typing import Optional, Dict, Any
import logging
import discord
from constants.configs import (
    BAN_AT_WARNINGS, 
    KICK_AT_WARNINGS, 
    TIMEOUT_AT_WARNINGS, 
    TIMEOUT_SECONDS_ON_THRESHOLD
)

def _is_currently_timed_out(member: discord.Member) -> bool:
    """Check if the member is currently timed out."""
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
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Enforce punishments based on warning count and configuration.

    Args:
        member: The Discord member to punish.
        count: The current warning count.
        channel: Optional channel to send notification messages to.
        logger: Optional logger instance.
        config: Optional dictionary to override default punishment thresholds.
                Keys: 'ban_threshold', 'kick_threshold', 'timeout_threshold', 'timeout_duration'.

    Returns:
        str: The type of punishment enforced ("ban", "kick", "timeout", or "none").
    """
    logger = logger or logging.getLogger("bot")
    
    cfg = config or {}
    ban_threshold = cfg.get("ban_threshold", BAN_AT_WARNINGS)
    kick_threshold = cfg.get("kick_threshold", KICK_AT_WARNINGS)
    timeout_threshold = cfg.get("timeout_threshold", TIMEOUT_AT_WARNINGS)
    timeout_duration = cfg.get("timeout_duration", TIMEOUT_SECONDS_ON_THRESHOLD)

    try:
        if count >= ban_threshold:
            await member.guild.ban(member, reason=f"Too many warnings ({ban_threshold})")
            if channel:
                await channel.send(f"⛔ {member.mention} has been banned for reaching {ban_threshold} warnings.")
            return "ban"

        if count == kick_threshold:
            await member.guild.kick(member, reason=f"Too many warnings ({kick_threshold})")
            if channel:
                await channel.send(f"👢 {member.mention} has been kicked for reaching {kick_threshold} warnings.")
            return "kick"

        if count >= timeout_threshold and not _is_currently_timed_out(member):
            until = discord.utils.utcnow() + timedelta(seconds=timeout_duration)
            await member.edit(timed_out_until=until, reason="Auto timeout due to warnings")
            if channel:
                await channel.send(
                    f"🔇 {member.mention} has been temporarily muted "
                    f"({timeout_duration}s) due to repeated warnings."
                )
            return "timeout"

    except discord.Forbidden:
        if channel:
            await channel.send("❌ I lack permissions to enforce the punishment.")
        logger.warning("Permission error while enforcing punishments for %s", member)
    except Exception as e:
        logger.exception("Failed to enforce punishments for %s: %s", member, e)

    return "none"