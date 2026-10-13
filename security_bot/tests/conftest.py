import pathlib
import sys

import pytest_asyncio

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from database.connection import Database  # noqa: E402


class FakeMember:
    """Minimal stand-in for discord.Member used by punishment tests."""

    def __init__(self, member_id: int = 1, roles=("Mod",)) -> None:
        self.id = member_id
        self.roles = list(roles)
        self.actions = []

    async def edit(self, *, roles=None, reason=None):
        self.actions.append(("strip", roles, reason))
        self.roles = []

    async def kick(self, *, reason=None):
        self.actions.append(("kick", reason))

    async def ban(self, *, reason=None, **kwargs):
        self.actions.append(("ban", reason))


class FakeBot:
    def __init__(self, db) -> None:
        self.db = db


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.setup()
    yield database
    await database.close()