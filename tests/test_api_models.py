from pydantic import ValidationError

from discord_turn_service.models.turns import AskKind, AskTurnRequest


def test_ask_turn_request_valid() -> None:
    req = AskTurnRequest(
        correlation_id="ask-001",
        user_id=123,
        prompt="Hello?",
        timeout_seconds=60,
        mode="dm",
    )
    assert req.correlation_id == "ask-001"
    assert req.user_id == 123
    assert req.mode == "dm"


def test_ask_turn_request_rejects_non_positive_timeout() -> None:
    try:
        AskTurnRequest(
            correlation_id="ask-001",
            user_id=123,
            prompt="Hello?",
            timeout_seconds=0,
            mode="dm",
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for timeout_seconds=0")


def test_ask_turn_request_allows_discord_channel_hint() -> None:
    req = AskTurnRequest(
        correlation_id="ask-002",
        user_id=123,
        channel_id=456,
        prompt="Hello?",
        timeout_seconds=60,
        mode="dm",
    )
    assert req.channel_id == 456


def test_ask_turn_request_rejects_person_id_field() -> None:
    try:
        AskTurnRequest(
            correlation_id="ask-003",
            user_id=123,
            prompt="Hello?",
            timeout_seconds=60,
            mode="dm",
            person_id="person.sebastian",
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for person_id")


def test_ask_turn_request_multichoice_requires_choices() -> None:
    try:
        AskTurnRequest(
            correlation_id="ask-004",
            user_id=123,
            prompt="Pick one",
            timeout_seconds=60,
            mode="dm",
            ask_kind=AskKind.MULTICHOICE,
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for multichoice without choices")


def test_ask_turn_request_freeform_rejects_choices() -> None:
    try:
        AskTurnRequest(
            correlation_id="ask-005",
            user_id=123,
            prompt="Tell me your status",
            timeout_seconds=60,
            mode="dm",
            ask_kind=AskKind.FREEFORM,
            choices=[{"key": "fastest", "label": "Fastest"}],
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for freeform request with choices")


def test_ask_turn_request_multichoice_accepts_choices() -> None:
    req = AskTurnRequest(
        correlation_id="ask-006",
        user_id=123,
        prompt="Pick one",
        timeout_seconds=60,
        mode="dm",
        ask_kind=AskKind.MULTICHOICE,
        choices=[{"key": "fastest", "label": "Fastest"}],
    )
    assert req.ask_kind == AskKind.MULTICHOICE
    assert len(req.choices) == 1


def test_ask_turn_request_rejects_direction_field() -> None:
    try:
        AskTurnRequest(
            correlation_id="ask-007",
            user_id=123,
            prompt="Hello?",
            timeout_seconds=60,
            mode="dm",
            direction="system_to_user",
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for direction field on ask-turn")
