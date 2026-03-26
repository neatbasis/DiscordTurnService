"""Transport-safe semantic interaction contracts.

This package defines neutral DTO-like models shared across orchestration and
transport boundaries. It is the semantic seam, not the runtime implementation
layer.
"""

from .ask import (
    AnswerTemplate,
    AskKind,
    ChoiceOption,
    InteractionMode,
    InteractionResult,
    InteractionSpec,
    SlotSpec,
)

__all__ = [
    "AskKind",
    "InteractionMode",
    "ChoiceOption",
    "SlotSpec",
    "AnswerTemplate",
    "InteractionSpec",
    "InteractionResult",
]
