"""
MV-GPT DSS — Integrated RAM-FMEA Decision Support System Dashboard.
Prototype for Medium Voltage Green Power Transformer (1–35 kV).
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (UNY).

Language rule: All UI strings and explanations are in Bahasa Indonesia.
Data source: config/thresholds.yaml via backend.config_loader.
"""

import sys
from pathlib import Path
import json
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is in sys.path for Streamlit Cloud execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.config_loader import load_thresholds
from backend.engines.fmea_engine import FMEAEngine
from backend.engines.ram_engine import RAMEngine
from backend.schemas.common import CheckStatus
from backend.services.decision_service import DecisionService


st.set_page_config(
    page_title="MV-GPT DSS — Transformer Reliability & Safety",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "dummy_transformers.json"
    truth_path = base_dir / "data" / "dummy_transformers_truth.json"

    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    with open(truth_path, "r", encoding="utf-8") as f:
        truth = json.load(f)

    return dataset, truth


def render_ea_badge(code: str, title: str, result):
    """Render deterministic Electrical Accident badge with status color."""
    color_map = {
        CheckStatus.SAFE: ("#10b981", "#ecfdf5", "AMAN"),
        CheckStatus.WARNING: ("#f59e0b", "#fffbeb", "PERINGATAN"),
        CheckStatus.DANGER: ("#ef4444", "#fef2f2", "BAHAYA"),
        CheckStatus.INSUFFICIENT_DATA: ("#6b7280", "#f3f4f6", "DATA KURANG"),
    }
    border_col, bg_col, label_text = color_map.get(
        result.status, ("#6b7280", "#f3f4f6", "DATA KURANG")
    )

    st.markdown(
        f"""
        <div style="border: 2px solid {border_col}; background-color: {bg_col}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; font-size: 1.05rem; color: #1f2937;">{code}: {title}</span>
                <span style="background-color: {border_col}; color: white; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">
                    {label_text}
                </span>
            </div>
            <p style="margin: 8px 0 4px 0; font-size: 0.9rem; color: #374151;">{result.explanation_id}</p>
            <div style="font-size: 0.75rem; color: #6b7280; border-top: 1px dashed {border_col}; padding-top: 4px; margin-top: 6px;">
                <strong>Rujukan:</strong> {result.reference}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def create_availability_gauge(availability_pct: float, target_pct: float = 99.0):
    """Render Availability Gauge with renewable benchmark."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=availability_pct,
            delta={"reference": target_pct, "increasing": {"color": "#10b981"}},
            number={"suffix": "%", "valueformat": ".2f"},
            title={"text": "<b>Operational Availability (A)</b><br><span style='font-size:0.8em;color:gray'>Target EBT > 99.0% (Naskah hal. 24)</span>"},
            gauge={
                "axis": {"range": [95.0, 100.0], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "#2563eb"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [95.0, 98.0], "color": "#fee2e2"},
                    {"range": [98.0, 99.0], "color": "#fef3c7"},
                    {"range": [99.0, 100.0], "color": "#dcfce7"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.8,
                    "value": target_pct,
                },
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def create_reliability_curve(ram_engine: RAMEngine, ttf_list: list[float], censored_list: list[float]):
    """Render Weibull Reliability Curve with confidence band."""
    fit = ram_engine.fit_weibull(ttf=ttf_list, censored=censored_list)
    t_vals = np.linspace(100, 87600, 200)

    # R(t) = exp(-(t/eta)^beta)
    r_est = np.exp(-((t_vals / fit.eta) ** fit.beta))
    r_lower = np.exp(-((t_vals / fit.eta_ci[0]) ** fit.beta_ci[1]))
    r_upper = np.exp(-((t_vals / fit.eta_ci[1]) ** fit.beta_ci[0]))

    fig = go.Figure()

    # Confidence band
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([t_vals, t_vals[::-1]]),
            y=np.concatenate([r_upper, r_lower[::-1]]),
            fill="toself",
            fillcolor="rgba(59, 130, 246, 0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="95% Confidence Band",
        )
    )

    # Main reliability curve
    fig.add_trace(
        go.Scatter(
            x=t_vals,
            y=r_est,
            mode="lines",
            name=f"Weibull Fit (β={fit.beta:.2f}, η={fit.eta:.0f} jam)",
            line=dict(color="#1d4ed8", width=3),
        )
    )

    # 75% target reliability line (switchgear example p.28)
    fig.add_hline(
        y=0.75,
        line_dash="dot",
        line_color="#ef4444",
        annotation_text="Target R = 75% (Naskah hal. 28)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=f"<b>Kurva Keandalan Weibull R(t)</b> (MTBF={fit.mtbf:.0f} jam)",
        xaxis_title="Waktu Operasi t (Jam)",
        yaxis_title="Probabilitas Keandalan R(t)",
        yaxis=dict(range=[0, 1.05]),
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig, fit


def main():
    config = load_thresholds()
    decision_service = DecisionService(config=config)
    dataset, truth = load_data()

    # Header
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #1e3a8a 0%, #047857 100%); padding: 18px 24px; border-radius: 10px; color: white; margin-bottom: 20px;">
            <h1 style="margin:0; font-size: 1.8rem;">MV-GPT DSS — Integrated RAM-FMEA Decision Support System</h1>
            <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 0.95rem;">
                Sistem Pendukung Keputusan untuk Transformator Daya Ramah Lingkungan Tegangan Menengah (1–35 kV)<br>
                <em>Rujukan Metodologi: Proposal Disertasi Bab I–III (Rev3) — Prabowo Soetadji (UNY)</em>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar: Controls & Selector
    st.sidebar.header("⚙️ Konfigurasi & Pemilihan Unit")

    units = dataset["transformers"]
    unit_ids = [u["transformer_id"] for u in units]

    selected_unit_id = st.sidebar.selectbox(
        "Pilih Transformator Unit:",
        options=unit_ids,
        index=0,
        help="Pilih salah satu dari 30 unit transformator populasi dummy.",
    )

    selected_unit = next(u for u in units if u["transformer_id"] == selected_unit_id)

    # Check if unit belongs to parallel pairs
    parallel_pairs = dataset.get("parallel_pairs", [])
    companion_unit = None
    for p in parallel_pairs:
        if p["unit_a_id"] == selected_unit_id:
            companion_unit = next((u for u in units if u["transformer_id"] == p["unit_b_id"]), None)
            st.sidebar.info(f"Unit ini terpasang paralel dengan {p['unit_b_id']} ({p.get('description', '')}).")
            break
        elif p["unit_b_id"] == selected_unit_id:
            companion_unit = next((u for u in units if u["transformer_id"] == p["unit_a_id"]), None)
            st.sidebar.info(f"Unit ini terpasang paralel dengan {p['unit_a_id']} ({p.get('description', '')}).")
            break

    target_r = st.sidebar.slider(
        "Target Keandalan (Target R):",
        min_value=0.50,
        max_value=0.95,
        value=0.75,
        step=0.05,
        help="Target reliability input pengguna (Contoh switchgear naskah hal. 28 memakai R=0.75).",
    )

    t_eval = st.sidebar.slider(
        "Waktu Evaluasi Interval t (Bulan):",
        min_value=1.0,
        max_value=12.0,
        value=5.0,
        step=0.5,
        help="Waktu evaluasi interval pemeliharaan (Contoh switchgear naskah hal. 28 memakai t=5 bulan).",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        **Scope Sistem:** {config.meta.scope_kv.min:.0f}–{config.meta.scope_kv.max:.0f} kV  
        **Basis 1 Bulan:** {config.meta.hours_per_month.value:.0f} jam *(Dissertation Conv.)*  
        **Batas RH Tropis:** {config.environment.tropical_rh_threshold.value:.0f}% RH *(Hal. 61)*  
        **Target Availability:** {config.ram.target_availability.value:.1f}% *(Hal. 24)*
        """
    )

    # Generate Decision Plan
    plan = decision_service.generate_plan(
        unit_data=selected_unit,
        companion_unit_data=companion_unit,
        target_reliability=target_r,
        t_eval_months=t_eval,
    )

    # Nameplate & Operating Condition Bar
    np_data = selected_unit["nameplate"]
    op_data = selected_unit["operating_condition"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Kapasitas Terpasang", f"{np_data['rated_kva']:.0f} kVA", help="IEC 60076 Nameplate")
    c2.metric("Tegangan Kerja", f"{np_data['primary_kv']:.1f} / {np_data['secondary_kv']:.1f} kV", help="Rentang 1-35 kV (Hal. 17-18)")
    c3.metric("Beban Saat Ini", f"{op_data['load_kva']:.0f} kVA ({op_data['load_kva']/np_data['rated_kva']*100:.1f}%)")
    c4.metric("Fluida Pendingin", np_data['fluid_type'].replace('_', ' ').title(), f"FP: {np_data['flash_point_c']} °C")
    c5.metric("Suhu & Kelembaban", f"{op_data['ambient_temp_c']:.1f} °C / {op_data['ambient_rh_pct']:.1f}% RH", delta=f"{op_data['ambient_rh_pct']-80:.1f}% RH vs ambang", delta_color="inverse")

    # Main Tabs
    tab_actions, tab_safety, tab_ram, tab_fmea, tab_methodology = st.tabs([
        "📋 Engineering Actions",
        "🚨 Electrical Accidents (EA1–EA5)",
        "📈 RAM & Keandalan",
        "📑 Matriks FMEA 4-Baris",
        "📚 Metodologi & Rujukan Naskah",
    ])

    # -------------------------------------------------------------
    # TAB 1: Engineering Actions (Core Deliverable)
    # -------------------------------------------------------------
    with tab_actions:
        st.subheader("🎯 Rekomendasi Engineering Actions Terintegrasi")
        st.caption(
            "Engineering Action = Engineering Task (dari FMEA, Baris A) + Engineering Frequency (dari RAM, Persamaan 2.2). "
            "Urutan prioritas: Status EA DANGER terdahulu, kemudian RPN tertinggi, lalu interval pemeliharaan terpendek."
        )

        if plan.actions:
            action_rows = []
            for act in plan.actions:
                status_icon = "🔴 BAHAYA" if act.ea_risk_status == CheckStatus.DANGER else ("🟡 PERINGATAN" if act.ea_risk_status == CheckStatus.WARNING else "🟢 NORMAL")
                action_rows.append({
                    "Prioritas": f"#{act.priority_rank}",
                    "Status Risiko EA": status_icon,
                    "Komponen": act.component_name,
                    "RPN": act.rpn,
                    "Engineering Task (FMEA)": act.task_description,
                    "Metode Uji": act.test_method or "-",
                    "Frekuensi Pemeliharaan": f"Setiap {act.interval_months} bulan ({act.interval_hours:.0f} jam)",
                    "Standar Rujukan": act.reference_standard,
                    "Catatan Koreksi": act.reference_note or "-",
                })
            st.dataframe(action_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("Belum ada tindakan rekayasa yang terjadwal.")

        if plan.unscheduled_tasks:
            st.markdown("#### ⏳ Tugas Rekayasa Belum Terjadwal (Unscheduled Tasks)")
            st.caption("Tugas pengujian FMEA yang belum memiliki frekuensi pasti karena data historis kegagalan belum memadai.")
            unscheduled_rows = [
                {
                    "Komponen": ut.component_name,
                    "Tugas Pengujian": ut.task_description,
                    "Alasan Belum Terjadwal": ut.reason,
                }
                for ut in plan.unscheduled_tasks
            ]
            st.dataframe(unscheduled_rows, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------
    # TAB 2: Electrical Accidents (EA1-EA5)
    # -------------------------------------------------------------
    with tab_safety:
        st.subheader("🛡️ Hasil Verifikasi 5 Electrical Accidents (Hal. 6 & 16-17)")
        st.caption("Pemeriksaan deterministik tanpa heuristik. Hijau palsu dilarang; data kurang ditampilkan sebagai abu-abu.")

        ea_meta = [
            ("EA1", "Kebakaran akibat Flash Point Cairan Pendingin Rendah & DGA C2H2", plan.ea_results.get("EA1")),
            ("EA2", "Ledakan MV Circuit Breaker / Fuse (IR < Isc)", plan.ea_results.get("EA2")),
            ("EA3", "Kebakaran akibat Pemilihan Tipe Pendinginan yang Tidak Tepat", plan.ea_results.get("EA3")),
            ("EA4", "Kerusakan Operasi Paralel: Ketidaksesuaian Impedansi (%Z)", plan.ea_results.get("EA4")),
            ("EA5", "Kerusakan Operasi Paralel: Ketidaksesuaian Vector Group", plan.ea_results.get("EA5")),
        ]

        for code, title, res in ea_meta:
            if res:
                render_ea_badge(code, title, res)
            else:
                st.info(f"**{code}: {title}** — Tidak diterapkan (hanya relevan pada operasi paralel dua unit).")

    # -------------------------------------------------------------
    # TAB 3: RAM & Availability
    # -------------------------------------------------------------
    with tab_ram:
        st.subheader("📊 Analisis Keandalan, Ketersediaan & Pemeliharaan (RAM)")
        r_col1, r_col2 = st.columns([1, 1])

        with r_col1:
            gauge_fig = create_availability_gauge(plan.system_availability, target_pct=config.ram.target_availability.value)
            st.plotly_chart(gauge_fig, use_container_width=True)

        with r_col2:
            st.markdown("#### Formula RAM Kunci (Bab II, hal. 23–24)")
            st.markdown(
                f"""
                - **Reliability Eksponensial:** $R(t) = e^{{-\\lambda t}} = e^{{-t/\\text{{MTBF}}}}$ *(Persamaan 2.1)*
                - **Interval Pemeliharaan:** $\\text{{MTBF}} = \\frac{{t}}{{\\ln(1 / R(t))}}$ *(Persamaan 2.2)*
                - **Operational Availability:** $A = \\frac{{\\text{{MTBF}}}}{{\\text{{MTBF}} + \\text{{MTTR}}}}$ *(Persamaan 2.3)*
                - **Weibull Multi-Fase:** $R(t) = e^{{-(t/\\eta)^\\beta}}$ *(Persamaan 2.5)*
                - **Contoh Naskah Switchgear 20 kV (hal. 28-29):** Target $R=75\\%$ pada $t=5$ bulan $\\to$ $\\text{{MTBF}}=17,38$ bulan dibulatkan konservatif menjadi **18 bulan**, $A=99,63\\%$.
                """
            )

        # Plot Weibull curve for population
        st.markdown("---")
        st.markdown("#### Kurva Reliability Populasi untuk Komponen Kritis")
        comp_choice = st.selectbox(
            "Pilih Komponen untuk Kurva Weibull:",
            options=list(truth["components_truth"].keys()),
            format_func=lambda x: f"{x.upper()} (True β={truth['components_truth'][x]['beta']})",
        )

        samples = truth["component_samples"][comp_choice]
        curve_fig, fit_res = create_reliability_curve(
            decision_service.ram_engine,
            ttf_list=samples["failures"],
            censored_list=samples["censored"],
        )
        st.plotly_chart(curve_fig, use_container_width=True)

        if not fit_res.is_exponential_valid:
            st.warning(f"⚠️ **Validasi Kurva Bathtub:** {fit_res.warning}")
        else:
            st.success("✅ **Validasi Asumsi:** Parameter β berada dalam rentang fase random failure (0.9–1.1). Asumsi λ konstan Persamaan (2.1) valid.")

    # -------------------------------------------------------------
    # TAB 4: FMEA Matrix (4 Rows)
    # -------------------------------------------------------------
    with tab_fmea:
        st.subheader("📑 Matriks FMEA Empat Baris (Naskah hal. 65)")
        st.caption(
            "Struktur baku F-M-E-A sesuai proposal disertasi. Severity, Occurrence, dan Detection memakai skala AIAG 1–10 "
            "sebagai asumsi implementasi (diberi tanda jelas menunggu konfirmasi Bab IV)."
        )

        default_matrix = decision_service.fmea_engine.get_default_matrix()
        for idx, row in enumerate(default_matrix.rows, start=1):
            with st.expander(f"Komponen {idx}: {row.row_f.component_name} — RPN: {row.row_a.rpn} ({row.row_a.hidden_or_evident})", expanded=(idx == 1)):
                col_f, col_m = st.columns(2)
                with col_f:
                    st.markdown("**Baris F — Components & Function**")
                    st.markdown(f"- **Fungsi Nominal:** {row.row_f.nominal_function}")
                    st.markdown(f"- **Functional Failure:** {row.row_f.functional_failure}")
                with col_m:
                    st.markdown("**Baris M — Failure Mode & Mechanism**")
                    st.markdown(f"- **Failure Mode:** {row.row_m.failure_mode}")
                    st.markdown(f"- **Mekanisme Fisik:** {row.row_m.physical_mechanism}")
                    st.markdown(f"- **Root Cause:** {row.row_m.root_cause}")

                st.markdown("---")
                col_e, col_a = st.columns(2)
                with col_e:
                    st.markdown("**Baris E — Failure Effect**")
                    st.markdown(f"- **Local Effect:** {row.row_e.local_effect}")
                    st.markdown(f"- **System Effect:** {row.row_e.system_effect}")
                    st.markdown(f"- **End Effect:** {row.row_e.end_effect}")
                with col_a:
                    st.markdown("**Baris A — Analysis & Engineering Tasks**")
                    st.markdown(f"- **Karakteristik:** {row.row_a.failure_characteristic}")
                    st.markdown(f"- **Klasifikasi:** `{row.row_a.hidden_or_evident}`")
                    st.markdown(f"- **RPN:** {row.row_a.rpn} *(S={row.row_a.severity}, O={row.row_a.occurrence}, D={row.row_a.detection})*")
                    st.markdown(f"- **Engineering Task:** {row.row_a.engineering_task}")
                    st.markdown(f"- **Metode Uji (Tabel 3.1):** `{row.row_a.test_method}`")
                    st.markdown(f"- **Rujukan Naskah:** {row.row_a.reference_standard}")
                    if row.row_a.reference_note:
                        st.info(f"💡 **Catatan Koreksi Standar:** {row.row_a.reference_note}")

    # -------------------------------------------------------------
    # TAB 5: Methodology & Defense Audit (Sesi 5 Ready)
    # -------------------------------------------------------------
    with tab_methodology:
        st.subheader("📚 Pemetaan Metodologis ke Naskah Disertasi (Persiapan Sidang)")
        st.caption("Pemeriksaan ketertelusuran ilmiah untuk promotor dan dewan penguji.")

        st.markdown(
            """
            | Komponen Sistem | Rujukan Naskah Disertasi | Keterangan & Status Implementasi |
            |---|---|---|
            | **Persamaan RAM (2.1)–(2.5)** | Bab II, hal. 23–24 | Diimplementasikan murni di `backend/engines/ram_engine.py`. |
            | **Fixture Uji Busi 250 jam** | Bab II, hal. 27–28 | $R(50)=81,87\\%$, $R(130)=59,45\\%$, $F(130)=40,55\\%$ lolos uji unit. |
            | **Fixture Switchgear 20 kV** | Bab II, hal. 28–29 | $\\text{MTBF}=17,38$ bulan dibulatkan ke atas menjadi 18 bulan, $A=99,63\\%$. |
            | **Lima Electrical Accidents** | Bab I hal. 6 & Bab II hal. 16, 46 | 5 fungsi deterministik di `backend/safety/ea_checker.py`. |
            | **EA 1 (DGA Asetilena > 5 ppm)** | Bab II, hal. 16 | Martin et al. 2023 & Ahmad et al. 2025. Ambang C2H2 = 5 ppm. |
            | **EA 2 (IR 16 kA vs Isc 20 kA)** | Bab II, hal. 16 | Gaya >100 kN/m, energi >50 MJ. Evaluasi 3 tingkat (DANGER/WARNING/SAFE). |
            | **EA 3 (+7 °C => +30% aging)** | Bab II, hal. 16 & 44 | Diimplementasikan sebagai *Aging Acceleration Factor*, bukan sekadar lolos/gagal. |
            | **EA 4 (Selisih %Z > 10%)** | Bab II, hal. 17 | Selisih relatif $\\frac{\\|Za-Zb\\|}{\\text{mean}} > 10\\%$ memicu arus sirkulasi. |
            | **EA 5 (Vector Group Mismatch)** | Bab II, hal. 17 | Operasi beda fasa (beda jam $\\neq 0$) biner DANGER tanpa warning. |
            | **Struktur 4-Baris FMEA** | Bab III, hal. 65 | Baris F, M, E, A dimodelkan terpisah pada skema Pydantic. |
            | **Enam Komponen Kritis** | Bab III, hal. 63 | OLTC, winding, core, bushing, cooling, insulation (>85% kegagalan trafo). |
            | **Koreksi Tabel 3.1 Naskah** | Bab III, hal. 63 | Rujukan naskah tetap nilai utama; koreksi IEEE C57.152/IEC 60270 dicatat di `reference_note`. |
            """
        )

        st.markdown("---")
        st.markdown("#### Unduh Laporan Engineering Action Plan")
        plan_json = plan.model_dump_json(indent=2)
        st.download_button(
            label="📥 Unduh Action Plan (JSON)",
            data=plan_json,
            file_name=f"ActionPlan_{selected_unit_id}.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
