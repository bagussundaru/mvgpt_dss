"""
Schemas for Decision Service and Engineering Action Plans.
Bridges RAM (Frequency), FMEA (Tasks), and Safety (EA Checks).
Engineering Action = Engineering Task + Engineering Frequency.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.schemas.common import CheckResult, CheckStatus


class EngineeringAction(BaseModel):
    """
    Core deliverable of MV-GPT DSS.
    Engineering Action = Engineering Task (FMEA) + Engineering Frequency (RAM).
    """
    action_id: str
    component_id: str
    component_name: str
    fmea_row_id: str
    task_description: str
    test_method: str | None = None
    interval_months: int
    interval_hours: float
    target_reliability: float
    rpn: int
    ea_risk_status: Literal["SAFE", "WARNING", "DANGER", "INSUFFICIENT_DATA"]
    priority_rank: int
    source: str
    reference_standard: str
    reference_note: str | None = None


class UnscheduledTask(BaseModel):
    """
    Engineering Task from FMEA that cannot be assigned a frequency yet
    (e.g. insufficient failure data or zero failures).
    """
    task_id: str
    component_id: str
    component_name: str
    fmea_row_id: str
    task_description: str
    reason: str


class EngineeringActionPlan(BaseModel):
    """
    Complete consolidated action plan for a transformer unit.
    Ordered by: EA DANGER first -> Highest RPN -> Shortest Interval.
    """
    transformer_id: str
    utility_code: str
    overall_safety_status: CheckStatus
    ea_results: dict[str, CheckResult]
    actions: list[EngineeringAction]
    unscheduled_tasks: list[UnscheduledTask] = Field(default_factory=list)
    system_availability: float
    summary_notes: list[str] = Field(default_factory=list)
