"""Reference example: Ask-style orchestration calling DiscordTurnService.

This example demonstrates the boundary split:
- Ask maintains canonical person identity and reachability bindings.
- Ask resolves person -> channel binding -> Discord recipient identity.
- DiscordTurnService executes the Discord turn using Discord-native fields.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class PersonRecord:
    person_ref: str
    display_name: str
    person_type: str


@dataclass(frozen=True)
class ReachabilityBinding:
    person_ref: str
    channel_ref: str
    discord_user_id: int
    discord_channel_id: int | None = None


PERSONS: dict[str, PersonRecord] = {
    "person.bond": PersonRecord(
        person_ref="person.bond",
        display_name="Bond",
        person_type="agent",
    ),
    "person.moneypenny": PersonRecord(
        person_ref="person.moneypenny",
        display_name="Moneypenny",
        person_type="coordinator",
    ),
}


REACHABILITY: dict[str, ReachabilityBinding] = {
    "person.bond": ReachabilityBinding(
        person_ref="person.bond",
        channel_ref="channel.discord.primary",
        discord_user_id=123456789012345678,
        discord_channel_id=None,
    ),
}


def route_person_via_discord_turn_service(
    *,
    base_url: str,
    correlation_id: str,
    person_ref: str,
    prompt: str,
    timeout_seconds: float = 60.0,
) -> dict:
    """Resolve canonical person reachability in Ask, then execute Discord turn."""
    person = PERSONS[person_ref]
    binding = REACHABILITY[person.person_ref]

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
    result = route_person_via_discord_turn_service(
        base_url="http://localhost:8000",
        correlation_id="ask-001",
        person_ref="person.bond",
        prompt="Mission Control requests your current status.",
    )
    print(result)
