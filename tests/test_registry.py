import pytest

from discord_turn_service.turns.registry import ActiveTurnRegistry


@pytest.mark.asyncio
async def test_registry_acquire_and_release() -> None:
    registry = ActiveTurnRegistry()

    acquired = await registry.acquire(user_id=123, correlation_id="a1")
    assert acquired is True
    assert await registry.is_active(123) is True

    await registry.release(user_id=123, correlation_id="a1")
    assert await registry.is_active(123) is False


@pytest.mark.asyncio
async def test_registry_rejects_second_active_turn_for_same_user() -> None:
    registry = ActiveTurnRegistry()

    first = await registry.acquire(user_id=123, correlation_id="a1")
    second = await registry.acquire(user_id=123, correlation_id="a2")

    assert first is True
    assert second is False
