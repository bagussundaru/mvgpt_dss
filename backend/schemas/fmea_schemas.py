"""
Schemas for FMEA Matrix Engine.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 63-65).

Four-row structure (F-M-E-A, hal. 65):
- Row F: Components & Function (Nominal function & Functional failure)
- Row M: Failure Mode (Physical/chemical mechanism & root cause)
- Row E: Failure Effect (Local, system, end effects)
- Row A: Analysis (Hidden vs Evident, RPN with AIAG assumption, Engineering Tasks, Table 3.1 test mapping)
"""

from typing import Literal
from pydantic import BaseModel, Field


class RowF_ComponentFunction(BaseModel):
    """Row F: Components & Function (Naskah hal. 65)."""
    component_id: str
    component_name: str
    nominal_function: str
    functional_failure: str


class RowM_FailureMode(BaseModel):
    """Row M: Failure Mode & Mechanism (Naskah hal. 65)."""
    failure_mode_id: str
    failure_mode: str
    physical_mechanism: str
    root_cause: str


class RowE_FailureEffect(BaseModel):
    """Row E: Failure Effect (Naskah hal. 65)."""
    local_effect: str
    system_effect: str
    end_effect: str


class RowA_Analysis(BaseModel):
    """Row A: Analysis, RPN & Engineering Tasks (Naskah hal. 65)."""
    failure_characteristic: str
    hidden_or_evident: Literal["HIDDEN", "EVIDENT"]
    severity: int = Field(ge=1, le=10)
    occurrence: int = Field(ge=1, le=10)
    detection: int = Field(ge=1, le=10)
    rpn: int = Field(ge=1, le=1000)
    rpn_scale_assumption: str = "AIAG 1-10 (Implementation Assumption - Dissertation Bab IV Pending)"
    engineering_task: str
    test_method: str | None = None
    reference_standard: str
    reference_note: str | None = None


class FMEARow(BaseModel):
    """
    Single complete F-M-E-A item.
    Explicit 4-row structure mandated by dissertation p.65.
    """
    id: str
    row_f: RowF_ComponentFunction
    row_m: RowM_FailureMode
    row_e: RowE_FailureEffect
    row_a: RowA_Analysis


class FMEAMatrix(BaseModel):
    """Collection of FMEA rows for medium voltage green transformer."""
    rows: list[FMEARow]
