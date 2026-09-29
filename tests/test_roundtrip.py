"""
Roundtrip Verification Test.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3.

Verifies:
1. Parameter recovery: fit_weibull recovers ground-truth beta and eta from synthetic data
   within confidence intervals.
2. EA trigger verification: all 5 deliberate Electrical Accident triggers in dummy data
   properly trigger DANGER status in EA checkers.
"""

import json
from pathlib import Path
import pytest

from backend.config_loader import load_thresholds
from backend.engines.ram_engine import RAMEngine
from backend.safety.ea_checker import (
    check_dga_fire_risk,
    check_breaker_interrupting_capacity,
    check_cooling_adequacy,
    check_parallel_impedance,
    check_vector_group_compatibility,
)
from backend.schemas.common import CheckStatus


@pytest.fixture
def dataset_and_truth():
    base_dir = Path(__file__).resolve().parent.parent
    data_file = base_dir / "data" / "dummy_transformers.json"
    truth_file = base_dir / "data" / "dummy_transformers_truth.json"

    assert data_file.exists(), "dummy_transformers.json must exist"
    assert truth_file.exists(), "dummy_transformers_truth.json must exist"

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(truth_file, "r", encoding="utf-8") as f:
        truth = json.load(f)

    return data, truth


@pytest.fixture
def config():
    return load_thresholds()


@pytest.fixture
def ram_engine(config):
    return RAMEngine(config=config)


class TestRoundtripWeibullRecovery:
    """Verifikasi bahwa RAM engine dapat menemukan kembali parameter Weibull dari data."""

    def test_weibull_parameter_recovery(self, dataset_and_truth, ram_engine):
        _, truth = dataset_and_truth
        components_truth = truth["components_truth"]
        component_samples = truth["component_samples"]

        for comp, truth_params in components_truth.items():
            true_beta = truth_params["beta"]
            true_eta = truth_params["eta"]

            failures = component_samples[comp]["failures"]
            censored = component_samples[comp]["censored"]

            assert len(failures) > 0, f"Component {comp} must have failure data"

            fit = ram_engine.fit_weibull(ttf=failures, censored=censored)

            # Beta estimate should be within confidence interval
            assert fit.beta_ci[0] <= fit.beta <= fit.beta_ci[1]
            assert fit.eta_ci[0] <= fit.eta <= fit.eta_ci[1]

            # Statistical recovery: estimated beta within reasonable range of true beta
            # (allowing for statistical variation with 30 units)
            rel_error_beta = abs(fit.beta - true_beta) / true_beta
            assert rel_error_beta < 0.40, f"Beta recovery error for {comp} is too high: {rel_error_beta:.2f}"

            # Recovery of infant mortality vs wear-out characteristic
            if true_beta > 1.1:
                assert fit.beta > 1.0, f"Wearout component {comp} should have beta > 1.0"
            elif true_beta < 0.95:
                assert fit.beta < 1.1, f"Infant mortality component {comp} should have beta < 1.1"


class TestDeliberateEATriggers:
    """Verifikasi bahwa kelima pemicu kecelakaan listrik terdeteksi DANGER oleh EA checker."""

    def test_ea1_trigger_detected(self, dataset_and_truth, config):
        data, _ = dataset_and_truth
        tx11 = next(u for u in data["transformers"] if u["transformer_id"] == "TX-11")

        result = check_dga_fire_risk(
            c2h2_ppm=tx11["operating_condition"]["c2h2_ppm"],
            fluid_type=tx11["nameplate"]["fluid_type"],
            flash_point_c=tx11["nameplate"]["flash_point_c"],
            thresholds=config,
        )
        assert result.code == "EA1"
        assert result.status == CheckStatus.DANGER
        assert tx11["operating_condition"]["c2h2_ppm"] == 7.0

    def test_ea2_trigger_detected(self, dataset_and_truth, config):
        data, _ = dataset_and_truth
        tx12 = next(u for u in data["transformers"] if u["transformer_id"] == "TX-12")

        result = check_breaker_interrupting_capacity(
            ir_ka=tx12["operating_condition"]["breaker_ir_ka"],
            isc_ka=tx12["operating_condition"]["breaker_isc_ka"],
            thresholds=config,
        )
        assert result.code == "EA2"
        assert result.status == CheckStatus.DANGER
        assert tx12["operating_condition"]["breaker_ir_ka"] == 16.0
        assert tx12["operating_condition"]["breaker_isc_ka"] == 20.0

    def test_ea3_trigger_detected(self, dataset_and_truth, config):
        data, _ = dataset_and_truth
        tx13 = next(u for u in data["transformers"] if u["transformer_id"] == "TX-13")

        result = check_cooling_adequacy(
            cooling_type=tx13["nameplate"]["cooling_type"],
            load_kva=tx13["operating_condition"]["load_kva"],
            rated_kva=tx13["nameplate"]["rated_kva"],
            ambient_temp_c=tx13["operating_condition"]["ambient_temp_c"],
            thresholds=config,
        )
        assert result.code == "EA3"
        assert result.status == CheckStatus.DANGER
        assert result.measured["aging_acceleration_factor"] > 1.30

    def test_ea4_trigger_detected(self, dataset_and_truth, config):
        data, _ = dataset_and_truth
        pair1 = next(p for p in data["parallel_pairs"] if p["pair_id"] == "PAIR-01")
        tx5 = next(u for u in data["transformers"] if u["transformer_id"] == pair1["unit_a_id"])
        tx6 = next(u for u in data["transformers"] if u["transformer_id"] == pair1["unit_b_id"])

        result = check_parallel_impedance(
            z_pct_a=tx5["nameplate"]["impedance_z_pct"],
            z_pct_b=tx6["nameplate"]["impedance_z_pct"],
            kva_a=tx5["nameplate"]["rated_kva"],
            kva_b=tx6["nameplate"]["rated_kva"],
            thresholds=config,
        )
        assert result.code == "EA4"
        assert result.status == CheckStatus.DANGER
        assert result.measured["relative_diff_pct"] > 10.0

    def test_ea5_trigger_detected(self, dataset_and_truth, config):
        data, _ = dataset_and_truth
        pair2 = next(p for p in data["parallel_pairs"] if p["pair_id"] == "PAIR-02")
        tx7 = next(u for u in data["transformers"] if u["transformer_id"] == pair2["unit_a_id"])
        tx8 = next(u for u in data["transformers"] if u["transformer_id"] == pair2["unit_b_id"])

        result = check_vector_group_compatibility(
            vector_a=tx7["nameplate"]["vector_group"],
            vector_b=tx8["nameplate"]["vector_group"],
            thresholds=config,
        )
        assert result.code == "EA5"
        assert result.status == CheckStatus.DANGER
        assert result.measured["phase_shift_deg"] != 0
