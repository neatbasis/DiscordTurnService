from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AskKind(str, Enum):
    FREEFORM = "freeform"
    MULTICHOICE = "multichoice"


class ChoiceOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)
