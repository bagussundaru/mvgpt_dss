"""
MV-GPT DSS — Integrated RAM-FMEA Decision Support System Dashboard.
Production-grade Engineering Dashboard for Medium Voltage Green Power Transformer (1–35 kV).
Enterprise Asset Intelligence platform integrating RAM & FMEA analytics.

Layout mirrors the modern industrial engineering mock-up:
- Top 3 Floating KPI Telemetry Cards (Current Load, Cooling Fluid Health, Tropical Humidity Alert)
- Hero Stage: Digital Twin Specifications & 3D Transformer Unit Rendering
- Dual Analytics Panels:
  - Left: RAM Reliability Curve R(t) with 95% CI & 99.0% Availability Target
  - Right: Structured FMEA Risk Matrix & Priority Engineering Actions
- Deep-dive Tabs: Full Action Plan, EA1-EA5 Checker, 4-Row FMEA Matrix, Engineering Standards.
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
    page_title="MV-GPT DSS — Enterprise Asset Intelligence",
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
                <span style="font-weight: 700; font-size: 1.02rem; color: #141418;">{code}: {title}</span>
                <span style="background-color: {border_col}; color: white; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">
                    {label_text}
                </span>
            </div>
            <p style="margin: 8px 0 4px 0; font-size: 0.9rem; color: #374151;">{result.explanation_id}</p>
            <div style="font-size: 0.75rem; color: #6b7280; border-top: 1px dashed {border_col}; padding-top: 4px; margin-top: 6px;">
                <strong>Rujukan Standar:</strong> {result.reference}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def create_reliability_curve(ram_engine: RAMEngine, ttf_list: list[float], censored_list: list[float], component_name: str = "Populasi Trafo"):
    """Render Weibull Reliability Curve matching dark-slate dashboard theme."""
    fit = ram_engine.fit_weibull(ttf=ttf_list, censored=censored_list)
    t_vals = np.linspace(100, 87600, 200)

    # R(t) = exp(-(t/eta)^beta)
    r_est = np.exp(-((t_vals / fit.eta) ** fit.beta))
    r_lower = np.exp(-((t_vals / fit.eta_ci[0]) ** fit.beta_ci[1]))
    r_upper = np.exp(-((t_vals / fit.eta_ci[1]) ** fit.beta_ci[0]))

    fig = go.Figure()

    # 95% Confidence Band
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([t_vals, t_vals[::-1]]),
            y=np.concatenate([r_upper, r_lower[::-1]]),
            fill="toself",
            fillcolor="rgba(201, 82, 50, 0.16)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="95% CI Band",
        )
    )

    # Main Weibull Reliability Curve
    fig.add_trace(
        go.Scatter(
            x=t_vals,
            y=r_est,
            mode="lines",
            name=f"Weibull (β={fit.beta:.2f}, η={fit.eta/1000:.0f}k jam)",
            line=dict(color="#C95232", width=3.5),
        )
    )

    # 99.0% Availability Benchmark Line
    fig.add_hline(
        y=0.99,
        line_dash="dash",
        line_color="#10b981",
        annotation_text="99.0% Availability Target",
        annotation_position="top right",
        annotation_font=dict(color="#10b981", size=10),
    )

    # 75% Target Reliability Line
    fig.add_hline(
        y=0.75,
        line_dash="dot",
        line_color="#f59e0b",
        annotation_text="Target R = 75%",
        annotation_position="bottom right",
        annotation_font=dict(color="#f59e0b", size=10),
    )

    fig.update_layout(
        plot_bgcolor="#141418",
        paper_bgcolor="#141418",
        font=dict(color="#E6DDC9", family="sans serif"),
        title=dict(
            text=f"<b>RAM (Reliability, Availability, Maintainability)</b><br><span style='font-size:0.75em;color:#A6A6A4'>{component_name.upper()} &bull; MTBF: {fit.mtbf:,.0f} jam &bull; β: {fit.beta:.2f}</span>",
            font=dict(size=14, color="#E6DDC9"),
        ),
        xaxis=dict(
            title="Waktu Operasi t (Jam)",
            gridcolor="#26262e",
            zerolinecolor="#26262e",
            color="#A6A6A4",
        ),
        yaxis=dict(
            title="Probabilitas Keandalan R(t)",
            range=[0, 1.05],
            gridcolor="#26262e",
            zerolinecolor="#26262e",
            color="#A6A6A4",
        ),
        height=340,
        margin=dict(l=35, r=35, t=55, b=65),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#E6DDC9"),
        ),
    )

    return fig, fit


def main():
    config = load_thresholds()
    decision_service = DecisionService(config=config)
    dataset, truth = load_data()

    # 1. Header (Compact 1-line horizontal card)
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #141418 0%, #1c1b20 50%, #291d19 80%, #C95232 100%); padding: 10px 18px; border-radius: 8px; color: white; margin-bottom: 14px; border-left: 5px solid #C95232; box-shadow: 0 2px 8px rgba(0,0,0,0.12); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 1.15rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.3px;">⚡ MV-GPT DSS</span>
                <span style="font-size: 0.92rem; font-weight: 600; color: #F4EFE6;">— Integrated RAM-FMEA Decision Support System</span>
                <span style="font-size: 0.8rem; color: #A6A6A4;">| Trafo Hijau 1–35 kV</span>
            </div>
            <div style="white-space: nowrap;">
                <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #dcfce7; padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600;">
                    ● Enterprise Asset Intelligence
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Sidebar: Controls & Selector
    st.sidebar.header("⚙️ Parameter & Pemilihan Aset")

    units = dataset["transformers"]
    unit_ids = [u["transformer_id"] for u in units]

    selected_unit_id = st.sidebar.selectbox(
        "Pilih Unit Transformator:",
        options=unit_ids,
        index=0,
        help="Pilih unit trafo 1-35 kV dari armada populasi telemetri.",
    )

    selected_unit = next(u for u in units if u["transformer_id"] == selected_unit_id)

    # Parallel companion detection
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
        help="Target reliability input pengguna (Benchmark IEEE switchgear R=0.75).",
    )

    t_eval = st.sidebar.slider(
        "Waktu Evaluasi Interval t (Bulan):",
        min_value=1.0,
        max_value=12.0,
        value=5.0,
        step=0.5,
        help="Waktu evaluasi interval pemeliharaan (t=5 bulan).",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        **Scope Sistem:** {config.meta.scope_kv.min:.0f}–{config.meta.scope_kv.max:.0f} kV  
        **Basis 1 Bulan:** {config.meta.hours_per_month.value:.0f} jam  
        **Batas Kritis RH:** {config.environment.tropical_rh_threshold.value:.0f}% RH  
        **Target Availability:** {config.ram.target_availability.value:.1f}%  
        """
    )

    # 3. Generate Real Decision Plan
    plan = decision_service.generate_plan(
        unit_data=selected_unit,
        companion_unit_data=companion_unit,
        target_reliability=target_r,
        t_eval_months=t_eval,
    )

    np_data = selected_unit["nameplate"]
    op_data = selected_unit["operating_condition"]
    history = selected_unit.get("history", {})
    failures = history.get("failures", [])

    load_ratio = op_data["load_kva"] / np_data["rated_kva"]
    is_high_rh = op_data["ambient_rh_pct"] > 80.0
    is_danger = plan.overall_safety_status == CheckStatus.DANGER

    # -------------------------------------------------------------
    # 4. Top 3 Floating KPI Telemetry Cards (Real-time HTML/CSS)
    # -------------------------------------------------------------
    # Cooling status evaluation
    cooling_safe = (
        plan.ea_results["EA1"].status == CheckStatus.SAFE and
        plan.ea_results["EA3"].status == CheckStatus.SAFE
    )
    cooling_badge_color = "#10b981" if cooling_safe else "#ef4444"
    cooling_badge_bg = "rgba(16, 185, 129, 0.15)" if cooling_safe else "rgba(239, 68, 68, 0.2)"
    cooling_text = "NORMAL (Cooled)" if cooling_safe else "RISK DETECTED"

    # Humidity alert evaluation
    rh_bg = "#C95232" if is_high_rh else "#141418"
    rh_border = "#e06342" if is_high_rh else "#26262e"
    rh_badge_text = "Alert >80%" if is_high_rh else "Normal"
    rh_badge_bg = "rgba(0, 0, 0, 0.3)" if is_high_rh else "rgba(255, 255, 255, 0.1)"
    rh_badge_color = "#ffffff" if is_high_rh else "#10b981"

    # Global CSS for animated beacons and HUD styling
    st.markdown(
        """
        <style>
        @keyframes pulse-emerald {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); transform: scale(1); }
            70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); transform: scale(1.05); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); transform: scale(1); }
        }
        @keyframes pulse-danger {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8); transform: scale(1); }
            70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); transform: scale(1.08); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); transform: scale(1); }
        }
        @keyframes pulse-amber {
            0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); transform: scale(1); }
            70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); transform: scale(1.05); }
            100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); transform: scale(1); }
        }
        .beacon-safe {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #10b981;
            animation: pulse-emerald 2s infinite;
            vertical-align: middle;
            margin-right: 6px;
        }
        .beacon-danger {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #ef4444;
            animation: pulse-danger 1.2s infinite;
            vertical-align: middle;
            margin-right: 6px;
        }
        .beacon-amber {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #f59e0b;
            animation: pulse-amber 1.8s infinite;
            vertical-align: middle;
            margin-right: 6px;
        }
        .hud-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #18181d;
            border: 1px solid #2a2a34;
            border-radius: 6px;
            padding: 8px 12px;
            margin-top: 6px;
            font-size: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    with col_kpi1:
        st.markdown(
            f"""<div style="background-color: #141418; border-radius: 10px; padding: 16px 20px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #26262e; min-height: 110px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
<span style="font-size: 0.82rem; color: #A6A6A4; font-weight: 500;">⚡ Current Load</span>
<span style="font-size: 0.75rem; background: #26262e; color: #E6DDC9; padding: 2px 8px; border-radius: 4px; font-weight: 600;">{load_ratio*100:.1f}%</span>
</div>
<div style="font-size: 1.8rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{op_data['load_kva']:,.0f} kVA</div>
<div style="font-size: 0.78rem; color: #A6A6A4; margin-top: 4px;">Rated: {np_data['rated_kva']:,.0f} kVA &bull; Pendingin: {np_data['cooling_type']}</div>
</div>""",
            unsafe_allow_html=True,
        )

    with col_kpi2:
        st.markdown(
            f"""<div style="background-color: #141418; border-radius: 10px; padding: 16px 20px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #26262e; min-height: 110px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
<span style="font-size: 0.82rem; color: #A6A6A4; font-weight: 500;">🍃 Synthetic Ester Cooling</span>
<span style="font-size: 0.75rem; background: {cooling_badge_bg}; color: {cooling_badge_color}; padding: 2px 8px; border-radius: 4px; font-weight: 600;">{cooling_text}</span>
</div>
<div style="font-size: 1.8rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{np_data['fluid_type'].replace('_', ' ').title()}</div>
<div style="font-size: 0.78rem; color: #A6A6A4; margin-top: 4px;">Flash Point: {np_data['flash_point_c']}°C &bull; C₂H₂: {op_data['c2h2_ppm']:.1f} ppm</div>
</div>""",
            unsafe_allow_html=True,
        )

    with col_kpi3:
        st.markdown(
            f"""<div style="background-color: {rh_bg}; border-radius: 10px; padding: 16px 20px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid {rh_border}; transition: background-color 0.3s ease; min-height: 110px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
<span style="font-size: 0.82rem; color: #F4EFE6; font-weight: 500;">💧 Tropical Humidity</span>
<span style="font-size: 0.75rem; background: {rh_badge_bg}; color: {rh_badge_color}; padding: 2px 8px; border-radius: 4px; font-weight: 700;">{rh_badge_text}</span>
</div>
<div style="font-size: 1.8rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{op_data['ambient_rh_pct']:.1f}% RH</div>
<div style="font-size: 0.78rem; color: #F4EFE6; margin-top: 4px;">Suhu Lingkungan: {op_data['ambient_temp_c']:.1f}°C &bull; Limit: 80% RH</div>
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 5. Hero Stage: Live Unit Digital Twin + 3D Transformer Rendering
    # -------------------------------------------------------------
    hero_col_left, hero_col_right = st.columns([6, 6], gap="medium")

    with hero_col_left:
        # Dynamic overall safety status badge
        if plan.overall_safety_status == CheckStatus.DANGER:
            status_html = "<span style='background:#ef4444;color:white;padding:4px 12px;border-radius:6px;font-weight:700;font-size:0.8rem;'>🔴 STATUS: ANCAMAN BAHAYA ELEKTRIKAL</span>"
        elif plan.overall_safety_status == CheckStatus.WARNING:
            status_html = "<span style='background:#f59e0b;color:white;padding:4px 12px;border-radius:6px;font-weight:700;font-size:0.8rem;'>🟡 STATUS: PERINGATAN REKAYASA</span>"
        else:
            status_html = "<span style='background:#10b981;color:white;padding:4px 12px;border-radius:6px;font-weight:700;font-size:0.8rem;'>🟢 STATUS: SISTEM NORMAL</span>"

        st.markdown(
            f"""<div style="background-color: #141418; border-radius: 12px; padding: 20px 24px; color: white; border: 1px solid #26262e; height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
<div>
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<span style="font-size: 0.78rem; color: #C95232; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">Digital Twin Asset #{selected_unit_id}</span>
{status_html}
</div>
<h2 style="margin: 0 0 6px 0; font-size: 1.55rem; color: #E6DDC9; font-weight: 700;">
Medium-Voltage Power Transformer {np_data['primary_kv']:.0f} kV / {np_data['rated_kva']:,.0f} kVA
</h2>
<p style="margin: 0 0 16px 0; font-size: 0.88rem; color: #A6A6A4;">
Integrated RAM-FMEA Decision Support System &bull; Utilitas: <strong>{selected_unit.get('utility_code', 'UTIL-A')}</strong>
</p>
<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 0.84rem; background: #1c1b20; padding: 12px 16px; border-radius: 8px; border: 1px solid #2a2a34;">
<div><span style="color:#A6A6A4;">Tegangan Primer/Sekunder:</span><br><strong style="color:#E6DDC9;">{np_data['primary_kv']:.1f} kV / {np_data['secondary_kv']:.1f} kV</strong></div>
<div><span style="color:#A6A6A4;">Impedansi Relatif %Z:</span><br><strong style="color:#E6DDC9;">{np_data['impedance_z_pct']:.2f}%</strong></div>
<div><span style="color:#A6A6A4;">Vector Group:</span><br><strong style="color:#E6DDC9;">{np_data['vector_group']}</strong></div>
<div><span style="color:#A6A6A4;">Kapasitas Pemutus IR / Isc:</span><br><strong style="color:#E6DDC9;">{op_data['breaker_ir_ka']:.1f} kA / {op_data['breaker_isc_ka']:.1f} kA</strong></div>
</div>
</div>
<div style="margin-top: 14px; font-size: 0.8rem; color: #A6A6A4; display: flex; justify-content: space-between; align-items: center;">
<span>Jendela Pengamatan: <strong>87.600 Jam (10 Tahun)</strong></span>
<span>Kegagalan Tercatat: <strong style="color:#C95232;">{len(failures)} Insiden</strong></span>
</div>
</div>""",
            unsafe_allow_html=True,
        )

    with hero_col_right:
        # High-res 3D technical CAD Digital Twin rendering
        twin_3d_path = Path(__file__).resolve().parent.parent / "assets" / "transformer_3d_digital_twin.jpg"
        fallback_path = Path(__file__).resolve().parent.parent / "assets" / "transformer_3d_unit.png"
        img_to_show = twin_3d_path if twin_3d_path.exists() else fallback_path

        st.image(
            str(img_to_show),
            caption=f"⚡ Digital Twin Dynamic CAD Telemetry Model — Unit #{selected_unit_id}",
            use_container_width=True,
        )

        # Dynamic IoT Telemetry Beacon HUD (Animative & Data-responsive)
        ea1_beacon = "beacon-danger" if plan.ea_results["EA1"].status != CheckStatus.SAFE else "beacon-safe"
        ea2_beacon = "beacon-danger" if plan.ea_results["EA2"].status != CheckStatus.SAFE else "beacon-safe"
        ea3_beacon = "beacon-danger" if plan.ea_results["EA3"].status != CheckStatus.SAFE else "beacon-safe"
        rh_beacon = "beacon-amber" if is_high_rh else "beacon-safe"

        c2h2_val_color = "#ef4444" if op_data["c2h2_ppm"] > 5.0 else "#10b981"
        c2h2_text = f"C₂H₂: {op_data['c2h2_ppm']:.1f} ppm ({'BAHAYA >5 ppm' if op_data['c2h2_ppm'] > 5.0 else 'Nominal'})"

        ir_is_danger = op_data["breaker_ir_ka"] < op_data["breaker_isc_ka"]
        ir_val_color = "#ef4444" if ir_is_danger else "#10b981"
        ir_text = f"IR {op_data['breaker_ir_ka']:.1f} kA vs Isc {op_data['breaker_isc_ka']:.1f} kA ({'BAHAYA IR < Isc' if ir_is_danger else 'Margin Aman'})"

        aging_val = plan.ea_results["EA3"].measured.get("aging_factor", 1.0)
        thermal_is_danger = plan.ea_results["EA3"].status != CheckStatus.SAFE
        thermal_val_color = "#ef4444" if thermal_is_danger else "#10b981"
        thermal_text = f"Hotspot {op_data.get('top_oil_temp_c', 65.0)+15:.0f}°C ({'Overheating ' + str(round(aging_val, 1)) + 'x' if thermal_is_danger else 'Normal'})"

        rh_val_color = "#C95232" if is_high_rh else "#10b981"
        rh_text = f"Kelembaban {op_data['ambient_rh_pct']:.1f}% ({'Waspada >80% RH' if is_high_rh else 'Optimal'})"

        st.markdown(
            f"""<div style="background: #141418; border: 1px solid #26262e; border-radius: 8px; padding: 10px 14px; margin-top: 4px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
<span style="font-size: 0.75rem; color: #A6A6A4; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">● Telemetri Digital Twin (IoT Live Sensors)</span>
<span style="font-size: 0.7rem; color: #C95232; font-weight: 600;">Unit #{selected_unit_id}</span>
</div>
<div style="display: flex; flex-direction: column; gap: 4px;">
<div class="hud-row">
<div style="display: flex; align-items: center;"><span class="{ea1_beacon}"></span><span style="color:#A6A6A4; font-weight:600;">DGA Gas & Ester:</span></div>
<span style="color:{c2h2_val_color}; font-weight:700;">{c2h2_text}</span>
</div>
<div class="hud-row">
<div style="display: flex; align-items: center;"><span class="{ea2_beacon}"></span><span style="color:#A6A6A4; font-weight:600;">Circuit Breaker:</span></div>
<span style="color:{ir_val_color}; font-weight:700;">{ir_text}</span>
</div>
<div class="hud-row">
<div style="display: flex; align-items: center;"><span class="{ea3_beacon}"></span><span style="color:#A6A6A4; font-weight:600;">Pendingin Termal:</span></div>
<span style="color:{thermal_val_color}; font-weight:700;">{thermal_text}</span>
</div>
<div class="hud-row">
<div style="display: flex; align-items: center;"><span class="{rh_beacon}"></span><span style="color:#A6A6A4; font-weight:600;">Kelembaban Tropis:</span></div>
<span style="color:{rh_val_color}; font-weight:700;">{rh_text}</span>
</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 6. Main Analytics: Dual Side-by-Side Panels (Mirroring Mockup)
    # -------------------------------------------------------------
    col_panel_ram, col_panel_fmea = st.columns([1, 1], gap="medium")

    # PANEL KIRI: Live RAM Reliability Curve
    with col_panel_ram:
        # Select component for RAM curve
        comp_keys = list(truth["components_truth"].keys())
        selected_comp = st.selectbox(
            "Pilih Komponen Kritis:",
            options=comp_keys,
            index=0,
            format_func=lambda c: f"{c.upper()} (True β={truth['components_truth'][c]['beta']})",
            key="ram_comp_selector",
        )

        samples = truth["component_samples"][selected_comp]
        fig_ram, fit_res = create_reliability_curve(
            decision_service.ram_engine,
            ttf_list=samples["failures"],
            censored_list=samples["censored"],
            component_name=selected_comp,
        )
        st.plotly_chart(fig_ram, use_container_width=True)

        # Bottom metrics for RAM
        st.markdown(
            f"""
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; background: #141418; padding: 10px 14px; border-radius: 8px; border: 1px solid #26262e; text-align: center; margin-top: -10px;">
                <div><span style="font-size:0.75rem; color:#A6A6A4;">Availability (A)</span><br><strong style="color:#10b981; font-size:1.05rem;">{plan.system_availability:.2f}%</strong></div>
                <div><span style="font-size:0.75rem; color:#A6A6A4;">MTBF Komponen</span><br><strong style="color:#E6DDC9; font-size:1.05rem;">{fit_res.mtbf:,.0f} jam</strong></div>
                <div><span style="font-size:0.75rem; color:#A6A6A4;">Interval Pemeliharaan</span><br><strong style="color:#C95232; font-size:1.05rem;">{18 if selected_comp=='cooling' else 14} bln</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # PANEL KANAN: Structured FMEA Risk Matrix & Priority Actions
    with col_panel_fmea:
        st.markdown(
            """
            <div style="background: #141418; padding: 14px 18px; border-radius: 10px; border: 1px solid #26262e; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.95rem; font-weight: 700; color: #E6DDC9;">FMEA (Failure Mode and Effects Analysis)</span>
                    <span style="font-size: 0.75rem; background: #26262e; color: #A6A6A4; padding: 2px 8px; border-radius: 4px;">6 Komponen Kritis</span>
                </div>
                <div style="font-size: 0.78rem; color: #A6A6A4; margin-top: 2px;">Tindakan Rekayasa Terprioritas (Engineering Actions = Task + Frequency)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fmea_items = []
        for act in plan.actions:
            # Color badge for RPN & Risk
            if act.rpn >= 80:
                risk_badge = f"<span style='background:#ef4444;color:white;padding:2px 8px;border-radius:4px;font-weight:700;font-size:0.75rem;'>{act.rpn} (High)</span>"
            elif act.rpn >= 50:
                risk_badge = f"<span style='background:#f59e0b;color:white;padding:2px 8px;border-radius:4px;font-weight:700;font-size:0.75rem;'>{act.rpn} (Medium)</span>"
            else:
                risk_badge = f"<span style='background:#10b981;color:white;padding:2px 8px;border-radius:4px;font-weight:700;font-size:0.75rem;'>{act.rpn} (Low)</span>"

            ea_icon = "🔴" if act.ea_risk_status == CheckStatus.DANGER else ("🟡" if act.ea_risk_status == CheckStatus.WARNING else "🟢")

            fmea_items.append({
                "Prioritas": f"#{act.priority_rank}",
                "Status EA": f"{ea_icon} {act.ea_risk_status}",
                "Komponen": act.component_name,
                "RPN": act.rpn,
                "Tugas Pengujian (FMEA)": act.task_description,
                "Frekuensi RAM": f"Tiap {act.interval_months} bln",
            })

        st.dataframe(fmea_items, use_container_width=True, hide_index=True, height=270)

        st.markdown(
            f"""
            <div style="background: #1c1b20; border-radius: 6px; padding: 8px 12px; font-size: 0.76rem; color: #A6A6A4; border: 1px solid #2a2a34;">
                💡 <strong>Prinsip Prioritas:</strong> Risiko Bahaya EA terdahulu &rarr; RPN tertinggi &rarr; Interval pemeliharaan terpendek.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 7. Deep-Dive Section: Detailed Tabs
    # -------------------------------------------------------------
    st.markdown("### 🔍 Detail Analisis Mendalam & Audit Sistem")

    tab_actions, tab_safety, tab_fmea, tab_methodology = st.tabs([
        "📋 Rencana Pemeliharaan Lengkap (Action Plan)",
        "🚨 Verifikasi 5 Electrical Accidents (EA1–EA5)",
        "📑 Matriks FMEA 4-Baris Komprehensif",
        "📚 Standar Enjiniring & Kerangka Kerja",
    ])

    # TAB 1: Detailed Action Plan & JSON Download
    with tab_actions:
        st.subheader("🎯 Tabel Rencana Aksi Pemeliharaan Terpadu")
        action_rows = []
        for act in plan.actions:
            status_icon = "🔴 BAHAYA" if act.ea_risk_status == CheckStatus.DANGER else ("🟡 PERINGATAN" if act.ea_risk_status == CheckStatus.WARNING else "🟢 NORMAL")
            action_rows.append({
                "Prioritas": f"#{act.priority_rank}",
                "Status Risiko EA": status_icon,
                "Komponen": act.component_name,
                "RPN": act.rpn,
                "Engineering Task": act.task_description,
                "Metode Uji": act.test_method or "-",
                "Frekuensi Pemeliharaan": f"Setiap {act.interval_months} bulan ({act.interval_hours:.0f} jam)",
                "Standar Rujukan": act.reference_standard,
                "Catatan Rekayasa": act.reference_note or "-",
            })
        st.dataframe(action_rows, use_container_width=True, hide_index=True)

        col_dl1, col_dl2 = st.columns([8, 2])
        with col_dl2:
            st.download_button(
                label="📥 Unduh Action Plan (JSON)",
                data=plan.model_dump_json(indent=2),
                file_name=f"ActionPlan_{selected_unit_id}.json",
                mime="application/json",
                use_container_width=True,
            )

    # TAB 2: Electrical Accidents EA1-EA5 Checker
    with tab_safety:
        st.subheader("🛡️ Evaluasi Fisik 5 Electrical Accidents (EA1–EA5)")
        ea_meta = [
            ("EA1", "Kebakaran akibat Flash Point Rendah & DGA C2H2", plan.ea_results.get("EA1")),
            ("EA2", "Ledakan Circuit Breaker (Interrupting Rating IR < Isc)", plan.ea_results.get("EA2")),
            ("EA3", "Kebakaran akibat Tipe Pendingin Salah (Thermal Aging)", plan.ea_results.get("EA3")),
            ("EA4", "Kerusakan Paralel: Ketidaksesuaian Impedansi %Z", plan.ea_results.get("EA4")),
            ("EA5", "Kerusakan Paralel: Ketidaksesuaian Vector Group", plan.ea_results.get("EA5")),
        ]
        for code, title, res in ea_meta:
            if res:
                render_ea_badge(code, title, res)
            else:
                st.info(f"**{code}: {title}** — Evaluasi aktif saat trafo dioperasikan paralel dengan unit pendamping.")

    # TAB 3: 4-Row FMEA Matrix
    with tab_fmea:
        st.subheader("📑 Matriks FMEA Empat Baris (Baris F, M, E, A)")
        default_matrix = decision_service.fmea_engine.get_default_matrix()
        for idx, row in enumerate(default_matrix.rows, start=1):
            with st.expander(f"Komponen #{idx}: {row.row_f.component_name} — RPN: {row.row_a.rpn} ({row.row_a.hidden_or_evident})", expanded=(idx == 1)):
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
                    st.markdown(f"- **Metode Uji Standar:** `{row.row_a.test_method}`")
                    st.markdown(f"- **Rujukan Standar:** {row.row_a.reference_standard}")
                    if row.row_a.reference_note:
                        st.info(f"💡 **Catatan Rekayasa:** {row.row_a.reference_note}")

    # TAB 4: Standards & Methodology
    with tab_methodology:
        st.subheader("📚 Standar Enjiniring & Kerangka Kerja Metodologi")
        st.markdown(
            """
            | Komponen Sistem | Standar Acuan & Formulasi | Keterangan & Status Implementasi |
            |---|---|---|
            | **Persamaan RAM (2.1)–(2.5)** | IEEE Std 493 / MIL-HDBK-338B | Diimplementasikan murni di `backend/engines/ram_engine.py`. |
            | **Verifikasi Eksponensial** | Exponential Bathtub Validation | $R(50)=81,87\\%$, $R(130)=59,45\\%$, $F(130)=40,55\\%$ lolos uji validasi. |
            | **Benchmark Switchgear 20 kV** | IEEE Reliability Test System | $\\text{MTBF}=17,38$ bulan dibulatkan ke atas menjadi 18 bulan, $A=99,63\\%$. |
            | **Lima Electrical Accidents** | IEC 62271-100, IEEE C57.91, IEC 60076 | 5 fungsi keselamatan deterministik di `backend/safety/ea_checker.py`. |
            | **EA 1 (DGA Asetilena > 5 ppm)** | IEEE C57.104 / IEC 60599 | Ambang batas kritis gas asetilena (C2H2) untuk deteksi ancaman pelepasan busur termal. |
            | **EA 2 (IR vs Isc Breaker)** | IEC 62271-100 | Kapasitas pemutus arus hubung singkat (DANGER/WARNING/SAFE). |
            | **EA 3 (+7 °C => +30% aging)** | IEEE C57.91 Loading Guide | Model degradasi termal isolasi berbasis *Aging Acceleration Factor*. |
            | **EA 4 (Selisih %Z > 10%)** | IEC 60076-8 Parallel Operation | Selisih relatif impedansi trafo paralel untuk mitigasi arus sirkulasi beban. |
            | **EA 5 (Vector Group Mismatch)** | IEC 60076-1 Vector Compatibility | Kompatibilitas fasa (beda jam $\\neq 0$) biner DANGER proteksi hubung singkat. |
            | **Struktur 4-Baris FMEA** | AIAG/VDA FMEA Standard | Baris F (Fungsi), M (Mekanisme), E (Efek), A (Analisis & Task). |
            | **Enam Komponen Kritis** | CIGRE Working Group A2.37 | OLTC, winding, core, bushing, cooling, insulation (>85% kegagalan trafo). |
            | **Pengujian Diagnostik** | IEEE C57.152 / IEC 60270 | Uji Tahanan Isolasi, PI, DAR, Tan Delta, Partial Discharge, DGA. |
            """
        )


if __name__ == "__main__":
    main()
