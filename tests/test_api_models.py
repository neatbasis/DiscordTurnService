from pydantic import ValidationError

from discord_turn_service.models.turns import AskTurnRequest


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
