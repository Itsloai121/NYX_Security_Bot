"""Custom Bot class: intents, setup_hook, cog loader, shared state."""
from __future__ import annotations

import logging
import os
from typing import Any

import discord
from discord.ext import commands

from database.connection import Database
from utils.cache import ConfigCache

log = logging.getLogger(__name__)

EXTENSIONS = (
    "core.errors",
    "cogs.antinuke",
    "cogs.antiraid",
    "cogs.moderation",
    "cogs.modlog",
    "cogs.settings",
)


class SecurityBot(commands.Bot):
    """Holds config, database and cache so every cog shares one instance."""

    def __init__(self, config: dict[str, Any]) -> None:
        intents = discord.Intents.default()
        intents.members = True           # join/leave velocity for antiraid
        intents.message_content = True   # mention/phishing scanning
        if hasattr(intents, "moderation"):       # discord.py >= 2.4
            intents.moderation = True    # ban events for antinuke
        elif hasattr(intents, "bans"):           # discord.py 2.2-2.3
            intents.bans = True

        owner_env = os.getenv("OWNER_ID", "")
        owner_id = int(owner_env) if owner_env.isdigit() else None

        super().__init__(
            command_prefix=config.get("default_prefix", "!"),
            intents=intents,
            owner_id=owner_id,
            help_command=None,
        )
        self.config = config
        self.db = Database(os.getenv("DATABASE_PATH", "data/security_bot.db"))
        self.cache = ConfigCache()

    async def setup_hook(self) -> None:
        await self.db.setup()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        log.info("setup_hook complete: %d extensions loaded", len(EXTENSIONS))

    async def on_ready(self) -> None:
        log.info("connected as %s", self.user)

    async def close(self) -> None:
        await self.db.close()
        await super().close()