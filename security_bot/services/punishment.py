"""Strip roles / kick / ban logic used by anti-nuke."""
from __future__ import annotations

import logging

import discord

from core.errors import PunishmentFailed

log = logging.getLogger(__name__)

VALID_MODES = ("strip", "kick", "ban")


class PunishmentService:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def apply(self, member: discord.Member, mode: str, reason: str) -> str:
        mode = (mode or "ban").lower()
        if mode not in VALID_MODES:
            raise PunishmentFailed(f"unknown punishment mode: {mode}")
        try:
            if mode == "strip":
                await member.edit(roles=[], reason=reason)
            elif mode == "kick":
                await member.kick(reason=reason)
            else:
                await member.ban(reason=reason)
        except discord.Forbidden as exc:
            raise PunishmentFailed(
                f"missing hierarchy/permissions to {mode} {member}"
            ) from exc
        except discord.HTTPException as exc:
            raise PunishmentFailed(f"discord error during {mode}: {exc}") from exc
        return mode

    async def apply_safe(self, member: discord.Member, mode: str, reason: str):
        """Returns the applied mode, or None when the punishment failed."""
        try:
            return await self.apply(member, mode, reason)
        except PunishmentFailed as exc:
            log.warning("punishment failed for %s: %s", member, exc)
            return None