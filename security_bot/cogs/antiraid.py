"""Anti-raid: join-velocity lockdown + mention-spam blocking."""
from __future__ import annotations

import asyncio
import datetime
from typing import Dict, List, Tuple

import discord
from discord.ext import commands

from database.repositories.guild_settings import GuildSettingsRepository
from utils import checks, embeds


class AntiRaid(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        from services.detection import RateDetector  # local import keeps cog light

        self.detector = RateDetector(cooldown_seconds=30.0)
        self._locked: Dict[int, List[Tuple[int, object]]] = {}
        self._tasks: set = set()

    async def _settings(self, guild: discord.Guild):
        settings = self.bot.cache.get(guild.id)
        if settings is None:
            settings = await GuildSettingsRepository(self.bot.db).get_or_create(guild.id)
            self.bot.cache.put(settings)
        return settings

    async def lockdown(self, guild: discord.Guild, minutes: int) -> None:
        stored: List[Tuple[int, object]] = []
        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            if overwrite.send_messages is False:
                continue
            stored.append((channel.id, overwrite.send_messages))
            overwrite.send_messages = False
            try:
                await channel.set_permissions(
                    guild.default_role, overwrite=overwrite, reason="raid lockdown"
                )
            except discord.HTTPException:
                continue
        self._locked[guild.id] = stored

        modlog = self.bot.get_cog("ModLog")
        if modlog:
            await modlog.send(
                guild,
                embeds.alert_embed(
                    "RAID LOCKDOWN",
                    f"Public posting disabled for @everyone for {minutes} minutes.",
                    {"channels locked": len(stored)},
                ),
            )
        if minutes and minutes > 0:
            task = asyncio.create_task(self._auto_release(guild, minutes))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def release(self, guild: discord.Guild) -> int:
        stored = self._locked.pop(guild.id, [])
        restored = 0
        for channel_id, previous in stored:
            channel = guild.get_channel(channel_id)
            if channel is None:
                continue
            overwrite = channel.overwrites_for(guild.default_role)
            overwrite.send_messages = previous
            try:
                await channel.set_permissions(
                    guild.default_role, overwrite=overwrite, reason="raid lockdown released"
                )
                restored += 1
            except discord.HTTPException:
                continue
        return restored

    async def _auto_release(self, guild: discord.Guild, minutes: int) -> None:
        await asyncio.sleep(minutes * 60)
        await self.release(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await self._settings(member.guild)
        if not settings.antiraid_enabled:
            return
        triggered = self.detector.record(
            member.guild.id, "joins",
            settings.join_threshold, settings.join_window_seconds,
        )
        if not triggered:
            return
        cfg = self.bot.config.get("antiraid", {})
        if cfg.get("action", "lockdown") == "lockdown":
            await self.lockdown(member.guild, int(cfg.get("lockdown_duration_minutes", 10)))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        settings = self.bot.cache.get(message.guild.id)
        if settings is None or not settings.antiraid_enabled:
            return
        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count < settings.mention_threshold:
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        if isinstance(message.author, discord.Member):
            try:
                await message.author.timeout(
                    datetime.timedelta(minutes=10), reason="mention spam"
                )
            except discord.HTTPException:
                pass
        modlog = self.bot.get_cog("ModLog")
        if modlog:
            await modlog.send(
                message.guild,
                embeds.alert_embed(
                    "MENTION SPAM BLOCKED",
                    f"{message.author} mentioned {mention_count} targets in one message.",
                    {"channel": message.channel.mention},
                ),
            )

    @commands.command(name="lockdown")
    @checks.is_admin()
    async def lockdown_cmd(self, ctx, minutes: int = 10):
        await self.lockdown(ctx.guild, minutes)
        await ctx.send(embed=embeds.success_embed(f"Lockdown active for {minutes} minutes."))

    @commands.command(name="release")
    @checks.is_admin()
    async def release_cmd(self, ctx):
        restored = await self.release(ctx.guild)
        await ctx.send(embed=embeds.success_embed(f"Lockdown released on {restored} channels."))


async def setup(bot) -> None:
    await bot.add_cog(AntiRaid(bot))