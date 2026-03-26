"""Turn state transition validation.

This module is the single authority for canonical turn lifecycle transitions.
All write paths that change turn state must go through this module, directly
or via a service that wraps it.

The transition model is intentionally monotonic and operational.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping

from discord_turn_service.models.turns import Turn, TurnState


ALLOWED_TRANSITIONS: Final[Mapping[TurnState, frozenset[TurnState]]] = {
    TurnState.RECEIVED: frozenset(
        {TurnState.OPEN, TurnState.PROCESSED, TurnState.ERROR}
    ),
    TurnState.OPEN: frozenset(
        {
            TurnState.ANSWERED,
            TurnState.TIMED_OUT,
            TurnState.CANCELED,
            TurnState.ERROR,
        }
    ),
    TurnState.ANSWERED: frozenset({TurnState.PROCESSED}),
    TurnState.TIMED_OUT: frozenset(),
    TurnState.CANCELED: frozenset(),
    TurnState.PROCESSED: frozenset(),
    TurnState.ERROR: frozenset(),
}


@dataclass(slots=True)
class InvalidTurnTransitionError(Exception):
    """Raised when a requested turn state transition is not allowed."""

    turn_id: str
    from_state: TurnState
    to_state: TurnState

    def __str__(self) -> str:
        return (
            f"Invalid transition for turn {self.turn_id!r}: "
            f"{self.from_state.value!r} -> {self.to_state.value!r}"
        )


def is_transition_allowed(from_state: TurnState, to_state: TurnState) -> bool:
    """Return True if the requested transition is allowed."""
    return to_state in ALLOWED_TRANSITIONS[from_state]


def validate_transition(*, turn_id: str, from_state: TurnState, to_state: TurnState) -> None:
    """Validate a transition or raise InvalidTurnTransitionError."""
    if not is_transition_allowed(from_state=from_state, to_state=to_state):
        raise InvalidTurnTransitionError(
            turn_id=turn_id,
            from_state=from_state,
            to_state=to_state,
        )


def transition_turn(turn: Turn, to_state: TurnState, **updates: object) -> Turn:
    """Return a new turn with a validated lifecycle transition applied.

    All canonical turn state changes must go through this function.
    """
    validate_transition(
        turn_id=turn.turn_id or "<unknown>",
        from_state=turn.state,
        to_state=to_state,
    )
    return turn.model_copy(update={"state": to_state, **updates})
