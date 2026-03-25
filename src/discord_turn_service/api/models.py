from typing import Literal, Optional

from pydantic import BaseModel, Field


class AskTurnRequest(BaseModel):
    correlation_id: str = Field(..., min_length=1)
    user_id: int
    prompt: str = Field(..., min_length=1)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    mode: Literal["dm"] = "dm"


class AskTurnResult(BaseModel):
    correlation_id: str
    status: Literal["answered", "timeout", "error"]
    response_text: Optional[str] = None
    user_id: int
    channel_id: Optional[int] = None
    error: Optional[str] = None
