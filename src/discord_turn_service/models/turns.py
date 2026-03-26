from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TurnDirection(str, Enum):
    SYSTEM_TO_USER = "system_to_user"
    USER_TO_SYSTEM = "user_to_system"


class TurnIntent(str, Enum):
    ASK = "ask"
    REPLY = "reply"


class TurnState(str, Enum):
    PENDING = "pending"
    ANSWERED = "answered"
    TIMEOUT = "timeout"
    ERROR = "error"


class TurnReasonType(str, Enum):
    DISCORD = "discord"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


class TurnReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TurnReasonType
    code: str = Field(..., min_length=1)
    message: str | None = Field(default=None, min_length=1)


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: ErrorDetail


class CreateTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=1)
    user_id: int
    prompt: str = Field(..., min_length=1)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    mode: Literal["dm"] = "dm"
    channel_id: int | None = None


class CreateCanonicalTurnRequest(CreateTurnRequest):
    model_config = ConfigDict(extra="forbid")

    direction: TurnDirection
    intent: TurnIntent


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str | None = Field(default=None, min_length=1)
    correlation_id: str = Field(..., min_length=1)
    user_id: int
    channel_id: int | None = None
    direction: TurnDirection
    intent: TurnIntent
    state: TurnState
    prompt: str = Field(..., min_length=1)
    response_text: str | None = None
    timeout_seconds: float = Field(..., gt=0, le=600)
    reason: TurnReason | None = None


class TurnOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=1)
    status: Literal["answered", "timeout", "error"]
    response_text: str | None = None
    user_id: int
    channel_id: int | None = None
    error: str | None = None
    reason: TurnReason | None = None


class RecordTurnOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "timeout", "error"]
    response_text: str | None = None
    channel_id: int | None = None
    error: str | None = None
    reason: TurnReason | None = None


class AskTurnRequest(CreateTurnRequest):
    model_config = ConfigDict(extra="forbid")


class AskTurnResult(TurnOutcome):
    model_config = ConfigDict(extra="forbid")
