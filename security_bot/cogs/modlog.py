"""Staff-only logging. Discord's audit log is limited; this gives better forensics."""
from __future__ import annotations

import discord
from discord.ext import commands

from utils import embeds
from utils.permissions import dangerous_permissions_of


class ModLog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def channel(self, guild: discord.Guild):
        settings = self.bot.cache.get(guild.id)
        if settings is None or not settings.log_channel_id:
            return None
        channel = guild.get_channel(settings.log_channel_id)
        if channel is None:
            return None
        perms = channel.permissions_for(guild.me)
        return channel if perms.send_messages and perms.embed_links else None

    async def send(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel = await self.channel(guild)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def _audit_actor(self, guild, action):
        try:
            entries = await guild.audit_logs(limit=1, action=action).flatten()
        except discord.HTTPException:
            return None
        return entries[0].user if entries else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        await self.send(
            message.guild,
            embeds.log_embed(
                "MESSAGE DELETE",
                f"Message by {message.author} deleted in {message.channel.mention}.",
                {"content": (message.content or "<no text>")[:500]},
            ),
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        await self.send(
            before.guild,
            embeds.log_embed(
                "MESSAGE EDIT",
                f"Message by {before.author} edited in {before.channel.mention}.",
                {"before": (before.content or "")[:400], "after": (after.content or "")[:400]},
            ),
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send(
            member.guild,
            embeds.log_embed("MEMBER JOIN", f"{member} ({member.id}) joined."),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        actor = await self._audit_actor(member.guild, discord.AuditLogAction.kick)
        event = "MEMBER KICK" if actor else "MEMBER LEAVE"
        fields = {"actor": str(actor)} if actor else None
        await self.send(
            member.guild,
            embeds.log_embed(event, f"{member} ({member.id}) left the server.", fields),
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user):
        actor = await self._audit_actor(guild, discord.AuditLogAction.ban)
        await self.send(
            guild,
            embeds.log_embed("MEMBER BAN", f"{user} ({user.id}) was banned.",
                             {"actor": str(actor)} if actor else None),
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user):
        await self.send(guild, embeds.log_embed("MEMBER UNBAN", f"{user} ({user.id}) was unbanned."))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        actor = await self._audit_actor(channel.guild, discord.AuditLogAction.channel_delete)
        await self.send(
            channel.guild,
            embeds.log_embed("CHANNEL DELETE", f"#{channel.name} deleted.",
                             {"actor": str(actor)} if actor else None),
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        actor = await self._audit_actor(channel.guild, discord.AuditLogAction.channel_create)
        await self.send(
            channel.guild,
            embeds.log_embed("CHANNEL CREATE", f"#{channel.name} created.",
                             {"actor": str(actor)} if actor else None),
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        actor = await self._audit_actor(role.guild, discord.AuditLogAction.role_delete)
        await self.send(
            role.guild,
            embeds.log_embed("ROLE DELETE", f"Role {role.name} deleted.",
                             {"actor": str(actor)} if actor else None),
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions == after.permissions:
            return
        added = dangerous_permissions_of(after.permissions)
        actor = await self._audit_actor(after.guild, discord.AuditLogAction.role_update)
        await self.send(
            after.guild,
            embeds.log_embed(
                "ROLE PERMISSION CHANGE",
                f"Role {after.name} permissions changed.",
                {"actor": str(actor) if actor else "unknown",
                 "dangerous_now": ", ".join(added) or "none"},
            ),
        )

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        actor = await self._audit_actor(guild, discord.AuditLogAction.webhook_create)
        action = "webhook created"
        if actor is None:
            actor = await self._audit_actor(guild, discord.AuditLogAction.webhook_delete)
            action = "webhook deleted"
        await self.send(
            guild,
            embeds.log_embed("WEBHOOK CHANGE", f"A webhook was {action} in {channel.mention}.",
                             {"actor": str(actor)} if actor else None),
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_roles = {r.id for r in before.roles}
        after_roles = {r.id for r in after.roles}
        if before_roles == after_roles:
            return
        added = [r.name for r in after.roles if r.id not in before_roles]
        removed = [r.name for r in before.roles if r.id not in after_roles]
        await self.send(
            after.guild,
            embeds.log_embed(
                "MEMBER ROLES CHANGE",
                f"{after} roles updated.",
                {"added": ", ".join(added) or "none", "removed": ", ".join(removed) or "none"},
            ),
        )


async def setup(bot) -> None:
    await bot.add_cog(ModLog(bot))