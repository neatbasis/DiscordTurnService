import asyncio


class ActiveTurnRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._active_by_user: dict[int, str] = {}

    async def acquire(self, user_id: int, correlation_id: str) -> bool:
        async with self._lock:
            if user_id in self._active_by_user:
                return False
            self._active_by_user[user_id] = correlation_id
            return True

    async def release(self, user_id: int, correlation_id: str) -> None:
        async with self._lock:
            existing = self._active_by_user.get(user_id)
            if existing == correlation_id:
                self._active_by_user.pop(user_id, None)

    async def is_active(self, user_id: int) -> bool:
        async with self._lock:
            return user_id in self._active_by_user
