import asyncio

from discord_turn_service.turns.registry import ActiveTurnRegistry


def test_registry_acquire_and_release() -> None:
    async def _run() -> None:
        registry = ActiveTurnRegistry()

        acquired = await registry.acquire(user_id=123, correlation_id="a1")
        assert acquired is True
        assert await registry.is_active(123) is True

        await registry.release(user_id=123, correlation_id="a1")
        assert await registry.is_active(123) is False

    asyncio.run(_run())


def test_registry_rejects_second_active_turn_for_same_user() -> None:
    async def _run() -> None:
        registry = ActiveTurnRegistry()

        first = await registry.acquire(user_id=123, correlation_id="a1")
        second = await registry.acquire(user_id=123, correlation_id="a2")

        assert first is True
        assert second is False

    asyncio.run(_run())
