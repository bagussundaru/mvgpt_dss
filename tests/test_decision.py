"""
Unit tests for Decision Service.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3.
Verifies synthesis of RAM (Frequency), FMEA (Task), and EA Safety checks.
"""

from pathlib import Path
import json
import pytest

from backend.config_loader import load_thresholds
from backend.services.decision_service import DecisionService
from backend.schemas.common import CheckStatus


@pytest.fixture
def config():
    return load_thresholds()


@pytest.fixture
def dummy_dataset():
    base_dir = Path(__file__).resolve().parent.parent
    data_file = base_dir / "data" / "dummy_transformers.json"
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def decision_service(config):
    return DecisionService(config=config)


class TestDecisionService:
    """Verifikasi orchestrator DecisionService dan EngineeringActionPlan."""

    def test_plan_generation_basic(self, decision_service, dummy_dataset):
        # Pilih unit normal TX-01
        tx01 = next(u for u in dummy_dataset["transformers"] if u["transformer_id"] == "TX-01")
        plan = decision_service.generate_plan(tx01)

        assert plan.transformer_id == "TX-01"
        assert len(plan.actions) > 0
        assert "EA1" in plan.ea_results
        assert "EA2" in plan.ea_results
        assert "EA3" in plan.ea_results

        # Setiap action wajib memuat task dan frequency
        for act in plan.actions:
            assert act.task_description
            assert act.interval_months > 0
            assert act.interval_hours > 0

    def test_priority_ordering_rules(self, decision_service, dummy_dataset):
        # Unit TX-11 memicu EA1 DANGER (C2H2 = 7 ppm) yang terkait dengan sistem isolasi
        tx11 = next(u for u in dummy_dataset["transformers"] if u["transformer_id"] == "TX-11")
        plan = decision_service.generate_plan(tx11)

        assert plan.overall_safety_status == CheckStatus.DANGER

        # Aksi dengan status DANGER harus berada di paling atas
        first_action = plan.actions[0]
        assert first_action.ea_risk_status == CheckStatus.DANGER
        assert first_action.component_id == "insulation"

        # Verifikasi urutan umum: DANGER dulu, lalu RPN tinggi, lalu interval pendek
        for i in range(len(plan.actions) - 1):
            curr = plan.actions[i]
            nxt = plan.actions[i + 1]

            # Jika tingkat risiko EA berbeda
            if curr.ea_risk_status == CheckStatus.DANGER and nxt.ea_risk_status != CheckStatus.DANGER:
                continue  # Sesuai: DANGER mendahului non-DANGER

            # Jika tingkat risiko sama, bandingkan RPN
            if curr.ea_risk_status == nxt.ea_risk_status:
                if curr.rpn != nxt.rpn:
                    assert curr.rpn >= nxt.rpn
                else:
                    # Jika RPN sama, interval terpendek lebih dulu
                    assert curr.interval_months <= nxt.interval_months

    def test_unscheduled_tasks_handling(self, decision_service, dummy_dataset):
        # Salin unit TX-01 dan kosongkan riwayat kegagalan komponen 'core'
        tx_custom = json.loads(json.dumps(dummy_dataset["transformers"][0]))
        tx_custom["history"]["failures"] = [
            f for f in tx_custom["history"]["failures"] if f["component_id"] != "core"
        ]

        plan = decision_service.generate_plan(tx_custom, require_failure_history=True)

        # Komponen core yang tidak memiliki data kegagalan masuk ke unscheduled_tasks
        unscheduled_components = [t.component_id for t in plan.unscheduled_tasks]
        assert "core" in unscheduled_components
        task = next(t for t in plan.unscheduled_tasks if t.component_id == "core")
        assert "belum mencukupi" in task.reason.lower() or "kegagalan" in task.reason.lower()
