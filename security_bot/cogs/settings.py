"""Per-guild configuration commands."""
from __future__ import annotations

import discord
from discord.ext import commands

from database.repositories.guild_settings import GuildSettingsRepository
from utils import checks, embeds

VALID_PUNISHMENTS = ("strip", "kick", "ban")


class Settings(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def _save(self, ctx, **changes):
        settings = await GuildSettingsRepository(self.bot.db).update(ctx.guild.id, **changes)
        self.bot.cache.put(settings)
        return settings

    @commands.command(name="setup")
    @checks.is_admin()
    @checks.guild_configured()
    async def setup(self, ctx, log_channel: discord.TextChannel):
        await self._save(ctx, log_channel_id=log_channel.id)
        await ctx.send(embed=embeds.success_embed(f"Modlog channel set to {log_channel.mention}."))

    @commands.command(name="punishment")
    @checks.is_admin()
    @checks.guild_configured()
    async def punishment(self, ctx, mode: str):
        mode = mode.lower()
        if mode not in VALID_PUNISHMENTS:
            await ctx.reply(f"Valid modes: {', '.join(VALID_PUNISHMENTS)}")
            return
        await self._save(ctx, punishment=mode)
        await ctx.send(embed=embeds.success_embed(f"Anti-nuke punishment set to `{mode}`."))

    @commands.command(name="antiraid")
    @checks.is_admin()
    @checks.guild_configured()
    async def antiraid(self, ctx, state: str):
        enabled = state.lower() in ("on", "true", "enable", "enabled")
        await self._save(ctx, antiraid_enabled=enabled)
        await ctx.send(embed=embeds.success_embed(f"Anti-raid {'enabled' if enabled else 'disabled'}."))

    @commands.command(name="joins")
    @checks.is_admin()
    @checks.guild_configured()
    async def joins(self, ctx, threshold: int, window_seconds: int = 10):
        await self._save(ctx, join_threshold=threshold, join_window_seconds=window_seconds)
        await ctx.send(embed=embeds.success_embed(
            f"Raid trigger: {threshold} joins in {window_seconds}s."))

    @commands.command(name="mentions")
    @checks.is_admin()
    @checks.guild_configured()
    async def mentions(self, ctx, threshold: int):
        await self._save(ctx, mention_threshold=threshold)
        await ctx.send(embed=embeds.success_embed(f"Mention-spam threshold set to {threshold}."))

    @commands.command(name="showsettings")
    @checks.is_admin()
    @checks.guild_configured()
    async def showsettings(self, ctx):
        s = ctx.guild_settings
        await ctx.send(embed=embeds.success_embed(
            "Current settings.",
            {
                "log channel": f"<#{s.log_channel_id}>" if s.log_channel_id else "not set",
                "antinuke": s.antinuke_enabled,
                "antiraid": s.antiraid_enabled,
                "punishment": s.punishment,
                "join trigger": f"{s.join_threshold} joins / {s.join_window_seconds}s",
                "mention threshold": s.mention_threshold,
            },
        ))


async def setup(bot) -> None:
    await bot.add_cog(Settings(bot))