"""Canonical transport-facing turn models.

These models define the stateless interaction boundary for directional
turn exchange. They intentionally exclude higher-order semantic concepts
such as intent, mission meaning, question state, or policy interpretation.

This layer records who said what to whom, in which direction, under which
correlation and operational outcome conditions.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TurnDirection(str, Enum):
    SYSTEM_TO_USER = "system_to_user"
    USER_TO_SYSTEM = "user_to_system"


class AskKind(str, Enum):
    FREEFORM = "freeform"
    MULTICHOICE = "multichoice"


class TurnState(str, Enum):
    """Operational lifecycle states for a canonical turn.

    These states describe transport and processing progression only.
    They do not describe semantic interpretation or downstream planning state.
    """

    RECEIVED = "received"
    OPEN = "open"
    ANSWERED = "answered"
    TIMED_OUT = "timed_out"
    CANCELED = "canceled"
    PROCESSED = "processed"
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


class ChoiceOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)


class CreateTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Caller-provided correlation key for joining this Discord turn with upstream "
            "orchestration records."
        ),
    )
    user_id: int = Field(
        ...,
        description=(
            "Discord user ID (snowflake). Upstream systems must resolve canonical identity "
            "into this Discord-native recipient field before calling this service."
        ),
    )
    prompt: str = Field(..., min_length=1)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    mode: Literal["dm"] = "dm"
    channel_id: int | None = Field(
        default=None,
        description=(
            "Optional Discord DM channel ID (snowflake). If omitted, the service resolves or "
            "creates a DM channel for the provided user_id."
        ),
    )
    direction: TurnDirection = TurnDirection.SYSTEM_TO_USER
    ask_kind: AskKind = Field(
        default=AskKind.FREEFORM,
        description=(
            "Discord interaction flavor for this turn. This is a transport interaction "
            "property (freeform vs multichoice), not higher-order semantic intent."
        ),
    )
    choices: list[ChoiceOption] = Field(
        default_factory=list,
        description=(
            "Selectable options for multichoice turns. Must be non-empty when "
            "ask_kind='multichoice' and empty for freeform turns."
        ),
    )

    @model_validator(mode="after")
    def _validate_ask_kind_choices(self) -> "CreateTurnRequest":
        if self.ask_kind == AskKind.MULTICHOICE and not self.choices:
            raise ValueError("choices must be provided when ask_kind='multichoice'")
        if self.ask_kind == AskKind.FREEFORM and self.choices:
            raise ValueError("choices must be empty when ask_kind='freeform'")
        return self


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str | None = Field(default=None, min_length=1)
    correlation_id: str = Field(..., min_length=1)
    user_id: int
    channel_id: int | None = None
    direction: TurnDirection
    state: TurnState
    prompt: str = Field(..., min_length=1)
    ask_kind: AskKind = AskKind.FREEFORM
    choices: list[ChoiceOption] = Field(default_factory=list)
    response_text: str | None = None
    selected_choice_key: str | None = Field(default=None, min_length=1)
    timeout_seconds: float = Field(..., gt=0, le=600)
    reason: TurnReason | None = None


class TurnOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=1)
    status: Literal["answered", "timed_out", "error"]
    response_text: str | None = None
    selected_choice_key: str | None = Field(default=None, min_length=1)
    user_id: int
    channel_id: int | None = None
    error: str | None = None
    reason: TurnReason | None = None


class RecordTurnOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "timed_out", "canceled", "processed", "error"]
    response_text: str | None = None
    selected_choice_key: str | None = Field(default=None, min_length=1)
    channel_id: int | None = None
    error: str | None = None
    reason: TurnReason | None = None


class AskTurnRequest(CreateTurnRequest):
    model_config = ConfigDict(extra="forbid")


class AskTurnResult(TurnOutcome):
    model_config = ConfigDict(extra="forbid")
