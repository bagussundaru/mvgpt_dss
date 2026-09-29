"""
Unit tests for FMEA Matrix Engine.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 63-65).
"""

import pytest
from backend.engines.fmea_engine import FMEAEngine
from backend.schemas.fmea_schemas import (
    FMEARow,
    RowF_ComponentFunction,
    RowM_FailureMode,
    RowE_FailureEffect,
    RowA_Analysis,
)


@pytest.fixture
def fmea_engine():
    return FMEAEngine()


class TestFMEAMatrixEngine:
    """Uji FMEA Matrix 4-baris (F-M-E-A), RPN, dan konsistensi hidden/evident."""

    def test_rpn_calculation(self, fmea_engine):
        # RPN = S * O * D
        rpn = fmea_engine.calculate_rpn(severity=8, occurrence=4, detection=3)
        assert rpn == 96

    def test_rpn_bounds(self, fmea_engine):
        with pytest.raises(ValueError):
            fmea_engine.calculate_rpn(severity=11, occurrence=5, detection=5)
        with pytest.raises(ValueError):
            fmea_engine.calculate_rpn(severity=5, occurrence=0, detection=5)

    def test_hidden_failure_consistency_check(self, fmea_engine):
        # Hidden failure WAJIB punya test_method & engineering_task
        valid_hidden_row = FMEARow(
            id="FMEA-INS-01",
            row_f=RowF_ComponentFunction(
                component_id="insulation",
                component_name="Sistem Isolasi",
                nominal_function="Menahan tegangan kerja dan tegangan impuls",
                functional_failure="Penurunan nilai tahanan isolasi di bawah standar",
            ),
            row_m=RowM_FailureMode(
                failure_mode_id="FM-INS-01",
                failure_mode="Degradasi minyak ester & kertas",
                physical_mechanism="Oksidasi termal dan absorpsi kelembaban",
                root_cause="Kelembaban tropis >80% RH dan suhu operasi tinggi",
            ),
            row_e=RowE_FailureEffect(
                local_effect="Dielectric breakdown parsial",
                system_effect="Alarm gas / penurunan resistansi",
                end_effect="Trip transformator tidak terduga",
            ),
            row_a=RowA_Analysis(
                failure_characteristic="Random / Aging",
                hidden_or_evident="HIDDEN",
                severity=8,
                occurrence=3,
                detection=4,
                rpn=96,
                engineering_task="Pengujian Insulation Resistance dan Polarization Index terjadwal",
                test_method="Insulation Resistance (Megger)",
                reference_standard="IEC 60060 / IEEE 43",
                reference_note="IEEE 43 adalah standar mesin berputar; untuk trafo lazimnya IEEE C57.152",
            ),
        )

        assert fmea_engine.validate_row_consistency(valid_hidden_row) is True

        # Inconsistent hidden failure: tidak punya task pengujian
        inconsistent_hidden_row = valid_hidden_row.model_copy(deep=True)
        inconsistent_hidden_row.row_a.test_method = None
        inconsistent_hidden_row.row_a.engineering_task = ""
        assert fmea_engine.validate_row_consistency(inconsistent_hidden_row) is False

    def test_six_critical_components_coverage(self, fmea_engine):
        # Dissertation p.63: enam komponen kritis (>85% kegagalan)
        # OLTC, winding, core, bushing, cooling, insulation
        matrix = fmea_engine.get_default_matrix()
        comp_ids = {row.row_f.component_id for row in matrix.rows}
        expected = {"oltc", "winding", "core", "bushing", "cooling", "insulation"}
        assert expected.issubset(comp_ids)

    def test_table_3_1_reference_notes_retained(self, fmea_engine):
        # Tabel 3.1 naskah: rujukan asli tetap jadi nilai utama, koreksi di reference_note
        matrix = fmea_engine.get_default_matrix()
        insulation_rows = [r for r in matrix.rows if r.row_f.component_id == "insulation"]
        assert len(insulation_rows) > 0
        row = insulation_rows[0]
        assert "IEC 60060" in row.row_a.reference_standard or "IEEE 43" in row.row_a.reference_standard
        assert row.row_a.reference_note is not None
        assert "IEEE C57.152" in row.row_a.reference_note
