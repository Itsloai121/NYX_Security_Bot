"""Plain dataclasses mapped to SQLite rows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GuildSettings:
    guild_id: int
    prefix: str = "!"
    log_channel_id: Optional[int] = None
    antinuke_enabled: bool = True
    antiraid_enabled: bool = True
    punishment: str = "ban"
    join_threshold: int = 10
    join_window_seconds: int = 10
    mention_threshold: int = 15


@dataclass
class WhitelistEntry:
    guild_id: int
    entry_type: str  # "user" | "role"
    target_id: int


@dataclass
class Infraction:
    id: Optional[int]
    guild_id: int
    user_id: int
    action: str
    reason: str
    moderator_id: Optional[int]
    created_at: str


@dataclass
class BackupSnapshot:
    id: Optional[int]
    guild_id: int
    created_at: str
    data: str  # JSON payload