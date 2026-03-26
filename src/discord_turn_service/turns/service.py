import logging
import time
from typing import cast

import discord

from discord_turn_service.discord.runtime import runtime
from discord_turn_service.models.turns import AskKind, AskTurnRequest, AskTurnResult, ChoiceOption
from discord_turn_service.turns.registry import ActiveTurnRegistry

logger = logging.getLogger(__name__)
MULTICHOICE_RETRY_PROMPT = (
    "I couldn't match that reply to one of the options. "
    "Reply with the option number, key, or label."
)


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
            await dm_channel.send(self._render_prompt(request))

            def check(message: discord.Message) -> bool:
                return (
                    message.author.id == request.user_id
                    and message.channel.id == dm_channel.id
                )

            reply = await self._wait_for_reply_or_none(
                request=request,
                check=check,
                started=started,
            )
            if reply is None:
                return self._timed_out_result(
                    request=request,
                    channel_id=dm_channel.id,
                    started=started,
                )

            if request.ask_kind == AskKind.FREEFORM:
                return self._answered_result(
                    request=request,
                    response_text=reply.content,
                    selected_choice_key=None,
                    channel_id=reply.channel.id,
                    started=started,
                )

            selected_choice_key = self._resolve_selected_choice_key(
                ask_kind=request.ask_kind,
                choices=request.choices,
                response_text=reply.content,
            )
            while selected_choice_key is None:
                await dm_channel.send(MULTICHOICE_RETRY_PROMPT)
                reply = await self._wait_for_reply_or_none(
                    request=request,
                    check=check,
                    started=started,
                )
                if reply is None:
                    return self._timed_out_result(
                        request=request,
                        channel_id=dm_channel.id,
                        started=started,
                    )
                selected_choice_key = self._resolve_selected_choice_key(
                    ask_kind=request.ask_kind,
                    choices=request.choices,
                    response_text=reply.content,
                )

            return self._answered_result(
                request=request,
                response_text=reply.content,
                selected_choice_key=selected_choice_key,
                channel_id=reply.channel.id,
                started=started,
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

    @staticmethod
    def _render_prompt(request: AskTurnRequest) -> str:
        if request.ask_kind == AskKind.FREEFORM:
            return request.prompt

        lines = [request.prompt, "", "Reply with the option number, key, or label:"]
        for idx, choice in enumerate(request.choices, start=1):
            lines.append(f"{idx}. {choice.label} ({choice.key})")
        return "\n".join(lines)

    @staticmethod
    def _resolve_selected_choice_key(
        *,
        ask_kind: AskKind,
        choices: list[ChoiceOption],
        response_text: str | None,
    ) -> str | None:
        if ask_kind != AskKind.MULTICHOICE or response_text is None:
            return None

        normalized = response_text.strip().casefold()
        if not normalized:
            return None

        for index, choice in enumerate(choices, start=1):
            if normalized == str(index):
                return choice.key
            if normalized == choice.key.casefold():
                return choice.key
            if normalized == choice.label.casefold():
                return choice.key
        return None

    @staticmethod
    async def _wait_for_reply_or_none(
        *,
        request: AskTurnRequest,
        check: object,
        started: float,
    ) -> discord.Message | None:
        remaining_timeout = request.timeout_seconds - (time.monotonic() - started)
        if remaining_timeout <= 0:
            return None
        try:
            return await runtime.client.wait_for(
                "message",
                check=check,
                timeout=remaining_timeout,
            )
        except TimeoutError:
            return None

    @staticmethod
    def _answered_result(
        *,
        request: AskTurnRequest,
        response_text: str,
        selected_choice_key: str | None,
        channel_id: int,
        started: float,
    ) -> AskTurnResult:
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
            response_text=response_text,
            selected_choice_key=selected_choice_key,
            user_id=request.user_id,
            channel_id=channel_id,
        )

    @staticmethod
    def _timed_out_result(
        *,
        request: AskTurnRequest,
        channel_id: int,
        started: float,
    ) -> AskTurnResult:
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
            channel_id=channel_id,
        )


registry = ActiveTurnRegistry()
turn_service = TurnService(registry=registry)
