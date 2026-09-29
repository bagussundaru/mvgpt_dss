"""
Unit tests for EA Safety Checker (EA1-EA5).
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 6, 16-17, 46).
Strict compliance with .agents/rules/engineering-standards.md and ea-safety-checker SKILL.
"""

import pytest
from backend.config_loader import load_thresholds
from backend.safety.ea_checker import (
    check_dga_fire_risk,
    check_breaker_interrupting_capacity,
    check_cooling_adequacy,
    check_parallel_impedance,
    check_vector_group_compatibility,
)
from backend.schemas.common import CheckStatus


@pytest.fixture
def config():
    """Load system configuration from config/thresholds.yaml."""
    return load_thresholds()


# =========================================================================
# EA 1 — Kebakaran akibat flash point cairan pendingin yang rendah & DGA C2H2
# Hal. 16: C2H2 > 5 ppm -> DANGER (Dissertation p.16)
# =========================================================================
class TestEA1DGAFireRisk:
    """Uji pemeriksaan EA1: C2H2 dan flash point cairan isolasi."""

    def test_ea1_safe(self, config):
        result = check_dga_fire_risk(
            c2h2_ppm=2.0,
            fluid_type="mineral",
            flash_point_c=150.0,
            thresholds=config,
        )
        assert result.code == "EA1"
        assert result.status == CheckStatus.SAFE
        assert "5 ppm" in result.explanation_id or "aman" in result.explanation_id.lower()

    def test_ea1_danger_c2h2(self, config):
        # C2H2 = 6 ppm > 5 ppm ambang naskah
        result = check_dga_fire_risk(
            c2h2_ppm=6.0,
            fluid_type="synthetic_ester",
            flash_point_c=260.0,
            thresholds=config,
        )
        assert result.code == "EA1"
        assert result.status == CheckStatus.DANGER
        assert result.reference == "Dissertation p.16"
        assert "6.0" in result.explanation_id
        assert "5" in result.explanation_id

    def test_ea1_danger_flash_point(self, config):
        # Flash point mineral = 130 °C < ambang 140 °C IEC 60296
        result = check_dga_fire_risk(
            c2h2_ppm=1.0,
            fluid_type="mineral",
            flash_point_c=130.0,
            thresholds=config,
        )
        assert result.status == CheckStatus.DANGER
        assert "flash point" in result.explanation_id.lower()
        assert "130" in result.explanation_id

    def test_ea1_insufficient_data(self, config):
        result = check_dga_fire_risk(
            c2h2_ppm=None,
            fluid_type="mineral",
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "c2h2_ppm" in result.missing_fields
        # INSUFFICIENT_DATA tidak boleh jatuh ke SAFE
        assert result.status != CheckStatus.SAFE


# =========================================================================
# EA 2 — Ledakan MV Circuit Breaker / Fuse (IR < Isc)
# Hal. 16: IR 16 kA vs Isc 20 kA -> DANGER
# =========================================================================
class TestEA2InterruptingCapacity:
    """Uji pemeriksaan EA2: kapasitas pemutusan circuit breaker (IR vs Isc)."""

    def test_ea2_fixture_dissertation_danger(self, config):
        # Fixture eksplisit naskah hal. 16: IR 16 kA vs Isc 20 kA -> DANGER
        result = check_breaker_interrupting_capacity(
            ir_ka=16.0,
            isc_ka=20.0,
            thresholds=config,
        )
        assert result.code == "EA2"
        assert result.status == CheckStatus.DANGER
        assert "16" in result.explanation_id
        assert "20" in result.explanation_id
        assert "meledak" in result.explanation_id.lower() or "ledakan" in result.explanation_id.lower()

    def test_ea2_warning_margin(self, config):
        # Margin 1.2: 20 <= IR < 24 -> WARNING
        result = check_breaker_interrupting_capacity(
            ir_ka=22.0,
            isc_ka=20.0,
            thresholds=config,
        )
        assert result.code == "EA2"
        assert result.status == CheckStatus.WARNING
        assert "margin" in result.explanation_id.lower() or "tipis" in result.explanation_id.lower()

    def test_ea2_safe(self, config):
        # IR = 25 kA >= 1.2 * 20 = 24 kA -> SAFE
        result = check_breaker_interrupting_capacity(
            ir_ka=25.0,
            isc_ka=20.0,
            thresholds=config,
        )
        assert result.code == "EA2"
        assert result.status == CheckStatus.SAFE

    def test_ea2_insufficient_data(self, config):
        result = check_breaker_interrupting_capacity(
            ir_ka=None,
            isc_ka=20.0,
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "ir_ka" in result.missing_fields
        assert result.status != CheckStatus.SAFE


# =========================================================================
# EA 3 — Kebakaran akibat pemilihan tipe pendinginan tidak tepat
# Hal. 16 & 44: +7 °C di atas batas mempercepat penuaan ~30 % (aging factor = 1.30^(dT/7))
# =========================================================================
class TestEA3CoolingAdequacy:
    """Uji pemeriksaan EA3: kecukupan pendingin & aging acceleration factor."""

    def test_ea3_safe(self, config):
        result = check_cooling_adequacy(
            cooling_type="ONAN",
            load_kva=800.0,
            rated_kva=1000.0,
            ambient_temp_c=30.0,
            thresholds=config,
        )
        assert result.code == "EA3"
        assert result.status == CheckStatus.SAFE
        assert result.measured["aging_acceleration_factor"] == pytest.approx(1.0, abs=0.01)

    def test_ea3_overheating_aging_acceleration(self, config):
        # Beban lebih tinggi sehingga hotspot melampaui batas 110 °C
        result = check_cooling_adequacy(
            cooling_type="ONAN",
            load_kva=1300.0,
            rated_kva=1000.0,
            ambient_temp_c=40.0,
            thresholds=config,
        )
        assert result.code == "EA3"
        assert result.status in [CheckStatus.WARNING, CheckStatus.DANGER]
        assert result.measured["excess_temp_c"] > 0
        assert result.measured["aging_acceleration_factor"] > 1.0
        assert "penuaan" in result.explanation_id.lower() or "aging" in result.explanation_id.lower()

    def test_ea3_insufficient_data(self, config):
        result = check_cooling_adequacy(
            cooling_type="ONAN",
            load_kva=None,
            rated_kva=1000.0,
            ambient_temp_c=30.0,
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "load_kva" in result.missing_fields
        assert result.status != CheckStatus.SAFE


# =========================================================================
# EA 4 — Kerusakan operasi paralel: ketidaksesuaian impedansi (%Z)
# Hal. 17: selisih relatif > 10% -> DANGER & hitung arus sirkulasi
# =========================================================================
class TestEA4ParallelImpedance:
    """Uji pemeriksaan EA4: selisih relatif %Z dan arus sirkulasi."""

    def test_ea4_safe(self, config):
        # Za = 5.0, Zb = 5.2 -> selisih relatif 3.92% <= 10%
        result = check_parallel_impedance(
            z_pct_a=5.0,
            z_pct_b=5.2,
            thresholds=config,
        )
        assert result.code == "EA4"
        assert result.status == CheckStatus.SAFE
        assert result.measured["relative_diff_pct"] <= 10.0

    def test_ea4_danger_and_circulating_current(self, config):
        # Za = 5.0, Zb = 6.0 -> selisih relatif 18.18% > 10%
        result = check_parallel_impedance(
            z_pct_a=5.0,
            z_pct_b=6.0,
            kva_a=1000.0,
            kva_b=1000.0,
            rated_voltage_kv=20.0,
            thresholds=config,
        )
        assert result.code == "EA4"
        assert result.status == CheckStatus.DANGER
        assert result.measured["relative_diff_pct"] == pytest.approx(18.18, abs=0.1)
        assert "circulating_current_pct" in result.measured
        assert result.measured["circulating_current_pct"] > 0
        assert "sirkulasi" in result.explanation_id.lower()

    def test_ea4_insufficient_data(self, config):
        result = check_parallel_impedance(
            z_pct_a=5.0,
            z_pct_b=None,
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "z_pct_b" in result.missing_fields
        assert result.status != CheckStatus.SAFE


# =========================================================================
# EA 5 — Kerusakan operasi paralel: ketidaksesuaian vector group
# Hal. 17: beda jam ≠ 0 -> DANGER (murni biner, tidak ada WARNING)
# =========================================================================
class TestEA5VectorGroupCompatibility:
    """Uji pemeriksaan EA5: kompatibilitas vector group operasi paralel."""

    def test_ea5_safe_identical_vector(self, config):
        result = check_vector_group_compatibility(
            vector_a="Dyn11",
            vector_b="Dyn11",
            thresholds=config,
        )
        assert result.code == "EA5"
        assert result.status == CheckStatus.SAFE
        assert result.measured["phase_shift_deg"] == 0

    def test_ea5_danger_mismatched_vector(self, config):
        # Dyn11 vs Dyn5 -> selisih jam 6 (180 deg) -> DANGER (tidak ada WARNING)
        result = check_vector_group_compatibility(
            vector_a="Dyn11",
            vector_b="Dyn5",
            thresholds=config,
        )
        assert result.code == "EA5"
        assert result.status == CheckStatus.DANGER
        assert result.measured["phase_shift_deg"] == 180
        assert "fasa" in result.explanation_id.lower() or "bahaya" in result.explanation_id.lower()

    def test_ea5_invalid_format_insufficient_data(self, config):
        # Format tidak dikenal -> INSUFFICIENT_DATA, tidak boleh menebak
        result = check_vector_group_compatibility(
            vector_a="Dyn11",
            vector_b="XYZ99",
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "vector_b" in result.missing_fields

    def test_ea5_none_insufficient_data(self, config):
        result = check_vector_group_compatibility(
            vector_a=None,
            vector_b="Dyn11",
            thresholds=config,
        )
        assert result.status == CheckStatus.INSUFFICIENT_DATA
        assert "vector_a" in result.missing_fields
