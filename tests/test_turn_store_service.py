import pytest

from discord_turn_service.models.turns import AskKind, CreateTurnRequest, TurnDirection, TurnState
from discord_turn_service.turns.state_machine import InvalidTurnTransitionError
from discord_turn_service.turns.store_service import TurnStoreService


def test_apply_transition_persists_state() -> None:
    store_service = TurnStoreService(store={})
    created = store_service.create_turn(
        turn_id="turn-1",
        request=CreateTurnRequest(
            correlation_id="corr-1",
            user_id=42,
            prompt="hello",
            direction=TurnDirection.SYSTEM_TO_USER,
        ),
    )

    transitioned = store_service.apply_transition(created.turn_id or "", TurnState.OPEN)

    assert transitioned.state == TurnState.OPEN
    assert store_service.get_turn("turn-1").state == TurnState.OPEN


def test_invalid_transition_does_not_mutate_store() -> None:
    store_service = TurnStoreService(store={})
    created = store_service.create_turn(
        turn_id="turn-1",
        request=CreateTurnRequest(
            correlation_id="corr-1",
            user_id=42,
            prompt="hello",
            direction=TurnDirection.SYSTEM_TO_USER,
        ),
    )

    with pytest.raises(InvalidTurnTransitionError):
        store_service.apply_transition(created.turn_id or "", TurnState.ANSWERED)

    assert store_service.get_turn("turn-1").state == TurnState.RECEIVED


def test_create_turn_persists_ask_interaction_shape() -> None:
    store_service = TurnStoreService(store={})
    created = store_service.create_turn(
        turn_id="turn-2",
        request=CreateTurnRequest(
            correlation_id="corr-2",
            user_id=42,
            prompt="choose a route",
            direction=TurnDirection.SYSTEM_TO_USER,
            ask_kind=AskKind.MULTICHOICE,
            choices=[
                {"key": "fastest", "label": "Fastest"},
                {"key": "safest", "label": "Safest"},
            ],
        ),
    )

    assert created.ask_kind == AskKind.MULTICHOICE
    assert [choice.key for choice in created.choices] == ["fastest", "safest"]
