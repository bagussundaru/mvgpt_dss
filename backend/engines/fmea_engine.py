"""
FMEA Matrix Engine.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 63–65).

Enforces:
- 4-row structure (F-M-E-A, p. 65)
- 6 critical components (>85% transformer failures, p. 63)
- RPN = Severity * Occurrence * Detection (AIAG 1-10 assumption)
- Hidden failure consistency: hidden failure MUST have scheduled engineering testing task
- Table 3.1 test methods with naskah reference as primary and reference_note as correction
"""

from backend.schemas.fmea_schemas import (
    FMEAMatrix,
    FMEARow,
    RowA_Analysis,
    RowE_FailureEffect,
    RowF_ComponentFunction,
    RowM_FailureMode,
)


class FMEAEngine:
    """FMEA matrix computation and validation engine."""

    def calculate_rpn(self, severity: int, occurrence: int, detection: int) -> int:
        """
        Calculate Risk Priority Number.
        RPN = Severity * Occurrence * Detection.
        All inputs must be within [1, 10]. Range: [1, 1000].
        """
        if not (1 <= severity <= 10):
            raise ValueError(f"Severity harus antara 1 dan 10, diterima: {severity}")
        if not (1 <= occurrence <= 10):
            raise ValueError(f"Occurrence harus antara 1 dan 10, diterima: {occurrence}")
        if not (1 <= detection <= 10):
            raise ValueError(f"Detection harus antara 1 dan 10, diterima: {detection}")
        return severity * occurrence * detection

    def validate_row_consistency(self, row: FMEARow) -> bool:
        """
        Check if row satisfies the methodological rule:
        Hidden failure MUST have a scheduled engineering testing task and test method.
        """
        if row.row_a.hidden_or_evident == "HIDDEN":
            if not row.row_a.engineering_task or not row.row_a.engineering_task.strip():
                return False
            if not row.row_a.test_method or not row.row_a.test_method.strip():
                return False
        return True

    def get_default_matrix(self) -> FMEAMatrix:
        """
        Build the default 4-row FMEA matrix for the 6 critical MV transformer components.
        Covers >85% failure causes per dissertation p.63.
        """
        rows = [
            FMEARow(
                id="FMEA-OLTC-01",
                row_f=RowF_ComponentFunction(
                    component_id="oltc",
                    component_name="OLTC / Tap Changer",
                    nominal_function="Mengatur rasio tegangan belitan secara on-load kontinu",
                    functional_failure="Kontak aus, macet, atau deviasi transisi resistansi",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-OLTC-01",
                    failure_mode="Arcing dan degradasi mekanis kontak selektor",
                    physical_mechanism="Erosi kontak akibat pemutusan arus beban berulang dan kelelahan pegas",
                    root_cause="Jumlah operasi melebihi limit tanpa servis",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Overheating lokal dan gas hidrokarbon dalam kompartemen tap changer",
                    system_effect="Fluktuasi tegangan bus distribusi",
                    end_effect="Gagal tap change berbeban dan potensi trip trafo",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Wear-out mekanis bertahap",
                    hidden_or_evident="HIDDEN",
                    severity=7,
                    occurrence=3,
                    detection=4,
                    rpn=self.calculate_rpn(7, 3, 4),
                    engineering_task="Pengujian waktu transisi kontak (dynamic resistance) dan analisis DGA kompartemen tap changer",
                    test_method="Dynamic Contact Resistance Measurement & DGA",
                    reference_standard="IEC 60214-1",
                    reference_note="Standar on-load tap-changers",
                ),
            ),
            FMEARow(
                id="FMEA-WND-01",
                row_f=RowF_ComponentFunction(
                    component_id="winding",
                    component_name="Belitan (Winding)",
                    nominal_function="Transformasi tegangan dan arus listrik secara elektromagnetik",
                    functional_failure="Hubung singkat antarlilitan (turn-to-turn) atau fasa ke tanah",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-WND-01",
                    failure_mode="Degradasi isolasi kertas dan deformasi mekanis belitan",
                    physical_mechanism="Kelelahan termal kumulatif dan deformasi akibat gaya elektrodinamik hubung singkat",
                    root_cause="Thermal stress berlebih dan arus gangguan eksternal berulang",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Peningkatan rugi tembaga dan arcing internal fasa-fasa",
                    system_effect="Trip proteksi relai diferensial / overcurrent",
                    end_effect="Trafo keluar operasi mendadak (catastrophic winding burnout)",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Wear-out kelelahan termal-mekanis (beta ~ 1.8)",
                    hidden_or_evident="HIDDEN",
                    severity=8,
                    occurrence=2,
                    detection=3,
                    rpn=self.calculate_rpn(8, 2, 3),
                    engineering_task="Pengujian Tan Delta belitan dan Sweep Frequency Response Analysis (SFRA) berkala",
                    test_method="Tan Delta & SFRA",
                    reference_standard="IEC 60076-1 / IEEE C57.152",
                    reference_note="Untuk belitan transformator rujukan lazimnya IEEE C57.152 (dissertation Table 3.1)",
                ),
            ),
            FMEARow(
                id="FMEA-CORE-01",
                row_f=RowF_ComponentFunction(
                    component_id="core",
                    component_name="Inti Besi (Core)",
                    nominal_function="Menyalurkan fluks magnetik dengan rugi histeresis dan arus eddy minimum",
                    functional_failure="Grounding ganda (multiple ground) atau kegagalan insulasi baut pengikat inti",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-CORE-01",
                    failure_mode="Arus sirkulasi eddy berlebih pada laminasi inti",
                    physical_mechanism="Degradasi isolasi antar-laminasi silikon akibat getaran magnetostriksi",
                    root_cause="Penuaan vernis isolasi laminasi dan masuknya partikel konduktif",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Overheating inti lokal dan pembentukan gas thermal DGA",
                    system_effect="Peningkatan no-load loss dan arus eksitasi",
                    end_effect="Pemanasan berlebih tangki trafo dan degradasi oli dipercepat",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Infant mortality / Defect acak (beta ~ 0.9)",
                    hidden_or_evident="HIDDEN",
                    severity=6,
                    occurrence=2,
                    detection=4,
                    rpn=self.calculate_rpn(6, 2, 4),
                    engineering_task="Uji tahanan isolasi inti terhadap ground (Core Insulation Resistance 1 kV) saat shutdown",
                    test_method="Insulation Resistance (Megger 1 kV)",
                    reference_standard="IEC 60060 / IEEE 43",
                    reference_note="IEEE 43 untuk mesin berputar; untuk pengujian inti trafo lazimnya IEEE C57.152",
                ),
            ),
            FMEARow(
                id="FMEA-BSH-01",
                row_f=RowF_ComponentFunction(
                    component_id="bushing",
                    component_name="Bushing",
                    nominal_function="Mengisolasi konduktor tegangan menengah saat menembus dinding tangki",
                    functional_failure="Pecah isolator keramik / breakdown kapasitif internal",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-BSH-01",
                    failure_mode="Partial discharge dan kontaminasi permukaan bushing",
                    physical_mechanism="Infiltrasi uap air lingkungan tropis (>80% RH) ke seal bushing dan penumpukan polutan",
                    root_cause="Kualitas seal gasket menurun dan kelembaban atmosfer tinggi",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Flashover eksternal fasa ke ground",
                    system_effect="Trip proteksi busbar MV",
                    end_effect="Peledakan porselen bushing dan pemadaman penyulang",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Infant mortality / Defect instalasi (beta ~ 0.8)",
                    hidden_or_evident="HIDDEN",
                    severity=8,
                    occurrence=3,
                    detection=3,
                    rpn=self.calculate_rpn(8, 3, 3),
                    engineering_task="Pengujian Tan Delta bushing C1/C2 dan pengukuran Partial Discharge berkala",
                    test_method="Partial Discharge (pC) & Tan Delta",
                    reference_standard="IEC 60270",
                    reference_note="IEC 60270 sesuai untuk partial discharge, dikombinasikan dengan C57.152",
                ),
            ),
            FMEARow(
                id="FMEA-COOL-01",
                row_f=RowF_ComponentFunction(
                    component_id="cooling",
                    component_name="Sistem Pendingin",
                    nominal_function="Membuang panas Joule belitan dan inti ke atmosfer agar suhu operasi di bawah batas IEEE C57.91",
                    functional_failure="Kapasitas pelepasan panas berkurang drastis",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-COOL-01",
                    failure_mode="Sirkulasi terhambat atau kegagalan motor fan pendingin",
                    physical_mechanism="Penyumbatan debu/korosi pada fin radiator dan trip motor kipas ONAF/OFAF",
                    root_cause="Korosi lingkungan atmosfer lembab dan keausan bearing fan",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Suhu top-oil dan winding hotspot melebihi batas 110 °C",
                    system_effect="Peningkatan laju degradasi isolasi kertas (+7 °C => +30% aging)",
                    end_effect="Pelemahan dielektrik dini dan potensi trip over-temperature",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Random failure (beta ~ 1.0)",
                    hidden_or_evident="EVIDENT",
                    severity=7,
                    occurrence=4,
                    detection=3,
                    rpn=self.calculate_rpn(7, 4, 3),
                    engineering_task="Inspeksi operasional fan berkala, pembersihan sirip pendingin, dan monitoring termografi",
                    test_method="Thermovision",
                    reference_standard="IEEE C57.91 / Engineering practice",
                    reference_note="Evaluasi hotspot berdasarkan EA3",
                ),
            ),
            FMEARow(
                id="FMEA-INS-01",
                row_f=RowF_ComponentFunction(
                    component_id="insulation",
                    component_name="Sistem Isolasi",
                    nominal_function="Menjaga kekuatan dielektrik fluida ester dan kertas isolasi terhadap medan listrik tegangan menengah",
                    functional_failure="Dielectric breakdown pada cairan isolasi ester",
                ),
                row_m=RowM_FailureMode(
                    failure_mode_id="FM-INS-01",
                    failure_mode="Degradasi fluida pendingin hijau dan kertas isolasi",
                    physical_mechanism="Oksidasi termal dan hidrolisis ester yang dipercepat oleh kelembaban tropis >80% RH",
                    root_cause="Kondisi tropis Indonesia dengan RH tinggi memicu pembentukan asam dan air",
                ),
                row_e=RowE_FailureEffect(
                    local_effect="Penurunan tegangan tembus cairan dan pembentukan gas terlarut C2H2",
                    system_effect="Penurunan margin isolasi sistem proteksi transformator",
                    end_effect="Risiko kebakaran dan busur api internal fatal (EA1)",
                ),
                row_a=RowA_Analysis(
                    failure_characteristic="Aging penuaan jelas terkait umur (beta ~ 2.2)",
                    hidden_or_evident="HIDDEN",
                    severity=9,
                    occurrence=3,
                    detection=3,
                    rpn=self.calculate_rpn(9, 3, 3),
                    engineering_task="Pengambilan sampel fluida untuk DGA berkala, uji kelembaban ppm, dan Insulation Resistance (Megger/PI/DAR)",
                    test_method="DGA & Insulation Resistance (Megger)",
                    reference_standard="IEC 60060 / IEEE 43 / IEC 60599",
                    reference_note="Tabel 3.1 naskah merujuk IEC 60060/IEEE 43; untuk trafo lazimnya IEEE C57.152 dan ester IEEE C57.155",
                ),
            ),
        ]
        return FMEAMatrix(rows=rows)
