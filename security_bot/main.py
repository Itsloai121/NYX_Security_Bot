"""Entry point: load env, config, and start the bot."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from core.bot import SecurityBot

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger("main")


def load_config() -> dict:
    path = Path(__file__).parent / "config.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


async def run() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token or token.startswith("paste-"):
        raise SystemExit("Set DISCORD_TOKEN in .env before starting.")

    bot = SecurityBot(config=load_config())
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(run())