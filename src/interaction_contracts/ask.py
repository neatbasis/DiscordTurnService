from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AskKind(str, Enum):
    """Transport-side ask flavor used by current Discord ask-turn routes."""

    FREEFORM = "freeform"
    MULTICHOICE = "multichoice"


class InteractionMode(str, Enum):
    """General semantic interaction mode for richer cross-channel contracts."""

    FREEFORM = "freeform"
    CHOICE = "choice"
    TEMPLATE_FILL = "template_fill"
    MIXED = "mixed"


class ChoiceOption(BaseModel):
    """Bounded selection option for transport-side choice prompts.

    This remains intentionally small and compatible for channels that only support
    direct option picking (for example, current Discord multichoice ask-turn).
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)


class SlotSpec(BaseModel):
    """Named field requirement for semantic interaction targets."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str | None = None
    required: bool = True
    multi: bool = False


class AnswerTemplate(BaseModel):
    """Semantic answer pattern whose sentences may contain wildcard {slots}."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    sentences: list[str] = Field(..., min_length=1)
    label: str | None = None
    slot_bindings: dict[str, object] = Field(default_factory=dict)


class InteractionSpec(BaseModel):
    """Semantic interaction contract consumed by transport executors.

    Not every transport/channel must implement all fields immediately; this model
    defines a neutral seam for richer interaction intent.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    mode: InteractionMode

    slots: list[SlotSpec] = Field(default_factory=list)
    choices: list[ChoiceOption] = Field(default_factory=list)
    templates: list[AnswerTemplate] = Field(default_factory=list)

    timeout_seconds: float = Field(default=60.0, gt=0, le=600)


class InteractionResult(BaseModel):
    """Normalized semantic interaction result, independent of runtime layer."""

    model_config = ConfigDict(extra="forbid")

    interaction_id: str = Field(..., min_length=1)
    status: Literal["answered", "timed_out", "cancelled", "error"]

    answer_id: str | None = None
    sentence: str | None = None
    slots: dict[str, object] = Field(default_factory=dict)

    channel: str = Field(..., min_length=1)
    error: str | None = None
    meta: dict[str, object] = Field(default_factory=dict)
