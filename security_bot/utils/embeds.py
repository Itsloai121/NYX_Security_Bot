"""Shared embed builders so all cogs log with one format."""
from __future__ import annotations

from typing import Optional

import discord

RED = discord.Color.red()
ORANGE = discord.Color.orange()
GREEN = discord.Color.green()


def _base(title: str, description: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = discord.utils.utcnow()
    return embed


def _add_fields(embed: discord.Embed, fields: Optional[dict]) -> discord.Embed:
    for name, value in (fields or {}).items():
        embed.add_field(name=name, value=str(value)[:1024], inline=False)
    return embed


def alert_embed(title: str, description: str, fields: Optional[dict] = None) -> discord.Embed:
    return _add_fields(_base(title, description, RED), fields)


def log_embed(event: str, description: str, fields: Optional[dict] = None) -> discord.Embed:
    return _add_fields(_base(f"MODLOG | {event}", description, ORANGE), fields)


def success_embed(description: str, fields: Optional[dict] = None) -> discord.Embed:
    return _add_fields(_base("OK", description, GREEN), fields)