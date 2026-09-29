"""
RAM Engine — Reliability, Availability, Maintainability Pure Mathematical Engine.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3.

Equations implemented:
- (2.1) R(t) = exp(-lambda * t) = exp(-t / MTBF), MTBF = 1 / lambda (p. 23)
- (2.2) MTBF = t / ln[1 / R(t)] (p. 23)
- (2.3) A = MTBF / (MTBF + MTTR), or A = MTBF / (MTBF + MTTR + MDT) (p. 24)
- (2.4) M(t) = 1 - exp(-mu * t), mu = restoration rate = 1 / MTTR (p. 24)
- (2.5) Weibull: R(t) = exp(-(t / eta)^beta), MTBF = eta * Gamma(1 + 1/beta) (p. 24)

Non-negotiable principles:
- Zero hardcoded thresholds; loaded config is injected.
- Pure functions: no I/O, no network, no prints, no Streamlit imports.
- Explicit unit handling with internal base unit: hours.
"""

import math
from typing import Literal
import numpy as np
from scipy.optimize import minimize
from scipy.special import gamma

from backend.config_loader import ThresholdRegistry, load_thresholds
from backend.schemas.ram_schemas import (
    CalculationStatus,
    EngineeringFrequency,
    IntervalResult,
    MTBFResult,
    MTTRResult,
    WeibullFit,
)


class RAMEngine:
    """RAM mathematical engine for medium voltage transformers."""

    def __init__(self, config: ThresholdRegistry | None = None):
        """
        Initialize RAMEngine with injected configuration registry.
        If config is not provided, defaults to loaded thresholds.
        """
        self.config = config or load_thresholds()

    def _get_hours_multiplier(self, unit: Literal["hours", "months", "years"]) -> float:
        """Get hours multiplier based on thresholds configuration."""
        hours_per_month = self.config.meta.hours_per_month.value
        if unit == "hours":
            return 1.0
        elif unit == "months":
            return hours_per_month
        elif unit == "years":
            return hours_per_month * 12.0
        raise ValueError(f"Unit tidak valid: {unit}. Gunakan 'hours', 'months', atau 'years'.")

    def mtbf(
        self,
        uptime_hours: float,
        failures: int,
        unit: Literal["hours", "months", "years"] = "hours",
    ) -> MTBFResult:
        """
        Compute Mean Time Between Failures.
        Equation (2.1), p. 23: MTBF = uptime / failures.
        failures = 0 returns INSUFFICIENT_DATA without raising division error.
        """
        if failures <= 0:
            return MTBFResult(
                status=CalculationStatus.INSUFFICIENT_DATA,
                value=None,
                unit=unit,
                explanation_id="Belum ada data kegagalan tercatat (failures = 0).",
                missing_fields=["failures"],
            )

        multiplier = self._get_hours_multiplier(unit)
        mtbf_val = (uptime_hours / failures) / multiplier
        return MTBFResult(
            status=CalculationStatus.SUCCESS,
            value=mtbf_val,
            unit=unit,
            explanation_id=f"MTBF berhasil dihitung: {mtbf_val:.2f} {unit}.",
        )

    def mttr(
        self,
        downtime_hours: float,
        failures: int,
        unit: Literal["hours", "months", "years"] = "hours",
    ) -> MTTRResult:
        """
        Compute Mean Time to Repair.
        Equation (2.3), p. 24: MTTR = downtime / failures.
        failures = 0 returns INSUFFICIENT_DATA.
        """
        if failures <= 0:
            return MTTRResult(
                status=CalculationStatus.INSUFFICIENT_DATA,
                value=None,
                unit=unit,
                explanation_id="Belum ada data pemulihan tercatat (failures = 0).",
                missing_fields=["failures"],
            )

        multiplier = self._get_hours_multiplier(unit)
        mttr_val = (downtime_hours / failures) / multiplier
        return MTTRResult(
            status=CalculationStatus.SUCCESS,
            value=mttr_val,
            unit=unit,
            explanation_id=f"MTTR berhasil dihitung: {mttr_val:.2f} {unit}.",
        )

    def availability(
        self,
        mtbf: float,
        mttr: float,
        mdt: float = 0.0,
    ) -> float:
        """
        Compute operational availability.
        Equation (2.3), p. 24: A = MTBF / (MTBF + MTTR + MDT).
        """
        total_time = mtbf + mttr + mdt
        if total_time <= 0:
            raise ValueError("Total waktu (MTBF + MTTR + MDT) harus bernilai positif.")
        return mtbf / total_time

    def reliability(self, t: float, mtbf: float) -> float:
        """
        Compute exponential reliability at mission time t.
        Equation (2.1), p. 23: R(t) = exp(-t / MTBF).
        """
        if mtbf <= 0:
            raise ValueError("MTBF harus bernilai positif untuk menghitung reliability.")
        return math.exp(-t / mtbf)

    def maintainability(self, t: float, mu: float) -> float:
        """
        Compute maintainability probability within time t.
        Equation (2.4), p. 24: M(t) = 1 - exp(-mu * t).
        """
        if mu <= 0:
            raise ValueError("Restoration rate mu harus bernilai positif.")
        return 1.0 - math.exp(-mu * t)

    def maintenance_interval(
        self,
        t: float,
        target_reliability: float,
        unit: Literal["hours", "months", "years"] = "months",
    ) -> IntervalResult:
        """
        Determine maintenance interval from target reliability.
        Equation (2.2), p. 23 & Application p. 28-29:
        MTBF = t / ln[1 / R(t)].
        Rounds up conservatively using ceil per dissertation convention.
        """
        if not (0.0 < target_reliability < 1.0):
            raise ValueError("Target reliability harus berada pada rentang (0, 1).")
        if t <= 0:
            raise ValueError("Waktu evaluasi t harus lebih besar dari 0.")

        # Persamaan (2.2): MTBF = t / ln(1 / R)
        mtbf_raw = t / math.log(1.0 / target_reliability)

        # Konversi dan pembulatan ke satuan bulan sesuai naskah
        if unit == "months":
            interval_months = math.ceil(mtbf_raw)
        elif unit == "hours":
            hours_per_month = self.config.meta.hours_per_month.value
            interval_months = math.ceil(mtbf_raw / hours_per_month)
        else:  # years
            interval_months = math.ceil(mtbf_raw * 12.0)

        expl = (
            f"Target R={target_reliability*100:.1f}% pada t={t} {unit} menghasilkan "
            f"MTBF={mtbf_raw:.2f} {unit}. Dibulatkan konservatif ke atas menjadi "
            f"{interval_months} bulan."
        )

        return IntervalResult(
            mtbf_raw=mtbf_raw,
            interval_months=interval_months,
            maintenance_interval_months=interval_months,
            target_reliability=target_reliability,
            t_value=t,
            unit=unit,
            explanation_id=expl,
        )

    def fit_weibull(
        self,
        ttf: list[float],
        censored: list[float] | None = None,
    ) -> WeibullFit:
        """
        Estimate Weibull parameters (beta, eta) via Maximum Likelihood Estimation
        with exact right-censoring support and parameter confidence intervals.
        Equation (2.5), p. 24: R(t) = exp(-(t/eta)^beta).
        """
        if not ttf:
            raise ValueError("Data time-to-failure (ttf) tidak boleh kosong.")

        ttf_arr = np.array(ttf, dtype=float)
        cens_arr = np.array(censored, dtype=float) if censored else np.array([], dtype=float)

        if np.any(ttf_arr <= 0) or (len(cens_arr) > 0 and np.any(cens_arr <= 0)):
            raise ValueError("Semua nilai waktu kegagalan dan sensor harus positif.")

        n_events = len(ttf_arr)
        sum_log_ttf = float(np.sum(np.log(ttf_arr)))

        # Parameterize in unconstrained log-space: [ln(beta), ln(eta)]
        def neg_log_likelihood(params: np.ndarray) -> float:
            log_b, log_e = params[0], params[1]
            b = math.exp(log_b)
            e = math.exp(log_e)
            term1 = n_events * log_b
            term2 = n_events * b * log_e
            term3 = (b - 1.0) * sum_log_ttf
            term4 = float(np.sum((ttf_arr / e) ** b))
            term5 = float(np.sum((cens_arr / e) ** b)) if len(cens_arr) > 0 else 0.0
            log_lik = term1 - term2 + term3 - (term4 + term5)
            return -log_lik

        # Initial guesses: beta ~ 1.0, eta ~ mean(ttf)
        init_beta = 1.0
        init_eta = float(np.mean(ttf_arr))
        init_params = np.array([math.log(init_beta), math.log(init_eta)])

        res = minimize(neg_log_likelihood, init_params, method="BFGS")
        log_beta_opt, log_eta_opt = res.x[0], res.x[1]
        beta_est = float(math.exp(log_beta_opt))
        eta_est = float(math.exp(log_eta_opt))

        # Asymptotic 95% confidence intervals from inverted Hessian
        try:
            cov = res.hess_inv
            se_log_b = math.sqrt(max(float(cov[0, 0]), 1e-4))
            se_log_e = math.sqrt(max(float(cov[1, 1]), 1e-4))
        except Exception:
            se_log_b = 0.1
            se_log_e = 0.1

        beta_ci = (
            float(beta_est * math.exp(-1.96 * se_log_b)),
            float(beta_est * math.exp(1.96 * se_log_b)),
        )
        eta_ci = (
            float(eta_est * math.exp(-1.96 * se_log_e)),
            float(eta_est * math.exp(1.96 * se_log_e)),
        )

        # Weibull MTBF = eta * Gamma(1 + 1/beta) (p. 24)
        weibull_mtbf = float(eta_est * gamma(1.0 + 1.0 / beta_est))

        # Bathtub curve validation: Persamaan (2.1) hanya valid pada fase random failure (0.9 <= beta <= 1.1)
        b_min = self.config.ram.exponential_beta_band.min
        b_max = self.config.ram.exponential_beta_band.max
        is_exp_valid = (b_min <= beta_est <= b_max)

        warning_msg = None
        if not is_exp_valid:
            warning_msg = (
                f"Beta Weibull={beta_est:.2f} di luar rentang {b_min}-{b_max}. "
                "Asumsi lambda konstan tidak berlaku; gunakan model Weibull untuk interval pemeliharaan."
            )

        return WeibullFit(
            beta=beta_est,
            beta_ci=beta_ci,
            eta=eta_est,
            eta_ci=eta_ci,
            mtbf=weibull_mtbf,
            is_exponential_valid=is_exp_valid,
            warning=warning_msg,
            log_likelihood=float(-res.fun),
        )

    def engineering_frequency(
        self,
        component: str,
        target_reliability: float,
        t_eval: float = 5.0,
        unit: Literal["hours", "months", "years"] = "months",
    ) -> EngineeringFrequency:
        """
        Determine Engineering Frequency for a component as part of Engineering Action.
        Engineering Action = Engineering Task + Engineering Frequency.
        """
        res = self.maintenance_interval(
            t=t_eval,
            target_reliability=target_reliability,
            unit=unit,
        )
        hours_per_month = self.config.meta.hours_per_month.value
        interval_hrs = res.interval_months * hours_per_month

        rec = (
            f"Lakukan pemeliharaan berkala untuk komponen {component} "
            f"setiap {res.interval_months} bulan ({interval_hrs:.0f} jam) "
            f"guna menjaga keandalan di atas {target_reliability*100:.1f}%."
        )

        return EngineeringFrequency(
            component=component,
            target_reliability=target_reliability,
            interval_months=res.interval_months,
            interval_hours=interval_hrs,
            recommendation=rec,
        )
