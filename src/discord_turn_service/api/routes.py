from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from discord_turn_service.discord.runtime import runtime
from discord_turn_service.models.turns import (
    AskTurnRequest,
    AskTurnResult,
    CreateTurnRequest,
    ErrorDetail,
    ErrorResponse,
    RecordTurnOutcomeRequest,
    Turn,
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
from discord_turn_service.turns.state_machine import InvalidTurnTransitionError
from discord_turn_service.turns.store_service import TurnNotFoundError, TurnStoreService

router = APIRouter()

_turn_store: dict[str, Turn] = {}
turn_store_service = TurnStoreService(store=_turn_store)


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


def _invalid_transition_error(exc: InvalidTurnTransitionError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorDetail(
            code="invalid_turn_transition",
            message=str(exc),
        ).model_dump(),
    )


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
async def create_turn(request: CreateTurnRequest) -> Turn:
    return turn_store_service.create_turn(turn_id=str(uuid4()), request=request)


@router.get(
    "/turns/{turn_id}",
    response_model=Turn,
    responses={
        404: {"model": ErrorResponse, "description": "Turn ID does not exist."},
    },
)
async def get_turn(turn_id: str) -> Turn:
    try:
        return turn_store_service.get_turn(turn_id)
    except TurnNotFoundError as exc:
        raise _missing_turn_error(turn_id) from exc


@router.post(
    "/turns/{turn_id}/outcomes",
    response_model=Turn,
    responses={
        404: {"model": ErrorResponse, "description": "Turn ID does not exist."},
        409: {"model": ErrorResponse, "description": "Forbidden turn lifecycle transition."},
        422: {
            "model": ErrorResponse,
            "description": "Validation failure for the request payload.",
        },
    },
)
async def record_turn_outcome(turn_id: str, outcome: RecordTurnOutcomeRequest) -> Turn:
    reason = outcome.reason
    if outcome.status == "error" and reason is None and outcome.error:
        reason = TurnReason(
            type=TurnReasonType.INTERNAL,
            code="ask_turn_error",
            message=outcome.error,
        )

    try:
        return turn_store_service.apply_transition(
            turn_id=turn_id,
            to_state=TurnState(outcome.status),
            response_text=outcome.response_text,
            selected_choice_key=outcome.selected_choice_key,
            channel_id=outcome.channel_id,
            reason=reason,
        )
    except TurnNotFoundError as exc:
        raise _missing_turn_error(turn_id) from exc
    except InvalidTurnTransitionError as exc:
        raise _invalid_transition_error(exc) from exc


@router.post(
    "/ask-turn",
    response_model=AskTurnResult,
    responses={
        409: {
            "model": ErrorResponse,
            "description": (
                "A user already has an active turn in progress or turn transition conflict."
            ),
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation failure for the request payload.",
        },
    },
)
async def ask_turn(request: AskTurnRequest) -> AskTurnResult:
    canonical_turn = turn_store_service.create_turn(turn_id=str(uuid4()), request=request)

    try:
        turn_store_service.apply_transition(canonical_turn.turn_id or "", TurnState.OPEN)

        result = await turn_service.ask_turn(request)

        final_turn = turn_store_service.apply_transition(
            canonical_turn.turn_id or "",
            TurnState(result.status),
            response_text=result.response_text,
            selected_choice_key=result.selected_choice_key,
            channel_id=result.channel_id,
            reason=result.reason,
        )
        if final_turn.state == TurnState.ANSWERED:
            turn_store_service.apply_transition(
                canonical_turn.turn_id or "",
                TurnState.PROCESSED,
                response_text=result.response_text,
                selected_choice_key=result.selected_choice_key,
                channel_id=result.channel_id,
                reason=result.reason,
            )
        return result

    except DiscordNotReadyError as exc:
        turn_store_service.apply_transition(
            canonical_turn.turn_id or "",
            TurnState.ERROR,
            reason=TurnReason(
                type=TurnReasonType.DISCORD,
                code="discord_not_ready",
                message=str(exc),
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorDetail(code="discord_not_ready", message=str(exc)).model_dump(),
        ) from exc
    except ActiveTurnExistsError as exc:
        turn_store_service.apply_transition(
            canonical_turn.turn_id or "",
            TurnState.CANCELED,
            reason=TurnReason(
                type=TurnReasonType.VALIDATION,
                code="active_turn_exists",
                message=str(exc),
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(code="active_turn_exists", message=str(exc)).model_dump(),
        ) from exc
    except UnsupportedModeError as exc:
        turn_store_service.apply_transition(
            canonical_turn.turn_id or "",
            TurnState.CANCELED,
            reason=TurnReason(
                type=TurnReasonType.VALIDATION,
                code="unsupported_mode",
                message=str(exc),
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(code="unsupported_mode", message=str(exc)).model_dump(),
        ) from exc
    except InvalidTurnTransitionError as exc:
        raise _invalid_transition_error(exc) from exc
