from __future__ import annotations

from typing import List, Sequence

from database.connection import Database
from database.models import WhitelistEntry


class WhitelistRepository:
    """Users/roles exempt from anti-nuke punishment."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def add(self, guild_id: int, entry_type: str, target_id: int) -> None:
        await self.db.execute(
            "INSERT OR IGNORE INTO whitelist (guild_id, entry_type, target_id) VALUES (?, ?, ?)",
            (guild_id, entry_type, target_id),
        )

    async def remove(self, guild_id: int, entry_type: str, target_id: int) -> None:
        await self.db.execute(
            "DELETE FROM whitelist WHERE guild_id = ? AND entry_type = ? AND target_id = ?",
            (guild_id, entry_type, target_id),
        )

    async def list(self, guild_id: int) -> List[WhitelistEntry]:
        rows = await self.db.fetchall(
            "SELECT guild_id, entry_type, target_id FROM whitelist WHERE guild_id = ?",
            (guild_id,),
        )
        return [WhitelistEntry(**dict(row)) for row in rows]

    async def is_whitelisted(
        self, guild_id: int, user_id: int, role_ids: Sequence[int]
    ) -> bool:
        rows = await self.db.fetchall(
            "SELECT entry_type, target_id FROM whitelist WHERE guild_id = ?",
            (guild_id,),
        )
        for row in rows:
            if row["entry_type"] == "user" and row["target_id"] == user_id:
                return True
            if row["entry_type"] == "role" and row["target_id"] in role_ids:
                return True
        return False