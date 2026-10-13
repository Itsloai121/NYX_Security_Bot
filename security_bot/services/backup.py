"""Channel/role snapshot + restore (Xenon-style structural backup).

Scope note: this restores structure only (categories, channels, roles,
permission overwrites). Member recovery is intentionally out of scope -
that is RestoreCord's job. Discord has no native full-server backup, so
snapshots must be created BEFORE an incident.

Restore creates the saved structure alongside whatever currently exists;
run it on an empty or freshly recreated server after a nuke.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

import discord

log = logging.getLogger(__name__)

TEXT_TYPES = {"text", "news"}


class BackupService:
    def __init__(self, bot, max_snapshots: int = 5) -> None:
        self.bot = bot
        self.max_snapshots = max_snapshots

    async def snapshot(self, guild: discord.Guild) -> int:
        roles = []
        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            if role.is_default():
                continue
            roles.append(
                {
                    "name": role.name,
                    "color": role.color.value,
                    "permissions": role.permissions.value,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "position": role.position,
                }
            )

        channels = []
        for channel in guild.channels:
            overwrites = []
            for target, overwrite in channel.overwrites.items():
                allow, deny = overwrite.pair()
                if isinstance(target, discord.Role):
                    overwrites.append(
                        {"type": "role", "name": target.name,
                         "allow": allow.value, "deny": deny.value}
                    )
                else:
                    overwrites.append(
                        {"type": "member", "id": target.id,
                         "allow": allow.value, "deny": deny.value}
                    )
            channels.append(
                {
                    "type": str(channel.type),
                    "name": channel.name,
                    "position": channel.position,
                    "category": channel.category.name if getattr(channel, "category", None) else None,
                    "topic": getattr(channel, "topic", None),
                    "slowmode": getattr(channel, "slowmode_delay", 0),
                    "overwrites": overwrites,
                }
            )

        payload = json.dumps({"roles": roles, "channels": channels})
        cur = await self.bot.db.execute(
            "INSERT INTO backups (guild_id, data) VALUES (?, ?)", (guild.id, payload)
        )
        await self._prune(guild.id)
        return int(cur.lastrowid)

    async def list_snapshots(self, guild: discord.Guild) -> List[dict]:
        rows = await self.bot.db.fetchall(
            "SELECT id, created_at FROM backups WHERE guild_id = ? ORDER BY id DESC",
            (guild.id,),
        )
        return [dict(row) for row in rows]

    async def restore(self, guild: discord.Guild, snapshot_id: int) -> Dict[str, int]:
        row = await self.bot.db.fetchone(
            "SELECT data FROM backups WHERE id = ? AND guild_id = ?",
            (snapshot_id, guild.id),
        )
        if row is None:
            raise ValueError(f"snapshot {snapshot_id} not found for this guild")
        data = json.loads(row["data"])

        created_roles: Dict[str, discord.Role] = {}
        for role_data in sorted(data["roles"], key=lambda r: r["position"], reverse=True):
            role = await guild.create_role(
                name=role_data["name"],
                permissions=discord.Permissions(role_data["permissions"]),
                color=discord.Color(role_data["color"]),
                hoist=role_data["hoist"],
                mentionable=role_data["mentionable"],
                reason="backup restore",
            )
            created_roles[role.name] = role

        categories: Dict[str, discord.CategoryChannel] = {}
        for channel in sorted(
            (c for c in data["channels"] if c["type"] == "category"),
            key=lambda c: c["position"],
        ):
            categories[channel["name"]] = await guild.create_category(
                channel["name"], reason="backup restore"
            )

        restored_channels = 0
        for channel in sorted(
            (c for c in data["channels"] if c["type"] != "category"),
            key=lambda c: c["position"],
        ):
            overwrites: Dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}
            for ow in channel["overwrites"]:
                if ow["type"] == "role":
                    role = created_roles.get(ow["name"])
                    if role is None and ow["name"] == "@everyone":
                        role = guild.default_role
                    if role is not None:
                        overwrites[role] = discord.PermissionOverwrite.from_pair(
                            discord.Permissions(ow["allow"]),
                            discord.Permissions(ow["deny"]),
                        )
            category = categories.get(channel["category"]) if channel["category"] else None
            kwargs = {"category": category, "reason": "backup restore"}
            if overwrites:
                kwargs["overwrites"] = overwrites
            channel_type = channel["type"]
            if channel_type in TEXT_TYPES:
                kwargs["topic"] = channel.get("topic")
                kwargs["slowmode_delay"] = channel.get("slowmode") or 0
                await guild.create_text_channel(channel["name"], **kwargs)
            elif channel_type == "voice":
                await guild.create_voice_channel(channel["name"], **kwargs)
            elif channel_type == "stage_voice":
                await guild.create_stage_channel(channel["name"], **kwargs)
            elif channel_type == "forum":
                await guild.create_forum(channel["name"], **kwargs)
            else:
                await guild.create_text_channel(channel["name"], **kwargs)
            restored_channels += 1

        return {"roles": len(created_roles), "channels": restored_channels}

    async def _prune(self, guild_id: int) -> None:
        await self.bot.db.execute(
            "DELETE FROM backups WHERE guild_id = ? AND id NOT IN "
            "(SELECT id FROM backups WHERE guild_id = ? ORDER BY id DESC LIMIT ?)",
            (guild_id, guild_id, self.max_snapshots),
        )