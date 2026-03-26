from fastapi import FastAPI
from fastapi.testclient import TestClient

from discord_turn_service.api.routes import _turn_store, router
from discord_turn_service.models.turns import AskTurnResult

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def setup_function() -> None:
    _turn_store.clear()


def test_invalid_transition_returns_409() -> None:
    created = client.post(
        "/turns",
        json={
            "correlation_id": "corr-1",
            "user_id": 1,
            "prompt": "hello",
            "mode": "dm",
            "direction": "system_to_user",
        },
    )
    turn_id = created.json()["turn_id"]

    response = client.post(
        f"/turns/{turn_id}/outcomes",
        json={"status": "answered", "response_text": "hi"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_turn_transition"


def test_malformed_outcome_status_returns_422() -> None:
    created = client.post(
        "/turns",
        json={
            "correlation_id": "corr-2",
            "user_id": 1,
            "prompt": "hello",
            "mode": "dm",
            "direction": "system_to_user",
        },
    )
    turn_id = created.json()["turn_id"]

    response = client.post(
        f"/turns/{turn_id}/outcomes",
        json={"status": "not_a_state"},
    )

    assert response.status_code == 422


def test_create_turn_multichoice_and_record_selected_choice() -> None:
    created = client.post(
        "/turns",
        json={
            "correlation_id": "corr-3",
            "user_id": 1,
            "prompt": "Choose route",
            "mode": "dm",
            "direction": "system_to_user",
            "ask_kind": "multichoice",
            "choices": [
                {"key": "fastest", "label": "Fastest"},
                {"key": "safest", "label": "Safest"},
            ],
        },
    )
    assert created.status_code == 201
    assert created.json()["ask_kind"] == "multichoice"
    assert len(created.json()["choices"]) == 2


def test_create_turn_freeform_with_choices_returns_422() -> None:
    response = client.post(
        "/turns",
        json={
            "correlation_id": "corr-4",
            "user_id": 1,
            "prompt": "Status?",
            "mode": "dm",
            "direction": "system_to_user",
            "ask_kind": "freeform",
            "choices": [{"key": "x", "label": "X"}],
        },
    )
    assert response.status_code == 422


def test_ask_turn_owns_direction_and_persists_outbound_turn(monkeypatch) -> None:
    async def fake_ask_turn(request):
        return AskTurnResult(
            correlation_id=request.correlation_id,
            status="answered",
            response_text="Roger",
            user_id=request.user_id,
            channel_id=999,
        )

    monkeypatch.setattr("discord_turn_service.api.routes.turn_service.ask_turn", fake_ask_turn)

    response = client.post(
        "/ask-turn",
        json={
            "correlation_id": "corr-ask-1",
            "user_id": 42,
            "prompt": "Status?",
            "mode": "dm",
            "timeout_seconds": 30,
            "ask_kind": "freeform",
        },
    )

    assert response.status_code == 200
    stored_turn = next(iter(_turn_store.values()))
    assert stored_turn.direction.value == "system_to_user"


def test_ask_turn_rejects_direction_input() -> None:
    response = client.post(
        "/ask-turn",
        json={
            "correlation_id": "corr-ask-2",
            "user_id": 42,
            "prompt": "Status?",
            "mode": "dm",
            "direction": "system_to_user",
        },
    )

    assert response.status_code == 422
