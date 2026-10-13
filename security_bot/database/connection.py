"""SQLite connection wrapper. All repositories share one Database instance."""
from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id            INTEGER PRIMARY KEY,
    prefix              TEXT    NOT NULL DEFAULT '!',
    log_channel_id      INTEGER,
    antinuke_enabled    INTEGER NOT NULL DEFAULT 1,
    antiraid_enabled    INTEGER NOT NULL DEFAULT 1,
    punishment          TEXT    NOT NULL DEFAULT 'ban',
    join_threshold      INTEGER NOT NULL DEFAULT 10,
    join_window_seconds INTEGER NOT NULL DEFAULT 10,
    mention_threshold   INTEGER NOT NULL DEFAULT 15
);

CREATE TABLE IF NOT EXISTS whitelist (
    guild_id   INTEGER NOT NULL,
    entry_type TEXT    NOT NULL,
    target_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, entry_type, target_id)
);

CREATE TABLE IF NOT EXISTS infractions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    action       TEXT    NOT NULL,
    reason       TEXT    NOT NULL,
    moderator_id INTEGER,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    data       TEXT    NOT NULL
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def setup(self) -> None:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not initialised; call setup() first")
        return self._conn

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def fetchone(self, sql: str, params: tuple = ()):
        cur = await self.conn.execute(sql, params)
        return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()):
        cur = await self.conn.execute(sql, params)
        return await cur.fetchall()