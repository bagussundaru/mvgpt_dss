"""
Schemas for RAM Engine calculations.
Strictly maps to formulas from Prabowo Soetadji - Proposal Bab I-III Rev3.
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class CalculationStatus(str, Enum):
    """Status of mathematical calculation."""
    SUCCESS = "SUCCESS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MTBFResult(BaseModel):
    """
    Result of MTBF calculation.
    Persamaan (2.1): MTBF = 1/lambda = uptime / failures.
    """
    status: Literal["SUCCESS", "INSUFFICIENT_DATA"]
    value: float | None = None
    unit: str = "hours"
    explanation_id: str
    reference: str = "Dissertation p.23 Eq. (2.1)"
    missing_fields: list[str] = Field(default_factory=list)


class MTTRResult(BaseModel):
    """
    Result of MTTR calculation.
    Persamaan (2.3): MTTR = downtime / failures.
    """
    status: Literal["SUCCESS", "INSUFFICIENT_DATA"]
    value: float | None = None
    unit: str = "hours"
    explanation_id: str
    reference: str = "Dissertation p.24 Eq. (2.3)"
    missing_fields: list[str] = Field(default_factory=list)


class IntervalResult(BaseModel):
    """
    Result of maintenance interval determination.
    Persamaan (2.2): MTBF = t / ln[1 / R(t)].
    Output provides both mtbf_raw and conservative rounded interval.
    """
    mtbf_raw: float
    interval_months: int
    maintenance_interval_months: int
    target_reliability: float
    t_value: float
    unit: str = "months"
    explanation_id: str
    reference: str = "Dissertation p.23 Eq. (2.2), p.28-29"
    source: str = "Dissertation p.28-29"


class WeibullFit(BaseModel):
    """
    Result of Weibull MLE fitting with right-censored data support.
    Persamaan (2.5): R(t) = exp(-(t/eta)^beta).
    Includes confidence intervals and exponential assumption validation.
    """
    beta: float
    beta_ci: tuple[float, float]
    eta: float
    eta_ci: tuple[float, float]
    mtbf: float
    is_exponential_valid: bool
    warning: str | None = None
    log_likelihood: float | None = None
    reference: str = "Dissertation p.24 Eq. (2.5)"


class EngineeringFrequency(BaseModel):
    """
    RAM output component for Engineering Actions.
    Engineering Action = Engineering Task + Engineering Frequency.
    """
    component: str
    target_reliability: float
    interval_months: int
    interval_hours: float
    recommendation: str
    source: str = "Dissertation p.28-29"
