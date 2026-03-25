from pydantic import ValidationError

from discord_turn_service.api.models import AskTurnRequest


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
