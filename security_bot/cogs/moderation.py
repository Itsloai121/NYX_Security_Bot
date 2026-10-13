"""Manual moderation commands + backup create/list/restore."""
from __future__ import annotations

import datetime

import discord
from discord.ext import commands

from database.repositories.infractions import InfractionRepository
from services.backup import BackupService
from utils import checks, embeds
from utils.permissions import hierarchy_allows


class Moderation(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.infractions = InfractionRepository(bot.db)
        self.backups = BackupService(bot, max_snapshots=bot.config.get("backup", {}).get("max_snapshots", 5))

    async def _modlog(self, guild, embed):
        modlog = self.bot.get_cog("ModLog")
        if modlog:
            await modlog.send(guild, embed)

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 50):
        deleted = await ctx.channel.purge(limit=min(max(amount, 1), 500))
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "no reason"):
        if not hierarchy_allows(ctx.author, member) or not hierarchy_allows(ctx.guild.me, member):
            await ctx.reply("Role hierarchy blocks this action.")
            return
        await member.ban(reason=reason)
        await self.infractions.record(ctx.guild.id, member.id, "ban", reason, ctx.author.id)
        await self._modlog(ctx.guild, embeds.log_embed("MANUAL BAN", f"{member} banned by {ctx.author}.", {"reason": reason}))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "no reason"):
        if not hierarchy_allows(ctx.author, member) or not hierarchy_allows(ctx.guild.me, member):
            await ctx.reply("Role hierarchy blocks this action.")
            return
        await member.kick(reason=reason)
        await self.infractions.record(ctx.guild.id, member.id, "kick", reason, ctx.author.id)
        await self._modlog(ctx.guild, embeds.log_embed("MANUAL KICK", f"{member} kicked by {ctx.author}.", {"reason": reason}))

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "no reason"):
        if not hierarchy_allows(ctx.author, member) or not hierarchy_allows(ctx.guild.me, member):
            await ctx.reply("Role hierarchy blocks this action.")
            return
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await self.infractions.record(ctx.guild.id, member.id, "timeout", reason, ctx.author.id)
        await self._modlog(ctx.guild, embeds.log_embed("TIMEOUT", f"{member} timed out {minutes}m by {ctx.author}.", {"reason": reason}))

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="manual lock")
        await ctx.send(embed=embeds.success_embed(f"{channel.mention} locked."))

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="manual unlock")
        await ctx.send(embed=embeds.success_embed(f"{channel.mention} unlocked."))

    @commands.group(name="backup", invoke_without_command=True)
    @checks.is_admin()
    async def backup(self, ctx):
        await ctx.send(embed=embeds.success_embed("Usage: `backup create|list|restore <id>`."))

    @backup.command(name="create")
    @checks.is_admin()
    async def backup_create(self, ctx):
        snapshot_id = await self.backups.snapshot(ctx.guild)
        await ctx.send(embed=embeds.success_embed(f"Snapshot #{snapshot_id} created."))

    @backup.command(name="list")
    @checks.is_admin()
    async def backup_list(self, ctx):
        rows = await self.backups.list_snapshots(ctx.guild)
        lines = [f"#{r['id']} @ {r['created_at']}" for r in rows] or ["<no snapshots>"]
        await ctx.send(embed=embeds.success_embed("Snapshots.", {"entries": "\n".join(lines)}))

    @backup.command(name="restore")
    @checks.is_admin()
    async def backup_restore(self, ctx, snapshot_id: int):
        try:
            result = await self.backups.restore(ctx.guild, snapshot_id)
        except ValueError:
            await ctx.reply("Snapshot not found for this server.")
            return
        await ctx.send(embed=embeds.success_embed(
            "Restore complete.",
            {"roles created": result["roles"], "channels created": result["channels"]},
        ))
        await self._modlog(ctx.guild, embeds.log_embed(
            "BACKUP RESTORE", f"Snapshot #{snapshot_id} restored by {ctx.author}."))


async def setup(bot) -> None:
    await bot.add_cog(Moderation(bot))