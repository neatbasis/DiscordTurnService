"""Canonical turn persistence service.

This service centralizes canonical turn writes so route handlers and adapters
do not mutate lifecycle state directly. It applies validated transitions
through the state machine before persistence.
"""

from __future__ import annotations

from discord_turn_service.models.turns import CreateTurnRequest, Turn, TurnState
from discord_turn_service.turns.state_machine import transition_turn


class TurnNotFoundError(KeyError):
    pass


class TurnStoreService:
    """Manage canonical turn records with monotonic lifecycle transitions."""

    def __init__(self, store: dict[str, Turn]) -> None:
        self._store = store

    def create_turn(self, *, turn_id: str, request: CreateTurnRequest) -> Turn:
        turn = Turn(
            turn_id=turn_id,
            correlation_id=request.correlation_id,
            user_id=request.user_id,
            channel_id=request.channel_id,
            direction=request.direction,
            state=TurnState.RECEIVED,
            prompt=request.prompt,
            ask_kind=request.ask_kind,
            choices=request.choices,
            timeout_seconds=request.timeout_seconds,
        )
        self._store[turn_id] = turn
        return turn

    def get_turn(self, turn_id: str) -> Turn:
        turn = self._store.get(turn_id)
        if turn is None:
            raise TurnNotFoundError(turn_id)
        return turn

    def apply_transition(self, turn_id: str, to_state: TurnState, **updates: object) -> Turn:
        turn = self.get_turn(turn_id)
        updated = transition_turn(turn=turn, to_state=to_state, **updates)
        self._store[turn_id] = updated
        return updated
