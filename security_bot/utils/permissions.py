"""Dangerous-permission helpers and hierarchy checks."""
from __future__ import annotations

from typing import List

import discord

DANGEROUS_PERMISSION_NAMES = (
    "administrator",
    "manage_roles",
    "manage_webhooks",
    "manage_channels",
    "manage_guild",
    "mention_everyone",
)


def dangerous_permissions_of(perms: discord.Permissions) -> List[str]:
    return [name for name in DANGEROUS_PERMISSION_NAMES if getattr(perms, name, False)]


def hierarchy_allows(actor: discord.Member, target: discord.Member) -> bool:
    """True when actor may safely act on target.

    The guild owner can never be acted on by a bot or member.
    """
    if target.id == target.guild.owner_id:
        return False
    return actor.top_role > target.top_role