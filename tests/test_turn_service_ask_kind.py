from discord_turn_service.models.turns import AskKind, AskTurnRequest
from discord_turn_service.turns.service import TurnService


def test_render_prompt_for_multichoice_includes_choices() -> None:
    request = AskTurnRequest(
        correlation_id="ask-101",
        user_id=1,
        prompt="Choose route",
        ask_kind=AskKind.MULTICHOICE,
        choices=[
            {"key": "fastest", "label": "Fastest"},
            {"key": "safest", "label": "Safest"},
        ],
    )

    rendered = TurnService._render_prompt(request)

    assert "Choose route" in rendered
    assert "1. Fastest (fastest)" in rendered
    assert "2. Safest (safest)" in rendered


def test_resolve_selected_choice_key_for_multichoice_variants() -> None:
    request = AskTurnRequest(
        correlation_id="ask-102",
        user_id=1,
        prompt="Choose route",
        ask_kind=AskKind.MULTICHOICE,
        choices=[
            {"key": "fastest", "label": "Fastest"},
            {"key": "safest", "label": "Safest"},
        ],
    )

    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="1",
        )
        == "fastest"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="safest",
        )
        == "safest"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="Fastest",
        )
        == "fastest"
    )


def test_resolve_selected_choice_key_for_freeform_returns_none() -> None:
    request = AskTurnRequest(
        correlation_id="ask-103",
        user_id=1,
        prompt="Status?",
        ask_kind=AskKind.FREEFORM,
    )

    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="available",
        )
        is None
    )
