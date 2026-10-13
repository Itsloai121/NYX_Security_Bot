from __future__ import annotations

from typing import List, Optional

from database.connection import Database
from database.models import Infraction


class InfractionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def record(
        self,
        guild_id: int,
        user_id: int,
        action: str,
        reason: str,
        moderator_id: Optional[int] = None,
    ) -> int:
        cur = await self.db.execute(
            "INSERT INTO infractions (guild_id, user_id, action, reason, moderator_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, action, reason, moderator_id),
        )
        return int(cur.lastrowid)

    async def recent(self, guild_id: int, limit: int = 10) -> List[Infraction]:
        rows = await self.db.fetchall(
            "SELECT * FROM infractions WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, limit),
        )
        return [Infraction(**dict(row)) for row in rows]

    async def count_for(self, guild_id: int, user_id: int) -> int:
        row = await self.db.fetchone(
            "SELECT COUNT(*) AS n FROM infractions WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        return int(row["n"]) if row else 0