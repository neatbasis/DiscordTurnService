"""Reference example: upstream orchestration calling DiscordTurnService.

This example demonstrates the boundary split:
- A higher orchestration layer resolves canonical identity and reachability.
- Ask receives a Discord-ready recipient.
- DiscordTurnService executes the Discord turn using Discord-native fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx


@dataclass(frozen=True)
class DiscordRecipient:
    """Discord-native recipient resolved by an upstream orchestration layer."""

    discord_user_id: int
    discord_channel_id: int | None = None


def route_discord_query_via_turn_service(
    *,
    base_url: str,
    correlation_id: str,
    recipient: DiscordRecipient,
    prompt: str,
    ask_kind: Literal["freeform", "multichoice"] = "freeform",
    choices: list[dict[str, str]] | None = None,
    timeout_seconds: float = 60.0,
) -> dict:
    """Execute a Discord turn against an already-resolved Discord recipient."""

    request = {
        "correlation_id": correlation_id,
        "user_id": recipient.discord_user_id,
        "channel_id": recipient.discord_channel_id,
        "prompt": prompt,
        "timeout_seconds": timeout_seconds,
        "mode": "dm",
        "direction": "system_to_user",
        "ask_kind": ask_kind,
    }
    if choices is not None:
        request["choices"] = choices

    response = httpx.post(f"{base_url}/ask-turn", json=request, timeout=timeout_seconds + 10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # In the real system, this recipient would be resolved upstream by
    # orchestration before Ask calls DiscordTurnService.
    recipient = DiscordRecipient(
        discord_user_id=123456789012345678,
        discord_channel_id=None,
    )

    freeform_result = route_discord_query_via_turn_service(
        base_url="http://localhost:8000",
        correlation_id="ask-001",
        recipient=recipient,
        prompt="Mission Control requests your current status.",
    )
    print(freeform_result)

    multichoice_result = route_discord_query_via_turn_service(
        base_url="http://localhost:8000",
        correlation_id="ask-002",
        recipient=recipient,
        prompt="Choose route preference.",
        ask_kind="multichoice",
        choices=[
            {"key": "fastest", "label": "Fastest"},
            {"key": "safest", "label": "Safest"},
            {"key": "quietest", "label": "Quietest"},
        ],
    )
    print(multichoice_result)
