"""Reusable command checks."""
from __future__ import annotations

from discord.ext import commands

from core.errors import NotAuthorized, NotConfigured
from database.repositories.guild_settings import GuildSettingsRepository


def is_admin():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise NotAuthorized
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        raise NotAuthorized

    return commands.check(predicate)


def guild_configured():
    """Loads (and caches) guild settings; attaches them to ctx.guild_settings."""

    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise NotConfigured
        settings = ctx.bot.cache.get(ctx.guild.id)
        if settings is None:
            repo = GuildSettingsRepository(ctx.bot.db)
            settings = await repo.get_or_create(ctx.guild.id)
            ctx.bot.cache.put(settings)
        ctx.guild_settings = settings
        return True

    return commands.check(predicate)