import logging
import time

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

            dm_channel = user.dm_channel or await user.create_dm()
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
                    status="timeout",
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


registry = ActiveTurnRegistry()
turn_service = TurnService(registry=registry)
