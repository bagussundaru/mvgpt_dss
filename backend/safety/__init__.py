"""Safety package for Electrical Accident checking."""
from backend.safety.ea_checker import (
    check_dga_fire_risk,
    check_breaker_interrupting_capacity,
    check_cooling_adequacy,
    check_parallel_impedance,
    check_vector_group_compatibility,
)

__all__ = [
    "check_dga_fire_risk",
    "check_breaker_interrupting_capacity",
    "check_cooling_adequacy",
    "check_parallel_impedance",
    "check_vector_group_compatibility",
]
