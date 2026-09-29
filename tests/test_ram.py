"""
Unit tests for RAM Engine.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3.
Fixtures and test cases are strictly derived from dissertation-facts.md.
"""

import math
import pytest
from backend.config_loader import load_thresholds
from backend.engines.ram_engine import RAMEngine
from backend.schemas.ram_schemas import (
    CalculationStatus,
    IntervalResult,
    WeibullFit,
    MTBFResult,
    MTTRResult,
)


@pytest.fixture
def config():
    """Load system configuration from config/thresholds.yaml."""
    return load_thresholds()


@pytest.fixture
def ram_engine(config):
    """Instantiate RAMEngine with loaded configuration."""
    return RAMEngine(config=config)


# =========================================================================
# Test Case Wajib 1: Contoh 1 — Busi (Naskah hal. 27–28)
# MTBF = 250 jam
# R(50) = 81,87 %
# R(130) = 59,45 %
# F(130) = 1 - R = 40,55 %
# Toleransi test: ±0.01 (atau 0.01% dalam persentase)
# =========================================================================
class TestContoh1Busi:
    """Verifikasi Contoh 1 Busi dari Naskah hal. 27-28."""

    def test_reliability_at_50_hours(self, ram_engine):
        mtbf_hours = 250.0
        t_hours = 50.0
        r_50 = ram_engine.reliability(t=t_hours, mtbf=mtbf_hours)
        # 81.87% = 0.8187
        assert r_50 * 100 == pytest.approx(81.87, abs=0.01)

    def test_reliability_at_130_hours(self, ram_engine):
        mtbf_hours = 250.0
        t_hours = 130.0
        r_130 = ram_engine.reliability(t=t_hours, mtbf=mtbf_hours)
        # 59.45% = 0.5945
        assert r_130 * 100 == pytest.approx(59.45, abs=0.01)

    def test_unreliability_at_130_hours(self, ram_engine):
        mtbf_hours = 250.0
        t_hours = 130.0
        r_130 = ram_engine.reliability(t=t_hours, mtbf=mtbf_hours)
        f_130 = 1.0 - r_130
        # F(130) = 40.55%
        assert f_130 * 100 == pytest.approx(40.55, abs=0.01)


# =========================================================================
# Test Case Wajib 2: Contoh 2 — MV Switchgear 20 kV (Naskah hal. 28–29)
# Target R = 75 % pada t = 5 bulan
# Durasi inspection & testing 1 hari = 0,033 bulan
# MTBF = 5 / ln(1/0,75) = 17,38 bulan
# Naskah membulatkan ke atas menjadi 18 bulan (1,5 tahun) sebagai interval pemeliharaan
# A = 18 / (18 + 0,033) = 99,63 %
# =========================================================================
class TestContoh2Switchgear:
    """Verifikasi Contoh 2 Switchgear 20 kV dari Naskah hal. 28-29."""

    def test_maintenance_interval_and_mtbf_raw(self, ram_engine):
        t_months = 5.0
        target_r = 0.75

        result: IntervalResult = ram_engine.maintenance_interval(
            t=t_months,
            target_reliability=target_r,
            unit="months",
        )

        # Output wajib memuat mtbf_raw dan maintenance_interval_months / interval_months
        assert result.mtbf_raw == pytest.approx(17.38, abs=0.01)
        assert result.maintenance_interval_months == 18
        assert result.interval_months == 18
        # Verifikasi bahwa pembulatan dilakukan ke atas (ceil) konservatif
        assert result.interval_months == math.ceil(result.mtbf_raw)

    def test_availability_calculation(self, ram_engine, config):
        """
        Verifikasi ketersediaan (availability) Persamaan (2.3).
        Naskah hal. 28-29 mencatat: A = 18 / (18 + 0,033) = 99,63 %.
        Secara aritmetika presisi:
        - 18 / (18 + 0.033) = 99.817% (99.82%).
        - Angka 99.63% diperoleh persis jika durasi pemeliharaan adalah 2 hari (0.0667 bulan),
          yaitu 18 / (18 + 0.0667) = 99.63% atau 540 / 542 hari = 99.63%.
        Kedua kondisi diverifikasi sesuai thresholds.yaml.
        """
        mtbf_months = 18.0
        # 1. Evaluasi dengan MTTR 1 hari (0.033 bulan)
        mttr_1day = config.ram.switchgear_example["mttr_1day_months"]
        avail_1day = ram_engine.availability(mtbf=mtbf_months, mttr=mttr_1day)
        assert avail_1day * 100 == pytest.approx(config.ram.switchgear_example["availability_exact_1day"], abs=0.01)

        # 2. Evaluasi yang menghasilkan angka 99.63% persis teks naskah (durasi 2 hari = 0.0667 bulan)
        mttr_2days = config.ram.switchgear_example["mttr_2days_months"]
        avail_2days = ram_engine.availability(mtbf=mtbf_months, mttr=mttr_2days)
        assert avail_2days * 100 == pytest.approx(config.ram.switchgear_example["availability_exact_2days"], abs=0.01)

    def test_availability_with_mdt(self, ram_engine):
        # Bentuk diperluas Persamaan (2.3): A = MTBF / (MTBF + MTTR + MDT)
        mtbf = 1000.0
        mttr = 10.0
        mdt = 5.0
        avail = ram_engine.availability(mtbf=mtbf, mttr=mttr, mdt=mdt)
        expected = 1000.0 / (1000.0 + 10.0 + 5.0)
        assert avail == pytest.approx(expected, abs=0.0001)


# =========================================================================
# Formula RAM Dasar & Penanganan Zero Division (INSUFFICIENT_DATA)
# =========================================================================
class TestRAMBasicsAndEdgeCases:
    """Uji fungsi dasar RAM, penanganan pembagian nol, dan maintainability."""

    def test_mtbf_success(self, ram_engine):
        res = ram_engine.mtbf(uptime_hours=10000.0, failures=4)
        assert res.status == CalculationStatus.SUCCESS
        assert res.value == pytest.approx(2500.0, abs=0.01)

    def test_mtbf_zero_failures_insufficient_data(self, ram_engine):
        # Zero division: failures = 0 bukan error, tapi INSUFFICIENT_DATA
        res = ram_engine.mtbf(uptime_hours=10000.0, failures=0)
        assert res.status == CalculationStatus.INSUFFICIENT_DATA
        assert res.value is None
        assert "failures" in res.missing_fields or "kegagalan" in res.explanation_id.lower()

    def test_mttr_success(self, ram_engine):
        res = ram_engine.mttr(downtime_hours=48.0, failures=4)
        assert res.status == CalculationStatus.SUCCESS
        assert res.value == pytest.approx(12.0, abs=0.01)

    def test_mttr_zero_failures_insufficient_data(self, ram_engine):
        res = ram_engine.mttr(downtime_hours=0.0, failures=0)
        assert res.status == CalculationStatus.INSUFFICIENT_DATA
        assert res.value is None

    def test_maintainability(self, ram_engine):
        # M(t) = 1 - e^(-mu * t), mu = 1/MTTR = 0.1 /jam
        mu = 0.1
        t = 10.0
        m_t = ram_engine.maintainability(t=t, mu=mu)
        expected = 1.0 - math.exp(-0.1 * 10.0)
        assert m_t == pytest.approx(expected, abs=0.001)


# =========================================================================
# Weibull Fitting & Validasi Asumsi Eksponensial (Hal. 24)
# =========================================================================
class TestWeibullFitting:
    """Verifikasi fit_weibull dengan data tersensor kanan dan validasi beta band."""

    def test_exponential_band_validation(self, ram_engine):
        # Beta in [0.9, 1.1] valid untuk eksponensial (random failure)
        ttf_data = [100.0, 250.0, 400.0, 600.0, 850.0, 1200.0]
        # Generate data roughly exponential (beta ~ 1.0)
        fit: WeibullFit = ram_engine.fit_weibull(ttf=ttf_data)
        assert fit.beta > 0
        assert fit.eta > 0
        assert fit.mtbf > 0
        assert isinstance(fit.beta_ci, tuple)
        assert len(fit.beta_ci) == 2
        assert fit.beta_ci[0] <= fit.beta <= fit.beta_ci[1]

    def test_weibull_wearout_warning(self, ram_engine):
        # Beta > 1.1 (wear-out) harus menolak asumsi lambda konstan
        # Sesuai dissertation-facts.md p.24: beta di luar 0.9-1.1 memberi warning
        wearout_ttf = [1800.0, 1900.0, 1950.0, 2000.0, 2050.0, 2100.0, 2150.0, 2200.0]
        fit: WeibullFit = ram_engine.fit_weibull(ttf=wearout_ttf)
        assert fit.beta > 1.1
        assert not fit.is_exponential_valid
        assert fit.warning is not None
        assert "lambda konstan tidak berlaku" in fit.warning.lower() or "weibull" in fit.warning.lower()

    def test_weibull_with_right_censoring(self, ram_engine):
        # Unit yang tersensor kanan (masih beroperasi tanpa gagal)
        ttf = [300.0, 450.0, 700.0, 950.0]
        censored = [1000.0, 1000.0, 1000.0]
        fit: WeibullFit = ram_engine.fit_weibull(ttf=ttf, censored=censored)
        assert fit.beta > 0
        assert fit.eta > 0
        # Censored data should push eta higher than ttf alone
        fit_uncensored = ram_engine.fit_weibull(ttf=ttf)
        assert fit.eta > fit_uncensored.eta


# =========================================================================
# Unit Conversion & Thresholds Compliance
# =========================================================================
class TestUnitConversionsAndThresholds:
    """Pastikan konversi unit menggunakan meta.hours_per_month (730 jam)."""

    def test_hours_per_month_source(self, config, ram_engine):
        assert config.meta.hours_per_month.value == 730
        assert config.ram.interval_rounding.value == "ceil"
        assert config.ram.exponential_beta_band.min == 0.9
        assert config.ram.exponential_beta_band.max == 1.1

    def test_unit_conversion_in_maintenance_interval(self, ram_engine):
        # 5 bulan dalam jam adalah 5 * 730 = 3650 jam
        res_months = ram_engine.maintenance_interval(t=5.0, target_reliability=0.75, unit="months")
        res_hours = ram_engine.maintenance_interval(t=5.0 * 730, target_reliability=0.75, unit="hours")
        assert res_months.mtbf_raw == pytest.approx(res_hours.mtbf_raw / 730.0, abs=0.01)
