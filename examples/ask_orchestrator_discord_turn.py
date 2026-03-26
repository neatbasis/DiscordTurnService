"""Reference example: Ask-style orchestration calling DiscordTurnService.

This example demonstrates the boundary split:
- Ask/orchestrator resolves person -> Discord recipient identity.
- DiscordTurnService executes the Discord turn using Discord-native fields.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ReachabilityBinding:
    person_ref: str
    channel_ref: str
    discord_user_id: int
    discord_channel_id: int | None = None


REACHABILITY: dict[str, ReachabilityBinding] = {
    "person.sebastian": ReachabilityBinding(
        person_ref="person.sebastian",
        channel_ref="channel.discord.primary",
        discord_user_id=123456789012345678,
        discord_channel_id=None,
    ),
}


def ask_person_via_discord_turn_service(
    *,
    base_url: str,
    correlation_id: str,
    person_ref: str,
    prompt: str,
    timeout_seconds: float = 60.0,
) -> dict:
    """Resolve person reachability in Ask layer, then execute Discord turn."""
    binding = REACHABILITY[person_ref]

    request = {
        "correlation_id": correlation_id,
        "user_id": binding.discord_user_id,
        "channel_id": binding.discord_channel_id,
        "prompt": prompt,
        "timeout_seconds": timeout_seconds,
        "mode": "dm",
        "direction": "system_to_user",
    }

    response = httpx.post(f"{base_url}/ask-turn", json=request, timeout=timeout_seconds + 10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    result = ask_person_via_discord_turn_service(
        base_url="http://localhost:8000",
        correlation_id="ask-001",
        person_ref="person.sebastian",
        prompt="Could you share your current status?",
    )
    print(result)
