"""
Single config loader for MV-GPT DSS.
Loads config/thresholds.yaml and parses into strictly typed Pydantic models.
Ensures zero hardcoded thresholds across all engines and safety checkers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class NumericThreshold(BaseModel):
    value: float
    unit: str
    source: str
    note: str | None = None


class StringThreshold(BaseModel):
    value: str
    source: str
    note: str | None = None


class ScopeKV(BaseModel):
    min: float
    max: float
    source: str


class MetaConfig(BaseModel):
    dissertation: str
    scope_kv: ScopeKV
    hours_per_month: NumericThreshold


class EA1Config(BaseModel):
    c2h2_critical: dict[str, NumericThreshold]
    flash_point_min: dict[str, NumericThreshold]


class EA2Config(BaseModel):
    safety_margin: NumericThreshold
    reference_standard: StringThreshold
    dissertation_example: dict[str, Any]


class EA3Config(BaseModel):
    avg_winding_rise_max: NumericThreshold
    hotspot_rise_max: NumericThreshold
    hotspot_absolute_max: NumericThreshold
    aging_step_temp: NumericThreshold
    aging_step_factor: NumericThreshold
    cooling_types: list[str]


class EA4Config(BaseModel):
    max_relative_diff_pct: NumericThreshold
    max_kva_ratio: NumericThreshold
    max_voltage_ratio_diff_pct: NumericThreshold


class EA5Config(BaseModel):
    phase_shift_per_clock: NumericThreshold
    tolerance: NumericThreshold


class BetaBand(BaseModel):
    min: float
    max: float
    source: str
    note: str | None = None


class RoundingConfig(BaseModel):
    value: str
    source: str
    note: str | None = None


class RAMConfig(BaseModel):
    min_observation_years: NumericThreshold
    target_availability: NumericThreshold
    exponential_beta_band: BetaBand
    interval_rounding: RoundingConfig
    switchgear_example: dict[str, Any] | None = None


class EnvironmentConfig(BaseModel):
    tropical_rh_threshold: NumericThreshold


class ComponentItem(BaseModel):
    id: str
    name_id: str


class ThresholdRegistry(BaseModel):
    meta: MetaConfig
    ea1: EA1Config
    ea2: EA2Config
    ea3: EA3Config
    ea4: EA4Config
    ea5: EA5Config
    ram: RAMConfig
    environment: EnvironmentConfig
    critical_components: list[ComponentItem]


def get_config_path() -> Path:
    """Find absolute path to config/thresholds.yaml."""
    base_dir = Path(__file__).resolve().parent.parent
    config_file = base_dir / "config" / "thresholds.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found at {config_file}")
    return config_file


@lru_cache(maxsize=1)
def load_thresholds(config_path: Path | str | None = None) -> ThresholdRegistry:
    """
    Load and parse thresholds.yaml.
    Cached for deterministic and zero-IO reuse during execution.
    """
    if config_path is None:
        path = get_config_path()
    else:
        path = Path(config_path)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return ThresholdRegistry(**data)
