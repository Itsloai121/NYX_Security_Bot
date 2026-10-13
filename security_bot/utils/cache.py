"""In-memory per-guild settings cache to avoid a DB hit on every event."""
from __future__ import annotations

from typing import Dict, Optional

from database.models import GuildSettings


class ConfigCache:
    def __init__(self) -> None:
        self._guilds: Dict[int, GuildSettings] = {}

    def get(self, guild_id: int) -> Optional[GuildSettings]:
        return self._guilds.get(guild_id)

    def put(self, settings: GuildSettings) -> None:
        self._guilds[settings.guild_id] = settings

    def invalidate(self, guild_id: int) -> None:
        self._guilds.pop(guild_id, None)