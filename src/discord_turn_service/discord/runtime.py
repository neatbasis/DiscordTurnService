import asyncio
import logging
from typing import Optional

import discord

from discord_turn_service.config import settings

logger = logging.getLogger(__name__)


class DiscordRuntime:
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.messages = True
        intents.dm_messages = True
        intents.guild_messages = False
        intents.message_content = True

        self.client = discord.Client(intents=intents)
        self.ready_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

        @self.client.event
        async def on_ready() -> None:
            logger.info("Discord client ready as %s", self.client.user)
            self.ready_event.set()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self.client.start(settings.discord_token))
        logger.info("Discord client startup task created")

    async def wait_until_ready(self, timeout: float = 30.0) -> bool:
        try:
            await asyncio.wait_for(self.ready_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def is_ready(self) -> bool:
        return self.ready_event.is_set() and not self.client.is_closed()

    async def stop(self) -> None:
        if not self.client.is_closed():
            await self.client.close()
        if self._task is not None:
            try:
                await self._task
            except Exception:
                logger.exception("Discord client task ended with error")
            finally:
                self._task = None


runtime = DiscordRuntime()
