"""Common schema models across MV-GPT DSS."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    """Uniform check status across EA and validation checkers."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CheckResult(BaseModel):
    """
    Uniform result structure for all safety checks (EA1-EA5).
    Mandated by engineering-standards.md.
    """
    code: str
    status: Literal["SAFE", "WARNING", "DANGER", "INSUFFICIENT_DATA"]
    measured: dict[str, Any]
    threshold: dict[str, Any]
    explanation_id: str
    reference: str
    missing_fields: list[str] = Field(default_factory=list)
