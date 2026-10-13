import pytest

from conftest import FakeBot, FakeMember
from database.repositories.infractions import InfractionRepository
from database.repositories.whitelist import WhitelistRepository
from services.punishment import PunishmentService


@pytest.mark.asyncio
async def test_strip_removes_all_roles():
    member = FakeMember(roles=["Mod", "Staff"])
    service = PunishmentService(FakeBot(db=None))
    applied = await service.apply_safe(member, "strip", "test")
    assert applied == "strip"
    assert member.actions[0][0] == "strip"
    assert member.roles == []


@pytest.mark.asyncio
async def test_kick_mode():
    member = FakeMember()
    service = PunishmentService(FakeBot(db=None))
    applied = await service.apply_safe(member, "kick", "test")
    assert applied == "kick"
    assert member.actions[0][0] == "kick"


@pytest.mark.asyncio
async def test_ban_mode():
    member = FakeMember()
    service = PunishmentService(FakeBot(db=None))
    applied = await service.apply_safe(member, "ban", "test")
    assert applied == "ban"
    assert member.actions[0][0] == "ban"


@pytest.mark.asyncio
async def test_unknown_mode_returns_none():
    member = FakeMember()
    service = PunishmentService(FakeBot(db=None))
    assert await service.apply_safe(member, "explode", "test") is None
    assert member.actions == []


@pytest.mark.asyncio
async def test_whitelist_roundtrip(db):
    repo = WhitelistRepository(db)
    await repo.add(1, "user", 42)
    assert await repo.is_whitelisted(1, 42, [9]) is True
    assert await repo.is_whitelisted(1, 7, [9]) is False
    await repo.add(1, "role", 9)
    assert await repo.is_whitelisted(1, 7, [9]) is True
    await repo.remove(1, "role", 9)
    assert await repo.is_whitelisted(1, 7, [9]) is False


@pytest.mark.asyncio
async def test_infraction_record_and_recent(db):
    repo = InfractionRepository(db)
    infraction_id = await repo.record(1, 42, "ban", "anti-nuke channel_delete", 7)
    assert infraction_id >= 1
    recent = await repo.recent(1)
    assert recent[0].user_id == 42
    assert recent[0].action == "ban"
    assert await repo.count_for(1, 42) == 1