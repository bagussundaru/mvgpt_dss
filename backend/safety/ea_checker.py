"""
EA Safety Checker — Deterministic Safety Rules for Electrical Accidents EA1–EA5.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 6, 16–17, 44, 46).

Deterministic safety verification:
- EA 1: Kebakaran akibat flash point cairan pendingin rendah & DGA asetilena (C2H2)
- EA 2: Ledakan MV circuit breaker / fuse akibat IR < Isc
- EA 3: Kebakaran akibat pemilihan tipe pendinginan tidak tepat (aging acceleration)
- EA 4: Kerusakan operasi paralel: ketidaksesuaian impedansi (%Z)
- EA 5: Kerusakan operasi paralel: ketidaksesuaian vector group

All functions are pure, strictly read thresholds from config/thresholds.yaml,
and return uniform CheckResult schemas.
"""

import math
import re
from typing import Any

from backend.config_loader import ThresholdRegistry, load_thresholds
from backend.schemas.common import CheckResult, CheckStatus


def check_dga_fire_risk(
    c2h2_ppm: float | None,
    fluid_type: str | None,
    flash_point_c: float | None = None,
    thresholds: ThresholdRegistry | None = None,
) -> CheckResult:
    """
    Check fire risk from Dissolved Gas Analysis (C2H2) and fluid flash point.
    Dissertation p.16: C2H2 > 5 ppm indicates severe fire hazard.
    """
    cfg = thresholds or load_thresholds()
    missing: list[str] = []
    if c2h2_ppm is None:
        missing.append("c2h2_ppm")
    if fluid_type is None:
        missing.append("fluid_type")

    if missing:
        return CheckResult(
            code="EA1",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"c2h2_ppm": c2h2_ppm, "fluid_type": fluid_type, "flash_point_c": flash_point_c},
            threshold={},
            explanation_id="Data DGA C2H2 atau jenis cairan tidak lengkap.",
            reference="Dissertation p.16",
            missing_fields=missing,
        )

    fluid_key = fluid_type.lower()
    if fluid_key not in cfg.ea1.c2h2_critical:
        return CheckResult(
            code="EA1",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"fluid_type": fluid_type},
            threshold={},
            explanation_id=f"Jenis cairan '{fluid_type}' tidak dikenali. Pilih mineral, natural_ester, atau synthetic_ester.",
            reference="Dissertation p.16",
            missing_fields=["fluid_type"],
        )

    crit_c2h2 = cfg.ea1.c2h2_critical[fluid_key].value
    crit_fp = cfg.ea1.flash_point_min[fluid_key].value

    measured: dict[str, Any] = {
        "c2h2_ppm": c2h2_ppm,
        "fluid_type": fluid_type,
        "flash_point_c": flash_point_c,
    }
    threshold: dict[str, Any] = {
        "c2h2_critical_ppm": crit_c2h2,
        "flash_point_min_c": crit_fp,
    }

    # C2H2 threshold check
    if c2h2_ppm > crit_c2h2:
        return CheckResult(
            code="EA1",
            status=CheckStatus.DANGER,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Kadar asetilena (C2H2) {c2h2_ppm:.1f} ppm melebihi ambang kritis "
                f"{crit_c2h2:.1f} ppm untuk {fluid_type}. Indikasi busur api internal dan risiko kebakaran tinggi."
            ),
            reference="Dissertation p.16",
        )

    # Flash point check if provided
    if flash_point_c is not None and flash_point_c < crit_fp:
        return CheckResult(
            code="EA1",
            status=CheckStatus.DANGER,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Flash point terukur {flash_point_c:.1f} °C lebih rendah dari standar minimum "
                f"{crit_fp:.1f} °C untuk {fluid_type}. Cairan pendingin rawan terbakar."
            ),
            reference=cfg.ea1.flash_point_min[fluid_key].source,
        )

    return CheckResult(
        code="EA1",
        status=CheckStatus.SAFE,
        measured=measured,
        threshold=threshold,
        explanation_id=(
            f"Kadar C2H2 {c2h2_ppm:.1f} ppm berada di bawah ambang kritis {crit_c2h2:.1f} ppm, "
            f"kondisi isolasi cairan aman dari risiko pelepasan energi termal ekstrem."
        ),
        reference="Dissertation p.16",
    )


def check_breaker_interrupting_capacity(
    ir_ka: float | None,
    isc_ka: float | None,
    thresholds: ThresholdRegistry | None = None,
) -> CheckResult:
    """
    Check MV circuit breaker interrupting rating (IR) against short circuit current (Isc).
    Dissertation p.16: IR 16 kA vs Isc 20 kA causes catastrophic explosion.
    Three-tier evaluation: DANGER, WARNING, SAFE.
    """
    cfg = thresholds or load_thresholds()
    missing: list[str] = []
    if ir_ka is None:
        missing.append("ir_ka")
    if isc_ka is None:
        missing.append("isc_ka")

    if missing:
        return CheckResult(
            code="EA2",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"ir_ka": ir_ka, "isc_ka": isc_ka},
            threshold={},
            explanation_id="Data kapasitas pemutusan breaker (IR) atau arus gangguan (Isc) tidak lengkap.",
            reference="IEC 62271-100 / Dissertation p.16",
            missing_fields=missing,
        )

    margin = cfg.ea2.safety_margin.value
    measured = {"ir_ka": ir_ka, "isc_ka": isc_ka}
    threshold = {"safety_margin_ratio": margin, "ir_required_ka": isc_ka * margin}

    if ir_ka < isc_ka:
        return CheckResult(
            code="EA2",
            status=CheckStatus.DANGER,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"IR {ir_ka:.1f} kA lebih kecil dari Isc {isc_ka:.1f} kA. "
                f"Breaker berisiko meledak saat memutus gangguan hubung singkat (gaya >100 kN/m, energi >50 MJ). "
                f"Isc berkembang seiring ekspansi jaringan sehingga verifikasi IR harus berulang sesuai frekuensi RAM."
            ),
            reference="Dissertation p.16",
        )
    elif isc_ka <= ir_ka < margin * isc_ka:
        return CheckResult(
            code="EA2",
            status=CheckStatus.WARNING,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"IR {ir_ka:.1f} kA melebihi Isc {isc_ka:.1f} kA namun margin keselamatan "
                f"cukup tipis (< {margin:.1f}x Isc = {margin * isc_ka:.1f} kA). "
                f"Periksa potensi kenaikan kapasitas hubung singkat gardu induk."
            ),
            reference="IEC 62271-100",
        )
    else:
        return CheckResult(
            code="EA2",
            status=CheckStatus.SAFE,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"IR {ir_ka:.1f} kA memadai terhadap Isc {isc_ka:.1f} kA "
                f"dengan margin keselamatan di atas {margin:.1f}x."
            ),
            reference="IEC 62271-100",
        )


def check_cooling_adequacy(
    cooling_type: str | None,
    load_kva: float | None,
    rated_kva: float | None,
    ambient_temp_c: float | None,
    thresholds: ThresholdRegistry | None = None,
) -> CheckResult:
    """
    Check cooling adequacy and insulation aging acceleration factor.
    Dissertation p.16: Every +7 °C rise above limit accelerates insulation aging by ~30%.
    """
    cfg = thresholds or load_thresholds()
    missing: list[str] = []
    if cooling_type is None:
        missing.append("cooling_type")
    if load_kva is None:
        missing.append("load_kva")
    if rated_kva is None:
        missing.append("rated_kva")
    if ambient_temp_c is None:
        missing.append("ambient_temp_c")

    if missing:
        return CheckResult(
            code="EA3",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={
                "cooling_type": cooling_type,
                "load_kva": load_kva,
                "rated_kva": rated_kva,
                "ambient_temp_c": ambient_temp_c,
            },
            threshold={},
            explanation_id="Parameter pembebanan atau pendingin tidak lengkap.",
            reference="IEEE C57.91 / Dissertation p.16",
            missing_fields=missing,
        )

    cool_upper = cooling_type.upper()
    if cool_upper not in cfg.ea3.cooling_types:
        return CheckResult(
            code="EA3",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"cooling_type": cooling_type},
            threshold={"valid_cooling_types": cfg.ea3.cooling_types},
            explanation_id=f"Tipe pendinginan '{cooling_type}' tidak dikenal. Pilih {cfg.ea3.cooling_types}.",
            reference="IEEE C57.91",
            missing_fields=["cooling_type"],
        )

    hotspot_max = cfg.ea3.hotspot_absolute_max.value
    hotspot_rise_max = cfg.ea3.hotspot_rise_max.value
    step_temp = cfg.ea3.aging_step_temp.value
    step_factor = cfg.ea3.aging_step_factor.value

    load_ratio = load_kva / rated_kva
    # Hotspot estimate via IEEE C57.91 loading exponent (~1.6)
    delta_hs = hotspot_rise_max * (load_ratio ** 1.6)
    hotspot_est = ambient_temp_c + delta_hs
    excess_temp = max(0.0, hotspot_est - hotspot_max)

    # Aging factor = 1.30 ^ (excess_temp / 7.0) (Dissertation p.16)
    aging_factor = step_factor ** (excess_temp / step_temp)
    life_reduction_pct = (1.0 - (1.0 / aging_factor)) * 100.0

    measured = {
        "cooling_type": cool_upper,
        "load_kva": load_kva,
        "rated_kva": rated_kva,
        "ambient_temp_c": ambient_temp_c,
        "hotspot_estimate_c": round(hotspot_est, 1),
        "excess_temp_c": round(excess_temp, 1),
        "aging_acceleration_factor": round(aging_factor, 2),
        "estimated_life_reduction_pct": round(life_reduction_pct, 1),
    }
    threshold = {
        "hotspot_max_c": hotspot_max,
        "aging_step_temp_k": step_temp,
        "aging_step_factor": step_factor,
    }

    if excess_temp > 14.0 or aging_factor >= 1.69:
        status = CheckStatus.DANGER
        upgrade_rec = " Pertimbangkan upgrade pendingin ke OFAF atau kurangi beban segera." if cool_upper != "OFAF" else ""
        expl = (
            f"Suhu hotspot diperkirakan {hotspot_est:.1f} °C melebihi batas {hotspot_max:.1f} °C "
            f"sebesar {excess_temp:.1f} °C. Laju penuaan isolasi dipercepat {aging_factor:.2f}x "
            f"(kehilangan umur ekonomis ~{life_reduction_pct:.1f}%).{upgrade_rec}"
        )
    elif excess_temp > 0.0:
        status = CheckStatus.WARNING
        upgrade_rec = f" Pertimbangkan transisi dari {cool_upper} ke ONAF/OFAF." if cool_upper == "ONAN" else ""
        expl = (
            f"Suhu hotspot {hotspot_est:.1f} °C melebihi batas {hotspot_max:.1f} °C "
            f"sebesar {excess_temp:.1f} °C. Laju penuaan isolasi meningkat {aging_factor:.2f}x.{upgrade_rec}"
        )
    else:
        status = CheckStatus.SAFE
        expl = (
            f"Suhu hotspot {hotspot_est:.1f} °C berada di bawah batas {hotspot_max:.1f} °C. "
            f"Sistem pendingin {cool_upper} memadai, faktor penuaan normal (1.0x)."
        )

    return CheckResult(
        code="EA3",
        status=status,
        measured=measured,
        threshold=threshold,
        explanation_id=expl,
        reference="Dissertation p.16 / IEEE C57.91",
    )


def check_parallel_impedance(
    z_pct_a: float | None,
    z_pct_b: float | None,
    kva_a: float | None = None,
    kva_b: float | None = None,
    rated_voltage_kv: float | None = None,
    thresholds: ThresholdRegistry | None = None,
) -> CheckResult:
    """
    Check relative impedance matching for parallel transformer operation.
    Dissertation p.17: %Z mismatch causes circulating current and premature aging.
    """
    cfg = thresholds or load_thresholds()
    missing: list[str] = []
    if z_pct_a is None:
        missing.append("z_pct_a")
    if z_pct_b is None:
        missing.append("z_pct_b")

    if missing:
        return CheckResult(
            code="EA4",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"z_pct_a": z_pct_a, "z_pct_b": z_pct_b},
            threshold={},
            explanation_id="Data impedansi trafo A atau B tidak lengkap.",
            reference="Dissertation p.17",
            missing_fields=missing,
        )

    z_mean = (z_pct_a + z_pct_b) / 2.0
    if z_mean <= 0:
        return CheckResult(
            code="EA4",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"z_pct_a": z_pct_a, "z_pct_b": z_pct_b},
            threshold={},
            explanation_id="Nilai rata-rata impedansi harus positif.",
            reference="Dissertation p.17",
            missing_fields=["z_pct_a", "z_pct_b"],
        )

    # Relative difference: abs(Za - Zb) / mean(Za, Zb) * 100%
    rel_diff_pct = (abs(z_pct_a - z_pct_b) / z_mean) * 100.0
    max_diff_pct = cfg.ea4.max_relative_diff_pct.value

    # Circulating current / load unbalance proxy: abs(Za - Zb) / (Za + Zb) * 100%
    circ_pct = (abs(z_pct_a - z_pct_b) / (z_pct_a + z_pct_b)) * 100.0

    measured: dict[str, Any] = {
        "z_pct_a": z_pct_a,
        "z_pct_b": z_pct_b,
        "relative_diff_pct": round(rel_diff_pct, 2),
        "circulating_current_pct": round(circ_pct, 2),
    }
    threshold: dict[str, Any] = {
        "max_relative_diff_pct": max_diff_pct,
    }

    if kva_a and kva_b:
        kva_ratio = max(kva_a / kva_b, kva_b / kva_a)
        measured["kva_ratio"] = round(kva_ratio, 2)
        threshold["max_kva_ratio"] = cfg.ea4.max_kva_ratio.value

    if rel_diff_pct > max_diff_pct:
        return CheckResult(
            code="EA4",
            status=CheckStatus.DANGER,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Selisih relatif impedansi {rel_diff_pct:.1f}% melebihi batas {max_diff_pct:.1f}%. "
                f"Timbul arus sirkulasi beban ~{circ_pct:.1f}% yang memicu overheating dan penuaan dini. "
                f"Paralel dilarang sebelum dilakukan penyesuaian tap changer atau penyeimbangan impedansi."
            ),
            reference="Dissertation p.17",
        )
    elif rel_diff_pct > max_diff_pct * 0.75:
        return CheckResult(
            code="EA4",
            status=CheckStatus.WARNING,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Selisih relatif impedansi {rel_diff_pct:.1f}% mendekati batas {max_diff_pct:.1f}%. "
                f"Terdapat ketidakseimbangan pembagian arus sirkulasi ~{circ_pct:.1f}%."
            ),
            reference="Dissertation p.17",
        )
    else:
        return CheckResult(
            code="EA4",
            status=CheckStatus.SAFE,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Selisih relatif impedansi {rel_diff_pct:.1f}% dalam batas toleransi {max_diff_pct:.1f}%. "
                f"Pembagian beban seimbang untuk operasi paralel."
            ),
            reference="Dissertation p.17",
        )


def check_vector_group_compatibility(
    vector_a: str | None,
    vector_b: str | None,
    thresholds: ThresholdRegistry | None = None,
) -> CheckResult:
    """
    Check vector group compatibility for parallel transformer operation.
    Dissertation p.17: Incompatible vector group causes severe out-of-phase short circuits.
    Pure binary check: DANGER or SAFE (no WARNING).
    """
    cfg = thresholds or load_thresholds()
    missing: list[str] = []
    if not vector_a:
        missing.append("vector_a")
    if not vector_b:
        missing.append("vector_b")

    if missing:
        return CheckResult(
            code="EA5",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"vector_a": vector_a, "vector_b": vector_b},
            threshold={},
            explanation_id="Data vector group trafo A atau B tidak lengkap.",
            reference="Dissertation p.17",
            missing_fields=missing,
        )

    # Parse vector notation: e.g. Dyn11 -> HV='D', LV='yn', clock=11
    pattern = re.compile(r"^([A-Z]+)([a-z]+)(\d{1,2})$")
    match_a = pattern.match(vector_a.strip())
    match_b = pattern.match(vector_b.strip())

    if not match_a or not match_b:
        unparsed = []
        if not match_a:
            unparsed.append("vector_a")
        if not match_b:
            unparsed.append("vector_b")
        return CheckResult(
            code="EA5",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"vector_a": vector_a, "vector_b": vector_b},
            threshold={},
            explanation_id=f"Format vector group {unparsed} tidak valid. Contoh format standar: 'Dyn11', 'Yd1', 'YNd11'.",
            reference="IEC 60076-1 / Dissertation p.17",
            missing_fields=unparsed,
        )

    clock_a = int(match_a.group(3))
    clock_b = int(match_b.group(3))

    if not (0 <= clock_a <= 11 and 0 <= clock_b <= 11):
        return CheckResult(
            code="EA5",
            status=CheckStatus.INSUFFICIENT_DATA,
            measured={"vector_a": vector_a, "vector_b": vector_b},
            threshold={},
            explanation_id="Angka jam vector group harus antara 0 dan 11.",
            reference="IEC 60076-1",
            missing_fields=["vector_a" if not (0 <= clock_a <= 11) else "vector_b"],
        )

    clock_diff = abs(clock_a - clock_b) % 12
    deg_per_clock = cfg.ea5.phase_shift_per_clock.value
    phase_shift_deg = clock_diff * deg_per_clock

    measured = {
        "vector_a": vector_a,
        "vector_b": vector_b,
        "clock_difference": clock_diff,
        "phase_shift_deg": phase_shift_deg,
    }
    threshold = {
        "clock_difference_max": cfg.ea5.tolerance.value,
        "phase_shift_max_deg": 0.0,
    }

    if clock_diff != 0:
        return CheckResult(
            code="EA5",
            status=CheckStatus.DANGER,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Vector group tidak kompatibel: {vector_a} vs {vector_b} berbeda {clock_diff} jam "
                f"({phase_shift_deg}° pergeseran fasa). Risiko short-circuit masif saat paralel! "
                f"Operasi paralel mutlak dilarang."
            ),
            reference="Dissertation p.17",
        )
    else:
        return CheckResult(
            code="EA5",
            status=CheckStatus.SAFE,
            measured=measured,
            threshold=threshold,
            explanation_id=(
                f"Vector group kompatibel: {vector_a} dan {vector_b} sefasa (beda jam 0). "
                f"Aman untuk sinkronisasi paralel."
            ),
            reference="Dissertation p.17",
        )
