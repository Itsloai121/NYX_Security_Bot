from __future__ import annotations

from typing import Optional

from database.connection import Database
from database.models import GuildSettings

FIELDS = {
    "prefix",
    "log_channel_id",
    "antinuke_enabled",
    "antiraid_enabled",
    "punishment",
    "join_threshold",
    "join_window_seconds",
    "mention_threshold",
}


def _row_to_settings(row) -> GuildSettings:
    return GuildSettings(
        guild_id=row["guild_id"],
        prefix=row["prefix"],
        log_channel_id=row["log_channel_id"],
        antinuke_enabled=bool(row["antinuke_enabled"]),
        antiraid_enabled=bool(row["antiraid_enabled"]),
        punishment=row["punishment"],
        join_threshold=row["join_threshold"],
        join_window_seconds=row["join_window_seconds"],
        mention_threshold=row["mention_threshold"],
    )


class GuildSettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, guild_id: int) -> Optional[GuildSettings]:
        row = await self.db.fetchone(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )
        return _row_to_settings(row) if row else None

    async def get_or_create(self, guild_id: int) -> GuildSettings:
        existing = await self.get(guild_id)
        if existing:
            return existing
        await self.db.execute(
            "INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        return await self.get(guild_id)

    async def update(self, guild_id: int, **changes) -> GuildSettings:
        changes = {k: v for k, v in changes.items() if k in FIELDS}
        if changes:
            sql = (
                "UPDATE guild_settings SET "
                + ", ".join(f"{k} = ?" for k in changes)
                + " WHERE guild_id = ?"
            )
            await self.db.execute(sql, tuple(changes.values()) + (guild_id,))
        return await self.get_or_create(guild_id)