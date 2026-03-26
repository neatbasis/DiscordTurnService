import pytest

from discord_turn_service.models.turns import Turn, TurnDirection, TurnState
from discord_turn_service.turns.state_machine import InvalidTurnTransitionError, transition_turn


def _turn(state: TurnState) -> Turn:
    return Turn(
        turn_id="turn-1",
        correlation_id="corr-1",
        user_id=1,
        direction=TurnDirection.SYSTEM_TO_USER,
        state=state,
        prompt="hello",
        timeout_seconds=30,
    )


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (TurnState.RECEIVED, TurnState.OPEN),
        (TurnState.RECEIVED, TurnState.PROCESSED),
        (TurnState.RECEIVED, TurnState.ERROR),
        (TurnState.OPEN, TurnState.ANSWERED),
        (TurnState.OPEN, TurnState.TIMED_OUT),
        (TurnState.OPEN, TurnState.CANCELED),
        (TurnState.OPEN, TurnState.ERROR),
        (TurnState.ANSWERED, TurnState.PROCESSED),
    ],
)
def test_allowed_transitions(from_state: TurnState, to_state: TurnState) -> None:
    transitioned = transition_turn(_turn(from_state), to_state)
    assert transitioned.state == to_state


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (TurnState.ANSWERED, TurnState.OPEN),
        (TurnState.PROCESSED, TurnState.OPEN),
        (TurnState.TIMED_OUT, TurnState.OPEN),
        (TurnState.CANCELED, TurnState.ANSWERED),
        (TurnState.ERROR, TurnState.OPEN),
    ],
)
def test_forbidden_transitions(from_state: TurnState, to_state: TurnState) -> None:
    with pytest.raises(InvalidTurnTransitionError):
        transition_turn(_turn(from_state), to_state)
