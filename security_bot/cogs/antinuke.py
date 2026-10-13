"""Anti-nuke: sliding-window detection of destructive actions + punishment."""
from __future__ import annotations

from typing import Union

import discord
from discord.ext import commands

from database.repositories.guild_settings import GuildSettingsRepository
from database.repositories.infractions import InfractionRepository
from database.repositories.whitelist import WhitelistRepository
from services.detection import RateDetector
from services.punishment import PunishmentService
from utils import checks, embeds
from utils.permissions import hierarchy_allows


class AntiNuke(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.detector = RateDetector(cooldown_seconds=30.0)
        self.punisher = PunishmentService(bot)
        self.whitelist = WhitelistRepository(bot.db)
        self.infractions = InfractionRepository(bot.db)

    async def _settings(self, guild: discord.Guild):
        settings = self.bot.cache.get(guild.id)
        if settings is None:
            settings = await GuildSettingsRepository(self.bot.db).get_or_create(guild.id)
            self.bot.cache.put(settings)
        return settings

    async def _actor(self, guild, action):
        try:
            entries = await guild.audit_logs(limit=1, action=action).flatten()
        except discord.HTTPException:
            return None
        return entries[0].user if entries else None

    async def _handle(self, guild, metric: str, actor, description: str) -> None:
        settings = await self._settings(guild)
        if not settings.antinuke_enabled or actor is None:
            return
        if actor.bot or actor.id == self.bot.user.id:
            return

        modlog = self.bot.get_cog("ModLog")

        if actor.id == guild.owner_id:
            # Owner cannot be punished; alert only.
            if modlog:
                await modlog.send(
                    guild,
                    embeds.alert_embed(
                        "ANTI-NUKE | OWNER ACTION",
                        description,
                        {"metric": metric, "note": "owner actions are alert-only"},
                    ),
                )
            return

        member = guild.get_member(actor.id)
        role_ids = [r.id for r in member.roles] if member else []
        if await self.whitelist.is_whitelisted(guild.id, actor.id, role_ids):
            return

        cfg = self.bot.config.get("antinuke", {}).get(
            metric, {"threshold": 2, "window_seconds": 10}
        )
        triggered = self.detector.record(
            guild.id, metric, cfg["threshold"], cfg["window_seconds"]
        )
        if not triggered:
            return

        applied = None
        if member is not None and hierarchy_allows(guild.me, member):
            applied = await self.punisher.apply_safe(
                member, settings.punishment, f"anti-nuke: {metric} threshold exceeded"
            )
        await self.infractions.record(
            guild.id, actor.id, applied or "alert",
            f"anti-nuke {metric}: {description}", self.bot.user.id,
        )
        if modlog:
            await modlog.send(
                guild,
                embeds.alert_embed(
                    "ANTI-NUKE TRIGGERED",
                    description,
                    {
                        "metric": metric,
                        "actor": f"{actor} ({actor.id})",
                        "action": applied or "alert only (hierarchy/whitelist)",
                    },
                ),
            )

    # ---- listeners ----

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        actor = await self._actor(channel.guild, discord.AuditLogAction.channel_delete)
        await self._handle(channel.guild, "channel_delete", actor, f"channel #{channel.name} deleted")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        actor = await self._actor(channel.guild, discord.AuditLogAction.channel_create)
        await self._handle(channel.guild, "channel_create", actor, f"channel #{channel.name} created")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        actor = await self._actor(role.guild, discord.AuditLogAction.role_delete)
        await self._handle(role.guild, "role_delete", actor, f"role {role.name} deleted")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions == after.permissions:
            return
        actor = await self._actor(after.guild, discord.AuditLogAction.role_update)
        await self._handle(after.guild, "role_update", actor, f"role {after.name} permissions changed")

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        actor = await self._actor(guild, discord.AuditLogAction.webhook_create)
        if actor is None:
            actor = await self._actor(guild, discord.AuditLogAction.webhook_delete)
        await self._handle(guild, "webhook_create", actor, f"webhook changed in #{channel.name}")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user):
        actor = await self._actor(guild, discord.AuditLogAction.ban)
        await self._handle(guild, "ban", actor, f"{user} banned")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        actor = await self._actor(member.guild, discord.AuditLogAction.kick)
        if actor is None:
            return
        await self._handle(member.guild, "kick", actor, f"{member} kicked")

    # ---- commands ----

    @commands.group(name="antinuke", invoke_without_command=True)
    @checks.is_admin()
    @checks.guild_configured()
    async def antinuke(self, ctx: commands.Context):
        await ctx.send(embed=embeds.success_embed(
            "Usage: `antinuke enable|disable|status|whitelist add|whitelist remove`."))

    @antinuke.command(name="enable")
    @checks.is_admin()
    @checks.guild_configured()
    async def antinuke_enable(self, ctx):
        settings = await GuildSettingsRepository(self.bot.db).update(
            ctx.guild.id, antinuke_enabled=True)
        self.bot.cache.put(settings)
        await ctx.send(embed=embeds.success_embed("Anti-nuke enabled."))

    @antinuke.command(name="disable")
    @checks.is_admin()
    @checks.guild_configured()
    async def antinuke_disable(self, ctx):
        settings = await GuildSettingsRepository(self.bot.db).update(
            ctx.guild.id, antinuke_enabled=False)
        self.bot.cache.put(settings)
        await ctx.send(embed=embeds.success_embed("Anti-nuke disabled."))

    @antinuke.command(name="status")
    @checks.is_admin()
    @checks.guild_configured()
    async def antinuke_status(self, ctx):
        entries = await self.whitelist.list(ctx.guild.id)
        await ctx.send(embed=embeds.success_embed(
            "Anti-nuke status.",
            {
                "enabled": ctx.guild_settings.antinuke_enabled,
                "punishment": ctx.guild_settings.punishment,
                "whitelist entries": len(entries),
            },
        ))

    @antinuke.group(name="whitelist", invoke_without_command=True)
    @checks.is_admin()
    @checks.guild_configured()
    async def whitelist(self, ctx):
        entries = await self.whitelist.list(ctx.guild.id)
        lines = [f"{e.entry_type}: {e.target_id}" for e in entries] or ["<empty>"]
        await ctx.send(embed=embeds.success_embed("Whitelist.", {"entries": "\n".join(lines)}))

    @whitelist.command(name="add")
    @checks.is_admin()
    @checks.guild_configured()
    async def whitelist_add(self, ctx, target: Union[discord.Member, discord.Role]):
        entry_type = "user" if isinstance(target, discord.Member) else "role"
        await self.whitelist.add(ctx.guild.id, entry_type, target.id)
        await ctx.send(embed=embeds.success_embed(f"Whitelisted {target.name} ({entry_type})."))

    @whitelist.command(name="remove")
    @checks.is_admin()
    @checks.guild_configured()
    async def whitelist_remove(self, ctx, target: Union[discord.Member, discord.Role]):
        entry_type = "user" if isinstance(target, discord.Member) else "role"
        await self.whitelist.remove(ctx.guild.id, entry_type, target.id)
        await ctx.send(embed=embeds.success_embed(f"Removed {target.name} from whitelist."))


async def setup(bot) -> None:
    await bot.add_cog(AntiNuke(bot))