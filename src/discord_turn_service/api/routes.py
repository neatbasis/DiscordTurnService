from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from discord_turn_service.discord.runtime import runtime
from discord_turn_service.models.turns import (
    AskTurnRequest,
    AskTurnResult,
    CreateCanonicalTurnRequest,
    ErrorDetail,
    ErrorResponse,
    RecordTurnOutcomeRequest,
    Turn,
    TurnDirection,
    TurnIntent,
    TurnReason,
    TurnReasonType,
    TurnState,
)
from discord_turn_service.turns.service import (
    ActiveTurnExistsError,
    DiscordNotReadyError,
    UnsupportedModeError,
    turn_service,
)

router = APIRouter()

_turn_store: dict[str, Turn] = {}


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, bool]:
    return {"ready": runtime.is_ready()}


def _missing_turn_error(turn_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorDetail(
            code="turn_not_found",
            message=f"Turn not found: {turn_id}",
        ).model_dump(),
    )


def _create_turn(request: CreateCanonicalTurnRequest) -> Turn:
    turn = Turn(
        turn_id=str(uuid4()),
        correlation_id=request.correlation_id,
        user_id=request.user_id,
        channel_id=request.channel_id,
        direction=request.direction,
        intent=request.intent,
        state=TurnState.PENDING,
        prompt=request.prompt,
        timeout_seconds=request.timeout_seconds,
    )
    _turn_store[turn.turn_id or ""] = turn
    return turn


@router.post(
    "/turns",
    response_model=Turn,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation failure for the request payload.",
        },
    },
)
async def create_turn(request: CreateCanonicalTurnRequest) -> Turn:
    return _create_turn(request)


@router.get(
    "/turns/{turn_id}",
    response_model=Turn,
    responses={
        404: {"model": ErrorResponse, "description": "Turn ID does not exist."},
    },
)
async def get_turn(turn_id: str) -> Turn:
    turn = _turn_store.get(turn_id)
    if turn is None:
        raise _missing_turn_error(turn_id)
    return turn


@router.post(
    "/turns/{turn_id}/outcomes",
    response_model=Turn,
    responses={
        404: {"model": ErrorResponse, "description": "Turn ID does not exist."},
        422: {
            "model": ErrorResponse,
            "description": "Validation failure for the request payload.",
        },
    },
)
async def record_turn_outcome(turn_id: str, outcome: RecordTurnOutcomeRequest) -> Turn:
    turn = _turn_store.get(turn_id)
    if turn is None:
        raise _missing_turn_error(turn_id)

    reason = outcome.reason
    if outcome.status == "error" and reason is None and outcome.error:
        reason = TurnReason(
            type=TurnReasonType.INTERNAL,
            code="ask_turn_error",
            message=outcome.error,
        )

    updated_turn = turn.model_copy(
        update={
            "state": TurnState(outcome.status),
            "response_text": outcome.response_text,
            "channel_id": outcome.channel_id if outcome.channel_id is not None else turn.channel_id,
            "reason": reason,
        }
    )
    _turn_store[turn_id] = updated_turn
    return updated_turn


@router.post(
    "/ask-turn",
    response_model=AskTurnResult,
    responses={
        409: {
            "model": ErrorResponse,
            "description": "A user already has an active turn in progress.",
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation failure for the request payload.",
        },
    },
)
async def ask_turn(request: AskTurnRequest) -> AskTurnResult:
    try:
        result = await turn_service.ask_turn(request)
    except DiscordNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorDetail(code="discord_not_ready", message=str(exc)).model_dump(),
        ) from exc
    except ActiveTurnExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(code="active_turn_exists", message=str(exc)).model_dump(),
        ) from exc
    except UnsupportedModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(code="unsupported_mode", message=str(exc)).model_dump(),
        ) from exc


    canonical_turn = _create_turn(
        CreateCanonicalTurnRequest(
            correlation_id=request.correlation_id,
            user_id=request.user_id,
            prompt=request.prompt,
            timeout_seconds=request.timeout_seconds,
            mode=request.mode,
            channel_id=request.channel_id,
            direction=TurnDirection.SYSTEM_TO_USER,
            intent=TurnIntent.ASK,
        )
    )
    outcome = RecordTurnOutcomeRequest(
        status=result.status,
        response_text=result.response_text,
        channel_id=result.channel_id,
        error=result.error,
        reason=result.reason,
    )
    await record_turn_outcome(canonical_turn.turn_id or "", outcome)

    return result
