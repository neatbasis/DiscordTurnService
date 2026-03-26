import logging
import time
from typing import cast

import discord

from discord_turn_service.discord.runtime import runtime
from discord_turn_service.models.turns import AskTurnRequest, AskTurnResult
from discord_turn_service.turns.registry import ActiveTurnRegistry

logger = logging.getLogger(__name__)


class DiscordNotReadyError(RuntimeError):
    pass


class ActiveTurnExistsError(RuntimeError):
    pass


class UnsupportedModeError(RuntimeError):
    pass


class TurnService:
    def __init__(self, registry: ActiveTurnRegistry) -> None:
        self.registry = registry

    async def ask_turn(self, request: AskTurnRequest) -> AskTurnResult:
        started = time.monotonic()

        if request.mode != "dm":
            raise UnsupportedModeError(f"Unsupported mode: {request.mode}")

        if not runtime.is_ready():
            raise DiscordNotReadyError("Discord runtime is not ready")

        acquired = await self.registry.acquire(
            user_id=request.user_id,
            correlation_id=request.correlation_id,
        )
        if not acquired:
            raise ActiveTurnExistsError("active ask-turn already exists for user")

        try:
            user = await runtime.client.fetch_user(request.user_id)
            if user is None:
                return AskTurnResult(
                    correlation_id=request.correlation_id,
                    status="error",
                    user_id=request.user_id,
                    error="Discord user not found",
                )

            dm_channel = await self._resolve_dm_channel(request=request, user=user)
            await dm_channel.send(request.prompt)

            def check(message: discord.Message) -> bool:
                return (
                    message.author.id == request.user_id
                    and message.channel.id == dm_channel.id
                )

            try:
                reply = await runtime.client.wait_for(
                    "message",
                    check=check,
                    timeout=request.timeout_seconds,
                )
                duration = time.monotonic() - started
                logger.info(
                    "ask_turn answered correlation_id=%s user_id=%s duration=%.3f",
                    request.correlation_id,
                    request.user_id,
                    duration,
                )
                return AskTurnResult(
                    correlation_id=request.correlation_id,
                    status="answered",
                    response_text=reply.content,
                    user_id=request.user_id,
                    channel_id=reply.channel.id,
                )
            except TimeoutError:
                duration = time.monotonic() - started
                logger.info(
                    "ask_turn timeout correlation_id=%s user_id=%s duration=%.3f",
                    request.correlation_id,
                    request.user_id,
                    duration,
                )
                return AskTurnResult(
                    correlation_id=request.correlation_id,
                    status="timed_out",
                    user_id=request.user_id,
                    channel_id=dm_channel.id,
                )

        except Exception as exc:
            logger.exception(
                "ask_turn error correlation_id=%s user_id=%s",
                request.correlation_id,
                request.user_id,
            )
            return AskTurnResult(
                correlation_id=request.correlation_id,
                status="error",
                user_id=request.user_id,
                error=str(exc),
            )
        finally:
            await self.registry.release(
                user_id=request.user_id,
                correlation_id=request.correlation_id,
            )

    async def _resolve_dm_channel(
        self,
        request: AskTurnRequest,
        user: discord.User,
    ) -> discord.DMChannel:
        """Resolve the DM channel used for a turn.

        If a caller already knows a Discord DM channel for this user, it may
        provide `channel_id`; otherwise we create (or reuse) the user's DM.
        """
        if request.channel_id is None:
            return user.dm_channel or await user.create_dm()

        channel = runtime.client.get_channel(request.channel_id)
        if channel is None:
            channel = await runtime.client.fetch_channel(request.channel_id)

        if not isinstance(channel, discord.DMChannel):
            raise ValueError(
                f"channel_id={request.channel_id} is not a Discord DM channel"
            )

        recipient = channel.recipient
        if recipient is None or recipient.id != request.user_id:
            raise ValueError(
                "channel_id does not belong to user_id for DM ask-turn"
            )

        return cast(discord.DMChannel, channel)


registry = ActiveTurnRegistry()
turn_service = TurnService(registry=registry)
