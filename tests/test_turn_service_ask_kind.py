from types import SimpleNamespace

import pytest

from discord_turn_service.models.turns import AskTurnRequest
from discord_turn_service.turns.registry import ActiveTurnRegistry
from discord_turn_service.turns.service import MULTICHOICE_RETRY_PROMPT, TurnService
from interaction_contracts import AskKind


class _FakeDMChannel:
    def __init__(self, channel_id: int) -> None:
        self.id = channel_id
        self.sent_messages: list[str] = []

    async def send(self, text: str) -> None:
        self.sent_messages.append(text)


class _FakeUser:
    def __init__(self, user_id: int, dm_channel: _FakeDMChannel) -> None:
        self.id = user_id
        self.dm_channel = dm_channel

    async def create_dm(self) -> _FakeDMChannel:
        return self.dm_channel


class _FakeMessage:
    def __init__(self, *, user_id: int, channel_id: int, content: str) -> None:
        self.author = SimpleNamespace(id=user_id)
        self.channel = SimpleNamespace(id=channel_id)
        self.content = content


class _FakeDiscordClient:
    def __init__(self, *, user_id: int, dm_channel: _FakeDMChannel, replies: list[str]) -> None:
        self._user_id = user_id
        self._dm_channel = dm_channel
        self._replies = list(replies)
        self.wait_for_timeouts: list[float] = []

    async def fetch_user(self, user_id: int) -> _FakeUser | None:
        if user_id != self._user_id:
            return None
        return _FakeUser(user_id=user_id, dm_channel=self._dm_channel)

    async def wait_for(self, _event: str, *, check, timeout: float):
        self.wait_for_timeouts.append(timeout)
        if not self._replies:
            raise TimeoutError
        content = self._replies.pop(0)
        message = _FakeMessage(
            user_id=self._user_id,
            channel_id=self._dm_channel.id,
            content=content,
        )
        assert check(message)
        return message


@pytest.fixture
def service() -> TurnService:
    return TurnService(registry=ActiveTurnRegistry())


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
            {
                "key": "accept-mission",
                "label": "Accept Mission",
                "aliases": ["accept", "yes", "go ahead"],
            },
            {
                "key": "decline-mission",
                "label": "Decline Mission",
                "aliases": ["decline", "no"],
            },
        ],
    )

    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="1",
        )
        == "accept-mission"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="decline-mission",
        )
        == "decline-mission"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="Accept Mission",
        )
        == "accept-mission"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="yes",
        )
        == "accept-mission"
    )
    assert (
        TurnService._resolve_selected_choice_key(
            ask_kind=request.ask_kind,
            choices=request.choices,
            response_text="GO AHEAD",
        )
        == "accept-mission"
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


@pytest.mark.asyncio
async def test_multichoice_reprompts_until_valid_reply(monkeypatch, service: TurnService) -> None:
    dm_channel = _FakeDMChannel(channel_id=9001)
    fake_client = _FakeDiscordClient(user_id=7, dm_channel=dm_channel, replies=["nope", "2"])
    fake_runtime = SimpleNamespace(is_ready=lambda: True, client=fake_client)
    monkeypatch.setattr("discord_turn_service.turns.service.runtime", fake_runtime)

    result = await service.ask_turn(
        AskTurnRequest(
            correlation_id="corr-1",
            user_id=7,
            prompt="Pick one",
            timeout_seconds=30,
            ask_kind=AskKind.MULTICHOICE,
            choices=[
                {"key": "accept-mission", "label": "Accept Mission"},
                {"key": "decline-mission", "label": "Decline Mission"},
            ],
        )
    )

    assert result.status == "answered"
    assert result.response_text == "2"
    assert result.selected_choice_key == "decline-mission"
    assert dm_channel.sent_messages[0].startswith("Pick one")
    assert MULTICHOICE_RETRY_PROMPT in dm_channel.sent_messages


@pytest.mark.asyncio
async def test_multichoice_invalid_replies_timeout_without_false_answer(
    monkeypatch,
    service: TurnService,
) -> None:
    dm_channel = _FakeDMChannel(channel_id=9002)
    fake_client = _FakeDiscordClient(
        user_id=8,
        dm_channel=dm_channel,
        replies=["???", "still wrong"],
    )
    fake_runtime = SimpleNamespace(is_ready=lambda: True, client=fake_client)
    monkeypatch.setattr("discord_turn_service.turns.service.runtime", fake_runtime)

    result = await service.ask_turn(
        AskTurnRequest(
            correlation_id="corr-2",
            user_id=8,
            prompt="Pick one",
            timeout_seconds=30,
            ask_kind=AskKind.MULTICHOICE,
            choices=[{"key": "accept", "label": "Accept"}],
        )
    )

    assert result.status == "timed_out"
    assert result.response_text is None
    assert result.selected_choice_key is None
    assert dm_channel.sent_messages.count(MULTICHOICE_RETRY_PROMPT) == 2


@pytest.mark.asyncio
async def test_multichoice_retries_use_remaining_timeout_budget(
    monkeypatch,
    service: TurnService,
) -> None:
    dm_channel = _FakeDMChannel(channel_id=9003)
    fake_client = _FakeDiscordClient(user_id=9, dm_channel=dm_channel, replies=["bad", "1"])
    fake_runtime = SimpleNamespace(is_ready=lambda: True, client=fake_client)
    monotonic_values = iter([0.0, 0.2, 0.6, 0.8, 1.2])

    def fake_monotonic() -> float:
        return next(monotonic_values, 1.2)

    monkeypatch.setattr("discord_turn_service.turns.service.runtime", fake_runtime)
    monkeypatch.setattr("discord_turn_service.turns.service.time.monotonic", fake_monotonic)

    result = await service.ask_turn(
        AskTurnRequest(
            correlation_id="corr-3",
            user_id=9,
            prompt="Pick one",
            timeout_seconds=1.0,
            ask_kind=AskKind.MULTICHOICE,
            choices=[{"key": "accept", "label": "Accept"}],
        )
    )

    assert result.status == "answered"
    assert result.selected_choice_key == "accept"
    assert fake_client.wait_for_timeouts == [0.8, 0.4]


@pytest.mark.asyncio
async def test_freeform_uses_first_reply(monkeypatch, service: TurnService) -> None:
    dm_channel = _FakeDMChannel(channel_id=9004)
    fake_client = _FakeDiscordClient(user_id=10, dm_channel=dm_channel, replies=["hello there"])
    fake_runtime = SimpleNamespace(is_ready=lambda: True, client=fake_client)
    monkeypatch.setattr("discord_turn_service.turns.service.runtime", fake_runtime)

    result = await service.ask_turn(
        AskTurnRequest(
            correlation_id="corr-4",
            user_id=10,
            prompt="Status?",
            timeout_seconds=30,
            ask_kind=AskKind.FREEFORM,
        )
    )

    assert result.status == "answered"
    assert result.response_text == "hello there"
    assert result.selected_choice_key is None
    assert dm_channel.sent_messages == ["Status?"]
