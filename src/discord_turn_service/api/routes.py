from fastapi import APIRouter, HTTPException, status

from discord_turn_service.api.models import AskTurnRequest, AskTurnResult
from discord_turn_service.discord.runtime import runtime
from discord_turn_service.turns.service import (
    ActiveTurnExistsError,
    DiscordNotReadyError,
    UnsupportedModeError,
    turn_service,
)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, bool]:
    return {"ready": runtime.is_ready()}


@router.post("/ask-turn", response_model=AskTurnResult)
async def ask_turn(request: AskTurnRequest) -> AskTurnResult:
    try:
        return await turn_service.ask_turn(request)
    except DiscordNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ActiveTurnExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except UnsupportedModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
