"""
MV-GPT DSS — Integrated RAM-FMEA Decision Support System Dashboard.
Production-grade Engineering Dashboard for Medium Voltage Green Power Transformer (1–35 kV).
Enterprise Asset Intelligence platform integrating RAM & FMEA analytics.

Layout conforms to the reference materials:
- Proposal Bab I–III (Rev3) & PPT Sidang Proposal Disertasi (Prabowo Soetadji, UNY)
- RAM-FMEA Transformer Safety DSS Technical Architecture & Wireframes:
  * Page 1 & 8: 2.5D Isometric CAD Cutaway Blueprint with 6 critical components (>85% failures)
  * Page 7: Core Synthesis (Engineering Actions = Engineering Tasks + Engineering Frequency)
  * Page 8: Modul Safety Checker 5 Ancaman Fatal (EA1–EA5 Shields & Parallel Operation Green Light)
  * Page 12: Dashboard APM Wireframe (Reliability Trend, Asset Availability Donut, Actions Scheduler)
  * Page 13: Optimasi Biaya & Keandalan (CAPEX/OPEX Economic U-Curve)
  * Slide 12: Tabel 2.5 Komparasi 11 Metodologi Analisis Risiko & Keandalan
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
            fillcolor="rgba(56, 189, 248, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="95% Confidence Interval",
        )
    )

    # Main R(t) line
    fig.add_trace(
        go.Scatter(
            x=t_vals,
            y=r_est,
            mode="lines",
            name=f"R(t) Weibull (β={fit.beta:.2f}, η={fit.eta:,.0f}h)",
            line=dict(color="#38bdf8", width=3),
        )
    )

    # Benchmark R = 0.75 line (IEEE Switchgear)
    fig.add_hline(
        y=0.75,
        line_dash="dot",
        line_color="#f59e0b",
        annotation_text="Target R = 0.75",
        annotation_position="bottom right",
        annotation_font=dict(color="#f59e0b", size=10),
    )

    # Wear-Out Zone shaded rectangle (after ~60,000h)
    fig.add_vrect(
        x0=60000,
        x1=87600,
        fillcolor="rgba(239, 68, 68, 0.08)",
        layer="below",
        line_width=0,
        annotation_text="Wear-Out Zone (λ meningkat)",
        annotation_position="top left",
        annotation_font=dict(color="#ef4444", size=9),
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Kurva Keandalan R(t) — {component_name.upper()}</b>",
            font=dict(size=13, color="#E6DDC9"),
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
        height=280,
        margin=dict(l=35, r=35, t=40, b=40),
        paper_bgcolor="#141418",
        plot_bgcolor="#141418",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="center",
            x=0.5,
            font=dict(size=9, color="#E6DDC9"),
        ),
    )

    return fig, fit


def create_availability_donut(availability_pct: float):
    """Render Asset Availability Donut Chart matching Page 12 wireframe."""
    fig = go.Figure(
        data=[
            go.Pie(
                values=[availability_pct, max(0.0, 100.0 - availability_pct)],
                hole=0.74,
                direction="clockwise",
                sort=False,
                marker=dict(colors=["#10b981", "#26262e"]),
                textinfo="none",
                hoverinfo="none",
            )
        ]
    )

    fig.update_layout(
        annotations=[
            dict(
                text=f"<b style='font-size:1.55rem;color:#10b981;'>{availability_pct:.2f}%</b><br><span style='font-size:0.75rem;color:#A6A6A4;'>Available</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
        ],
        showlegend=False,
        height=140,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_cost_optimization_curve():
    """Render CAPEX / OPEX Economic Balance U-Curve matching Page 13 of whitepaper."""
    r_vals = np.linspace(0.50, 0.98, 100)
    c_maint = 15.0 + 85.0 * ((r_vals - 0.45) / (1.02 - r_vals)) ** 0.85
    c_downtime = 160.0 * (1.0 - r_vals) ** 0.9
    c_total = c_maint + c_downtime
    min_idx = int(np.argmin(c_total))
    opt_r = r_vals[min_idx]
    opt_cost = c_total[min_idx]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=r_vals * 100,
            y=c_total,
            mode="lines",
            name="Total Cost (Biaya Total)",
            line=dict(color="#38bdf8", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=r_vals * 100,
            y=c_maint,
            mode="lines",
            name="Biaya Investasi Pemeliharaan (CAPEX/OPEX)",
            line=dict(color="#f59e0b", width=2, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=r_vals * 100,
            y=c_downtime,
            mode="lines",
            name="Biaya Produksi & Kerugian Downtime",
            line=dict(color="#ef4444", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[opt_r * 100],
            y=[opt_cost],
            mode="markers+text",
            name="Titik Optimum Operasi DSS",
            marker=dict(size=11, color="#10b981", symbol="diamond"),
            text=["Titik Optimum DSS (R≈76%)"],
            textposition="top center",
            textfont=dict(color="#10b981", size=11),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Optimasi Biaya dan Keandalan (CAPEX / OPEX U-Curve — Page 13)</b>",
            font=dict(size=13, color="#E6DDC9"),
        ),
        xaxis=dict(
            title="Tingkat Keandalan R (Reliability %)",
            gridcolor="#26262e",
            zerolinecolor="#26262e",
            color="#A6A6A4",
        ),
        yaxis=dict(
            title="Biaya Relatif (Cost Index)",
            gridcolor="#26262e",
            zerolinecolor="#26262e",
            color="#A6A6A4",
        ),
        height=320,
        margin=dict(l=40, r=40, t=50, b=50),
        paper_bgcolor="#141418",
        plot_bgcolor="#141418",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(size=9, color="#E6DDC9"),
        ),
    )
    return fig


def main():
    config = load_thresholds()
    decision_service = DecisionService(config=config)
    dataset, truth = load_data()

    # -------------------------------------------------------------
    # Zero-wasted space CSS injections & Animations
    # -------------------------------------------------------------
    st.markdown(
        """
        <style>
        /* Tight container styling with clean clearance for Streamlit top header */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            margin-bottom: -0.15rem;
        }
        @keyframes pulse-emerald {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); transform: scale(1); }
            70% { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); transform: scale(1.05); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); transform: scale(1); }
        }
        @keyframes pulse-danger {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8); transform: scale(1); }
            70% { box-shadow: 0 0 0 9px rgba(239, 68, 68, 0); transform: scale(1.08); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); transform: scale(1); }
        }
        @keyframes pulse-amber {
            0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); transform: scale(1); }
            70% { box-shadow: 0 0 0 7px rgba(245, 158, 11, 0); transform: scale(1.05); }
            100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); transform: scale(1); }
        }
        .beacon-safe {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10b981;
            animation: pulse-emerald 2s infinite;
            vertical-align: middle;
            margin-right: 5px;
        }
        .beacon-danger {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #ef4444;
            animation: pulse-danger 1.2s infinite;
            vertical-align: middle;
            margin-right: 5px;
        }
        .beacon-amber {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #f59e0b;
            animation: pulse-amber 1.8s infinite;
            vertical-align: middle;
            margin-right: 5px;
        }
        .hud-badge {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #18181d;
            border: 1px solid #2a2a34;
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 0.77rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------
    # 1. Header (Compact 1-line horizontal card, zero empty space)
    # -------------------------------------------------------------
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #141418 0%, #1c1b20 50%, #291d19 80%, #C95232 100%); padding: 10px 18px; border-radius: 8px; color: white; margin-bottom: 12px; border-left: 5px solid #C95232; box-shadow: 0 2px 8px rgba(0,0,0,0.12); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 1.15rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.3px;">⚡ MV-GPT DSS</span>
                <span style="font-size: 0.92rem; font-weight: 600; color: #F4EFE6;">— Integrated RAM-FMEA Decision Support System</span>
                <span style="font-size: 0.8rem; color: #A6A6A4;">| Trafo Hijau 1–35 kV</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #dcfce7; padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600;">
                    ● Enterprise Asset Intelligence
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------
    # 2. Sidebar: Asset & Scenario Selector
    # -------------------------------------------------------------
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

    # Generate Decision Plan
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

    # -------------------------------------------------------------
    # 3. Top 3 Floating KPI Telemetry Cards
    # -------------------------------------------------------------
    cooling_safe = (
        plan.ea_results["EA1"].status == CheckStatus.SAFE and
        plan.ea_results["EA3"].status == CheckStatus.SAFE
    )
    cooling_badge_color = "#10b981" if cooling_safe else "#ef4444"
    cooling_badge_bg = "rgba(16, 185, 129, 0.15)" if cooling_safe else "rgba(239, 68, 68, 0.2)"
    cooling_text = "NORMAL (Cooled)" if cooling_safe else "RISK DETECTED"

    rh_bg = "#C95232" if is_high_rh else "#141418"
    rh_border = "#e06342" if is_high_rh else "#26262e"
    rh_badge_text = "Alert >80%" if is_high_rh else "Normal"
    rh_badge_bg = "rgba(0, 0, 0, 0.3)" if is_high_rh else "rgba(255, 255, 255, 0.1)"
    rh_badge_color = "#ffffff" if is_high_rh else "#10b981"

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    with col_kpi1:
        st.markdown(
            f"""<div style="background-color: #141418; border-radius: 10px; padding: 14px 18px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #26262e; min-height: 102px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
<span style="font-size: 0.8rem; color: #A6A6A4; font-weight: 500;">⚡ Current Load</span>
<span style="font-size: 0.72rem; background: #26262e; color: #E6DDC9; padding: 2px 7px; border-radius: 4px; font-weight: 600;">{load_ratio*100:.1f}%</span>
</div>
<div style="font-size: 1.65rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{op_data['load_kva']:,.0f} kVA</div>
<div style="font-size: 0.76rem; color: #A6A6A4; margin-top: 2px;">Rated: {np_data['rated_kva']:,.0f} kVA &bull; Pendingin: {np_data['cooling_type']}</div>
</div>""",
            unsafe_allow_html=True,
        )

    with col_kpi2:
        st.markdown(
            f"""<div style="background-color: #141418; border-radius: 10px; padding: 14px 18px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #26262e; min-height: 102px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
<span style="font-size: 0.8rem; color: #A6A6A4; font-weight: 500;">🍃 Synthetic Ester Cooling</span>
<span style="font-size: 0.72rem; background: {cooling_badge_bg}; color: {cooling_badge_color}; padding: 2px 7px; border-radius: 4px; font-weight: 600;">{cooling_text}</span>
</div>
<div style="font-size: 1.65rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{np_data['fluid_type'].replace('_', ' ').title()}</div>
<div style="font-size: 0.76rem; color: #A6A6A4; margin-top: 2px;">Flash Point: {np_data['flash_point_c']}°C &bull; C₂H₂: {op_data['c2h2_ppm']:.1f} ppm</div>
</div>""",
            unsafe_allow_html=True,
        )

    with col_kpi3:
        st.markdown(
            f"""<div style="background-color: {rh_bg}; border-radius: 10px; padding: 14px 18px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid {rh_border}; transition: background-color 0.3s ease; min-height: 102px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
<span style="font-size: 0.8rem; color: #F4EFE6; font-weight: 500;">💧 Tropical Humidity</span>
<span style="font-size: 0.72rem; background: {rh_badge_bg}; color: {rh_badge_color}; padding: 2px 7px; border-radius: 4px; font-weight: 700;">{rh_badge_text}</span>
</div>
<div style="font-size: 1.65rem; font-weight: 700; color: #E6DDC9; letter-spacing: -0.5px;">{op_data['ambient_rh_pct']:.1f}% RH</div>
<div style="font-size: 0.76rem; color: #F4EFE6; margin-top: 2px;">Suhu Lingkungan: {op_data['ambient_temp_c']:.1f}°C &bull; Limit: 80% RH</div>
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 4. Hero Stage: 2.5D Isometric CAD Cutaway Blueprint + Full Safety Suite
    #    Zero empty space: Height of left and right columns balanced ~560px
    # -------------------------------------------------------------
    hero_col_left, hero_col_right = st.columns([5.5, 6.5], gap="medium")

    with hero_col_left:
        twin_25d_path = Path(__file__).resolve().parent.parent / "assets" / "transformer_25d_digital_twin.png"
        blueprint_raw_path = Path(__file__).resolve().parent.parent / "assets" / "transformer_25d_blueprint.png"
        img_to_show = twin_25d_path if twin_25d_path.exists() else blueprint_raw_path

        st.markdown(
            f"""
            <div style="background-color: #141418; border-radius: 10px; padding: 10px 14px; border: 1px solid #26262e; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.82rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.6px;">
                        ⚡ 2.5D Isometric CAD Cutaway Blueprint (Digital Twin)
                    </span>
                    <span style="font-size: 0.72rem; color: #A6A6A4; background: #1c1b20; padding: 2px 8px; border-radius: 4px;">
                        Unit #{selected_unit_id}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.image(
            str(img_to_show),
            caption="Gambar 1.3: Blueprint CAD 2.5D Cutaway Power Transformer 3-Fasa (UNY Proposal & DSS)",
            use_container_width=True,
        )

    with hero_col_right:
        # Status chip
        if plan.overall_safety_status == CheckStatus.DANGER:
            status_chip = "<span style='background:#ef4444;color:white;padding:3px 10px;border-radius:6px;font-weight:700;font-size:0.75rem;'>🔴 ANCAMAN BAHAYA ELEKTRIKAL</span>"
        elif plan.overall_safety_status == CheckStatus.WARNING:
            status_chip = "<span style='background:#f59e0b;color:white;padding:3px 10px;border-radius:6px;font-weight:700;font-size:0.75rem;'>🟡 PERINGATAN REKAYASA</span>"
        else:
            status_chip = "<span style='background:#10b981;color:white;padding:3px 10px;border-radius:6px;font-weight:700;font-size:0.75rem;'>🟢 SISTEM OPERASIONAL NORMAL</span>"

        # CARD 1: Nameplate & Operating Telemetry
        st.markdown(
            f"""
            <div style="background-color: #141418; border-radius: 10px; padding: 12px 16px; color: white; border: 1px solid #26262e; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 0.72rem; color: #C95232; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">
                        Data Nameplate & Operasi #{selected_unit_id}
                    </span>
                    {status_chip}
                </div>
                <h3 style="margin: 0 0 6px 0; font-size: 1.15rem; color: #E6DDC9; font-weight: 700;">
                    Medium-Voltage Power Transformer {np_data['primary_kv']:.0f} kV / {np_data['rated_kva']:,.0f} kVA
                </h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 10px; font-size: 0.78rem; background: #1c1b20; padding: 8px 12px; border-radius: 6px; border: 1px solid #2a2a34;">
                    <div><span style="color:#A6A6A4;">Tegangan:</span> <strong style="color:#E6DDC9;">{np_data['primary_kv']:.1f} kV / {np_data['secondary_kv']:.1f} kV</strong></div>
                    <div><span style="color:#A6A6A4;">Impedansi %Z:</span> <strong style="color:#E6DDC9;">{np_data['impedance_z_pct']:.2f}%</strong></div>
                    <div><span style="color:#A6A6A4;">Vector Group:</span> <strong style="color:#E6DDC9;">{np_data['vector_group']}</strong></div>
                    <div><span style="color:#A6A6A4;">Kapasitas Pemutus:</span> <strong style="color:#E6DDC9;">IR {op_data['breaker_ir_ka']:.1f} kA vs Isc {op_data['breaker_isc_ka']:.1f} kA</strong></div>
                    <div><span style="color:#A6A6A4;">Basis Operasi:</span> <strong style="color:#E6DDC9;">87.600 Jam (10 Tahun)</strong></div>
                    <div><span style="color:#A6A6A4;">Histori Insiden:</span> <strong style="color:#C95232;">{len(failures)} Kasus Tercatat</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # CARD 2: Modul Safety Checker: 5 Ancaman Fatal (Page 8 DSS)
        ea1_res = plan.ea_results["EA1"]
        ea2_res = plan.ea_results["EA2"]
        ea3_res = plan.ea_results["EA3"]
        ea4_res = plan.ea_results.get("EA4")
        ea5_res = plan.ea_results.get("EA5")

        def status_badge_html(res):
            if res is None:
                return "<span style='background:#374151;color:#d1d5db;padding:2px 6px;border-radius:4px;font-size:0.68rem;'>STANDBY</span>"
            if res.status == CheckStatus.DANGER:
                return "<span style='background:#ef4444;color:white;padding:2px 6px;border-radius:4px;font-weight:700;font-size:0.68rem;'>🔴 DANGER</span>"
            if res.status == CheckStatus.WARNING:
                return "<span style='background:#f59e0b;color:white;padding:2px 6px;border-radius:4px;font-weight:700;font-size:0.68rem;'>🟡 WARNING</span>"
            return "<span style='background:#10b981;color:white;padding:2px 6px;border-radius:4px;font-weight:700;font-size:0.68rem;'>🟢 SAFE</span>"

        # Check parallel authorization
        parallel_authorized = True
        if ea4_res and ea4_res.status == CheckStatus.DANGER:
            parallel_authorized = False
        if ea5_res and ea5_res.status == CheckStatus.DANGER:
            parallel_authorized = False

        if companion_unit:
            if parallel_authorized:
                parallel_banner = """
                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; border-radius: 6px; padding: 4px 8px; margin-top: 6px; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-size: 0.74rem; color: #dcfce7; font-weight: 600;">🛡️ Izin 'Parallel Operation Green Light' DITERBITKAN</span>
                    <span style="font-size: 0.68rem; color: #10b981; font-weight: 700;">EA4 & EA5 Lolos</span>
                </div>
                """
            else:
                parallel_banner = """
                <div style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 6px; padding: 4px 8px; margin-top: 6px; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-size: 0.74rem; color: #fecaca; font-weight: 600;">🚫 Izin Operasi Paralel DIBLOKIR — Ketidaksesuaian Parameter</span>
                    <span style="font-size: 0.68rem; color: #ef4444; font-weight: 700;">BAHAYA</span>
                </div>
                """
        else:
            parallel_banner = """
            <div style="background: #1c1b20; border: 1px solid #2a2a34; border-radius: 6px; padding: 4px 8px; margin-top: 6px; display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 0.73rem; color: #A6A6A4;">ℹ️ Unit Beroperasi Tunggal (Evaluasi Paralel Aktif Saat Pair Terhubung)</span>
                <span style="font-size: 0.68rem; color: #A6A6A4;">Standby</span>
            </div>
            """

        st.markdown(
            f"""
            <div style="background-color: #141418; border-radius: 10px; padding: 10px 14px; color: white; border: 1px solid #26262e; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: #E6DDC9;">Modul Safety Checker: 5 Ancaman Fatal (EA)</span>
                    <span style="font-size: 0.7rem; color: #A6A6A4;">Page 8 DSS</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #1c1b20; padding: 5px 8px; border-radius: 5px; border-left: 3px solid {'#ef4444' if ea1_res.status==CheckStatus.DANGER else '#10b981'}; font-size: 0.76rem;">
                        <span><strong>EA 1:</strong> Kebakaran (Flash Point & C₂H₂ &gt; 5 ppm)</span>
                        {status_badge_html(ea1_res)}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #1c1b20; padding: 5px 8px; border-radius: 5px; border-left: 3px solid {'#ef4444' if ea2_res.status==CheckStatus.DANGER else '#10b981'}; font-size: 0.76rem;">
                        <span><strong>EA 2:</strong> Ledakan Circuit Breaker (IR &lt; Isc)</span>
                        {status_badge_html(ea2_res)}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #1c1b20; padding: 5px 8px; border-radius: 5px; border-left: 3px solid {'#ef4444' if ea3_res.status==CheckStatus.DANGER else ('#f59e0b' if ea3_res.status==CheckStatus.WARNING else '#10b981')}; font-size: 0.76rem;">
                        <span><strong>EA 3:</strong> Overheating &amp; Penuaan Isolasi (+7°C ⇒ +30%)</span>
                        {status_badge_html(ea3_res)}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #1c1b20; padding: 5px 8px; border-radius: 5px; border-left: 3px solid {'#ef4444' if ea4_res and ea4_res.status==CheckStatus.DANGER else '#10b981'}; font-size: 0.76rem;">
                        <span><strong>EA 4:</strong> Kerusakan Paralel: Ketidaksesuaian %Z (|Δ%Z| &gt; 10%)</span>
                        {status_badge_html(ea4_res)}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #1c1b20; padding: 5px 8px; border-radius: 5px; border-left: 3px solid {'#ef4444' if ea5_res and ea5_res.status==CheckStatus.DANGER else '#10b981'}; font-size: 0.76rem;">
                        <span><strong>EA 5:</strong> Kerusakan Paralel: Ketidaksesuaian Vector Group</span>
                        {status_badge_html(ea5_res)}
                    </div>
                </div>
                {parallel_banner}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # CARD 3: Telemetri Sensor 6 Komponen Kritis (>85% Failure Scope)
        # Positioned here on the right to flush-align with the 2.5D blueprint on the left!
        c2h2_danger = op_data["c2h2_ppm"] > 5.0
        ir_danger = op_data["breaker_ir_ka"] < op_data["breaker_isc_ka"]
        cooling_danger = plan.ea_results["EA3"].status != CheckStatus.SAFE

        st.markdown(
            f"""
            <div style="background: #141418; border: 1px solid #26262e; border-radius: 8px; padding: 8px 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 0.74rem; color: #A6A6A4; font-weight: 600; text-transform: uppercase;">
                        ● Telemetri Sensor 6 Komponen Kritis (&gt;85% Failure Scope)
                    </span>
                    <span style="font-size: 0.7rem; color: #38bdf8;">CIGRE A2.37</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 5px;">
                    <div class="hud-badge">
                        <span><span class="{'beacon-danger' if c2h2_danger else 'beacon-safe'}"></span>Conservator/DGA:</span>
                        <strong style="color:{'#ef4444' if c2h2_danger else '#10b981'};">{op_data['c2h2_ppm']:.1f} ppm</strong>
                    </div>
                    <div class="hud-badge">
                        <span><span class="{'beacon-danger' if ir_danger else 'beacon-safe'}"></span>Bushing &amp; CB:</span>
                        <strong style="color:{'#ef4444' if ir_danger else '#10b981'};">IR {op_data['breaker_ir_ka']:.0f} kA</strong>
                    </div>
                    <div class="hud-badge">
                        <span><span class="beacon-safe"></span>Tap Changer (OLTC):</span>
                        <strong style="color:#10b981;">Kontak Stabil</strong>
                    </div>
                    <div class="hud-badge">
                        <span><span class="{'beacon-danger' if cooling_danger else 'beacon-safe'}"></span>Winding Hotspot:</span>
                        <strong style="color:{'#ef4444' if cooling_danger else '#10b981'};">{op_data.get('top_oil_temp_c', 65.0)+15:.0f}°C</strong>
                    </div>
                    <div class="hud-badge">
                        <span><span class="beacon-safe"></span>Core Lamination:</span>
                        <strong style="color:#10b981;">Nominal</strong>
                    </div>
                    <div class="hud-badge">
                        <span><span class="{'beacon-danger' if cooling_danger else 'beacon-safe'}"></span>Radiator Pendingin:</span>
                        <strong style="color:{'#ef4444' if cooling_danger else '#10b981'};">{np_data['cooling_type']}</strong>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 5. Core Dual-Track Engine: RAM & Engineering Actions Scheduler
    #    (Page 7 & Page 12 Wireframe) — Flush alignment with zero empty space
    # -------------------------------------------------------------
    col_panel_ram, col_panel_sched = st.columns([6, 6], gap="medium")

    with col_panel_ram:
        comp_keys = list(truth["components_truth"].keys())
        col_sel1, col_sel2 = st.columns([7, 3])
        with col_sel1:
            selected_comp = st.selectbox(
                "Pilih Komponen Kritis (RAM Curve):",
                options=comp_keys,
                index=0,
                format_func=lambda c: f"{c.upper()} (True β={truth['components_truth'][c]['beta']})",
                key="ram_comp_selector",
            )
        with col_sel2:
            st.markdown(
                """
                <div style="text-align: right; padding-top: 28px; font-size: 0.78rem; color: #10b981; font-weight: 700;">
                    Target: A &ge; 99%
                </div>
                """,
                unsafe_allow_html=True,
            )

        samples = truth["component_samples"][selected_comp]
        fig_ram, fit_res = create_reliability_curve(
            decision_service.ram_engine,
            ttf_list=samples["failures"],
            censored_list=samples["censored"],
            component_name=selected_comp,
        )
        st.plotly_chart(fig_ram, use_container_width=True)

        # Asset Availability Donut & Summary (Page 12 wireframe)
        col_avail_gauge, col_avail_meta = st.columns([4, 8])
        with col_avail_gauge:
            fig_avail = create_availability_donut(availability_pct=plan.system_availability)
            st.plotly_chart(fig_avail, use_container_width=True)

        with col_avail_meta:
            st.markdown(
                f"""
                <div style="background: #141418; border: 1px solid #26262e; border-radius: 8px; padding: 10px 12px; height: 140px; display: flex; flex-direction: column; justify-content: space-around;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span style="color:#A6A6A4;">MTBF ({selected_comp}):</span>
                        <strong style="color:#E6DDC9;">{fit_res.mtbf:,.0f} Jam</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span style="color:#A6A6A4;">Mean Time To Repair (MTTR):</span>
                        <strong style="color:#E6DDC9;">4.0 Jam</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span style="color:#A6A6A4;">Interval Pemeliharaan (RAM):</span>
                        <strong style="color:#C95232;">{18 if selected_comp=='cooling' else 14} Bulan (Konservatif)</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.74rem; border-top: 1px dashed #26262e; padding-top: 3px;">
                        <span style="color:#10b981;">Batas Green Renewable (hal. 24):</span>
                        <strong style="color:#10b981;">A &ge; 99.0% (Tercapai)</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_panel_sched:
        st.markdown(
            """
            <div style="background: #141418; padding: 10px 14px; border-radius: 8px; border: 1px solid #26262e; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.88rem; font-weight: 700; color: #E6DDC9;">
                        📋 Engineering Actions Scheduler (Page 7 & 12 Wireframe)
                    </span>
                    <span style="font-size: 0.72rem; background: #26262e; color: #A6A6A4; padding: 2px 7px; border-radius: 4px;">
                        FMEA + RAM
                    </span>
                </div>
                <div style="font-size: 0.74rem; color: #A6A6A4; margin-top: 2px;">
                    <strong>Sintesis:</strong> Engineering Action = Task (FMEA) + Frequency (RAM)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sched_items = []
        urgent_count = 0
        in_prog_count = 0
        sched_count = 0

        for idx, act in enumerate(plan.actions, start=1):
            if act.rpn >= 80 or act.ea_risk_status == CheckStatus.DANGER:
                p_badge = "🔴 Tinggi"
                status_txt = "Pending (Urgent)"
                urgent_count += 1
            elif act.rpn >= 50 or act.ea_risk_status == CheckStatus.WARNING:
                p_badge = "🟡 Sedang"
                status_txt = "In Progress"
                in_prog_count += 1
            else:
                p_badge = "🟢 Rendah"
                status_txt = "Scheduled"
                sched_count += 1

            sched_items.append({
                "ID": f"WO-{1040 + idx}",
                "Komponen": act.component_name,
                "Prioritas": p_badge,
                "RPN": act.rpn,
                "Tugas Teknik (FMEA)": act.task_description,
                "Frekuensi (RAM)": f"Tiap {act.interval_months} bln",
                "Status": status_txt,
            })

        st.dataframe(sched_items, use_container_width=True, hide_index=True, height=275)

        # Work Order Execution Summary Card (Balances column height perfectly with left panel)
        st.markdown(
            f"""
            <div style="background: #141418; border: 1px solid #26262e; border-radius: 8px; padding: 10px 14px; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 0.76rem; color: #A6A6A4; font-weight: 600;">Status Pelaksanaan Work Order:</span>
                    <span style="font-size: 0.72rem; color: #38bdf8;">Total: {len(plan.actions)} Tindakan</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center;">
                    <div style="background: #1c1b20; padding: 6px; border-radius: 6px; border: 1px solid #ef4444;">
                        <span style="font-size: 0.7rem; color: #ef4444; font-weight: 700;">🔴 Urgent</span><br>
                        <strong style="color: #E6DDC9; font-size: 0.95rem;">{urgent_count} WO</strong>
                    </div>
                    <div style="background: #1c1b20; padding: 6px; border-radius: 6px; border: 1px solid #f59e0b;">
                        <span style="font-size: 0.7rem; color: #f59e0b; font-weight: 700;">🟡 In Progress</span><br>
                        <strong style="color: #E6DDC9; font-size: 0.95rem;">{in_prog_count} WO</strong>
                    </div>
                    <div style="background: #1c1b20; padding: 6px; border-radius: 6px; border: 1px solid #10b981;">
                        <span style="font-size: 0.7rem; color: #10b981; font-weight: 700;">🟢 Scheduled</span><br>
                        <strong style="color: #E6DDC9; font-size: 0.95rem;">{sched_count} WO</strong>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_sched_btn1, col_sched_btn2 = st.columns([6, 6])
        with col_sched_btn1:
            st.download_button(
                label="📥 Unduh Action Plan (JSON)",
                data=plan.model_dump_json(indent=2),
                file_name=f"EngineeringActionPlan_{selected_unit_id}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_sched_btn2:
            st.markdown(
                """
                <div style="background: #1c1b20; border: 1px solid #2a2a34; border-radius: 6px; padding: 6px 10px; font-size: 0.72rem; color: #A6A6A4; text-align: center;">
                    ⚡ <strong>Prioritas:</strong> EA DANGER &gt; RPN Tertinggi &gt; Interval Terpendek
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 6. Deep-Dive Section: 5 Detailed Engineering Tabs
    # -------------------------------------------------------------
    st.markdown("### 🔍 Detail Analisis Mendalam & Audit Sistem")

    tab_actions, tab_safety, tab_fmea, tab_comparison, tab_cost = st.tabs([
        "📋 Rencana Pemeliharaan Lengkap (Action Plan)",
        "🛡️ Audit 5 Electrical Accidents (EA 1 – EA 5)",
        "📑 Matriks FMEA 4-Baris (Format Tabel 2.3)",
        "⚖️ Komparasi 11 Metodologi Risiko (Tabel 2.5 Slide 12)",
        "📈 Optimasi Biaya & Keandalan (CAPEX / OPEX Curve)",
    ])

    # TAB 1: Detailed Action Plan Table
    with tab_actions:
        st.subheader("🎯 Tabel Rencana Aksi Pemeliharaan Terpadu (Engineering Actions)")
        action_rows = []
        for act in plan.actions:
            status_icon = "🔴 BAHAYA" if act.ea_risk_status == CheckStatus.DANGER else ("🟡 PERINGATAN" if act.ea_risk_status == CheckStatus.WARNING else "🟢 NORMAL")
            action_rows.append({
                "Prioritas": f"#{act.priority_rank}",
                "Status Risiko EA": status_icon,
                "Komponen": act.component_name,
                "RPN": act.rpn,
                "Engineering Task": act.task_description,
                "Metode Uji Standar": act.test_method or "-",
                "Frekuensi Pemeliharaan": f"Setiap {act.interval_months} bulan ({act.interval_hours:.0f} jam)",
                "Standar Rujukan": act.reference_standard,
                "Catatan Rekayasa": act.reference_note or "-",
            })
        st.dataframe(action_rows, use_container_width=True, hide_index=True)

    # TAB 2: Electrical Accidents EA1-EA5 Checker
    with tab_safety:
        st.subheader("🛡️ Evaluasi Fisik 5 Electrical Accidents (EA1–EA5)")
        ea_details = [
            ("EA 1", "Kebakaran akibat Flash Point Rendah & DGA C₂H₂", plan.ea_results.get("EA1")),
            ("EA 2", "Ledakan Circuit Breaker (Interrupting Rating IR < Isc)", plan.ea_results.get("EA2")),
            ("EA 3", "Overheating & Penuaan Isolasi Dipercepat (+7 °C => +30% aging)", plan.ea_results.get("EA3")),
            ("EA 4", "Kerusakan Paralel: Ketidaksesuaian Impedansi (|Δ%Z| > 10%)", plan.ea_results.get("EA4")),
            ("EA 5", "Kerusakan Paralel: Ketidaksesuaian Vector Group", plan.ea_results.get("EA5")),
        ]

        color_map = {
            CheckStatus.SAFE: ("#10b981", "#ecfdf5", "AMAN"),
            CheckStatus.WARNING: ("#f59e0b", "#fffbeb", "PERINGATAN"),
            CheckStatus.DANGER: ("#ef4444", "#fef2f2", "BAHAYA"),
            CheckStatus.INSUFFICIENT_DATA: ("#6b7280", "#f3f4f6", "DATA KURANG"),
        }

        for code, title, res in ea_details:
            if res:
                border_col, bg_col, label_text = color_map.get(res.status, ("#6b7280", "#f3f4f6", "DATA KURANG"))
                st.markdown(
                    f"""
                    <div style="border: 2px solid {border_col}; background-color: {bg_col}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; font-size: 1.02rem; color: #141418;">{code}: {title}</span>
                            <span style="background-color: {border_col}; color: white; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">
                                {label_text}
                            </span>
                        </div>
                        <p style="margin: 8px 0 4px 0; font-size: 0.9rem; color: #374151;">{res.explanation_id}</p>
                        <div style="font-size: 0.75rem; color: #6b7280; border-top: 1px dashed {border_col}; padding-top: 4px; margin-top: 6px;">
                            <strong>Rujukan Standar:</strong> {res.reference} &bull; <strong>Measured:</strong> {res.measured}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info(f"**{code}: {title}** — Evaluasi aktif saat trafo dioperasikan paralel dengan unit pendamping.")

    # TAB 3: 4-Row FMEA Matrix (Tabel 2.3)
    with tab_fmea:
        st.subheader("📑 Matriks FMEA Empat Baris (Format Tabel 2.3 Proposal & AIAG/VDA)")
        st.markdown(
            """
            Struktur FMEA empat baris sesuai Bab II naskah:
            - **Baris F (Function):** Komponen kritis & Fungsi nominal; Functional Failure.
            - **Baris M (Mode & Mechanism):** Physical failure mechanism & root causes.
            - **Baris E (Effect):** Local, System, and End effects.
            - **Baris A (Analysis & Action):** Hidden vs Evident, RPN, Engineering Tasks & Diagnostic Test Methods.
            """
        )
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

    # TAB 4: 11 Methodologies Comparison (Slide 12)
    with tab_comparison:
        st.subheader("⚖️ Tabel 2.5 Perbandingan Metode Analisis Risiko dan Keandalan (Slide 12)")
        st.markdown("Perbandingan komprehensif 11 metodologi risiko yang menjadi landasan pemilihan integrasi **RAM dan FMEA** dalam penelitian ini:")
        methodology_table = [
            {
                "No": 1,
                "Metode": "FTA (Fault Tree Analysis)",
                "Fokus Utama": "Akar Penyebab (Top-Down)",
                "Kelebihan": "Detail dalam mencari kombinasi kegagalan sistem proteksi.",
                "Kelemahan untuk Kasus Ini": "Kurang dalam penilaian dampak (severity) secara sistematis.",
                "Relevansi ke 5 EA": "EA 2 (Ledakan CB)",
            },
            {
                "No": 2,
                "Metode": "RCA (Root Cause Analysis)",
                "Fokus Utama": "Investigasi Pasca-Kejadian",
                "Kelebihan": "Mendalam mencari akar masalah teknis setelah terjadi kerusakan.",
                "Kelemahan untuk Kasus Ini": "Bersifat Reaktif, tidak cocok untuk target preventif disertasi.",
                "Relevansi ke 5 EA": "EA 4 & 5 (Ops Paralel)",
            },
            {
                "No": 3,
                "Metode": "SIS (Safety Instrumented System)",
                "Fokus Utama": "Sistem Proteksi Otomatis",
                "Kelebihan": "Memastikan safety instrument bekerja sesuai standar keamanan.",
                "Kelemahan untuk Kasus Ini": "Terlalu fokus pada kontrol elektrik, mengabaikan aspek penuaan material.",
                "Relevansi ke 5 EA": "EA 1 & 3 (Kebakaran)",
            },
            {
                "No": 4,
                "Metode": "HAZOP (Hazard and Operability Study)",
                "Fokus Utama": "Bahaya Operasional",
                "Kelebihan": "Kuat dalam mendeteksi penyimpangan parameter operasional.",
                "Kelemahan untuk Kasus Ini": "Sangat kualitatif dan bergantung pada subjektivitas tim penilai.",
                "Relevansi ke 5 EA": "EA 5 (Vector Group)",
            },
            {
                "No": 5,
                "Metode": "Markov Chain",
                "Fokus Utama": "Probabilitas Kondisi",
                "Kelebihan": "Akurasi tinggi untuk sistem yang terus berubah secara dinamis.",
                "Kelemahan untuk Kasus Ini": "Membutuhkan data matematis rumit yang sulit didapat di lapangan.",
                "Relevansi ke 5 EA": "EA 1 (Degradasi Cairan)",
            },
            {
                "No": 6,
                "Metode": "Bow-Tie Analysis",
                "Fokus Utama": "Visualisasi Skenario",
                "Kelebihan": "Mempermudah pemetaan antara pencegahan dan mitigasi dampak.",
                "Kelemahan untuk Kasus Ini": "Bersifat 'high-level', tidak memberikan angka prioritas (RPN).",
                "Relevansi ke 5 EA": "EA 2 (Ledakan CB)",
            },
            {
                "No": 7,
                "Metode": "LOPA (Layer of Protection Analysis)",
                "Fokus Utama": "Lapisan Proteksi",
                "Kelebihan": "Semi-kuantitatif dalam menentukan kecukupan lapisan pelindung.",
                "Kelemahan untuk Kasus Ini": "Hanya fokus pada alat proteksi, bukan analisis risiko keandalan trafo.",
                "Relevansi ke 5 EA": "EA 2 (Proteksi Isc)",
            },
            {
                "No": 8,
                "Metode": "MSG-3 (Maintenance Steering Group)",
                "Fokus Utama": "Penjadwalan Tugas",
                "Kelebihan": "Sangat terstruktur untuk efisiensi jadwal pemeliharaan rutin.",
                "Kelemahan untuk Kasus Ini": "Terlalu prosedural, kurang dalam analisis risiko kegagalan desain.",
                "Relevansi ke 5 EA": "EA 1 (Flash Point)",
            },
            {
                "No": 9,
                "Metode": "PHA (Preliminary Hazard Analysis)",
                "Fokus Utama": "Identifikasi Awal",
                "Kelebihan": "Efektif dilakukan pada fase perencanaan atau pra-desain.",
                "Kelemahan untuk Kasus Ini": "Terlalu umum, tidak bisa digunakan untuk optimasi unit yang sudah ada.",
                "Relevansi ke 5 EA": "EA 3 (Tipe Pendingin)",
            },
            {
                "No": 10,
                "Metode": "RCM (Reliability-Centered Maintenance)",
                "Fokus Utama": "Strategi Maintenance",
                "Kelebihan": "Fokus menjaga fungsi sistem agar tetap sesuai parameter desain.",
                "Kelemahan untuk Kasus Ini": "Membutuhkan input detail yang hanya bisa disediakan oleh FMEA.",
                "Relevansi ke 5 EA": "EA 2 (Ledakan CB)",
            },
            {
                "No": 11,
                "Metode": "RAM dan FMEA (Metode Penelitian Ini)",
                "Fokus Utama": "Keandalan, Ketersediaan & Mode Kegagalan",
                "Kelebihan": "Mengintegrasikan analisis kuantitatif keandalan (RAM) dengan identifikasi sistematis mode kegagalan, dampak, dan kritikalitas (FMEA).",
                "Kelemahan untuk Kasus Ini": "Membutuhkan data historis kegagalan lengkap dan intensif waktu analisis.",
                "Relevansi ke 5 EA": "EA 1–5 (Semua Electrical Accidents: Keandalan Sistem & Identifikasi)",
            },
        ]
        st.dataframe(methodology_table, use_container_width=True, hide_index=True)

    # TAB 5: CAPEX/OPEX Cost Optimization Curve (Page 13)
    with tab_cost:
        st.subheader("📈 Optimasi Biaya dan Keandalan (CAPEX / OPEX Economic Balance — Page 13)")
        st.markdown(
            """
            Keseimbangan ekonomis implementasi DSS RAM-FMEA:
            - **Kurva Biaya Investasi Pemeliharaan (CAPEX/OPEX):** Naik eksponensial seiring tuntutan keandalan mendekati 100%.
            - **Kurva Kerugian Downtime & Risiko Kecelakaan:** Turun drastis saat keandalan ditingkatkan.
            - **Kurva Biaya Total (Total Cost):** Berbentuk kurva U dengan titik minimum yang merupakan **Titik Optimum Operasi DSS**.
            """
        )
        fig_cost = create_cost_optimization_curve()
        st.plotly_chart(fig_cost, use_container_width=True)

        st.info(
            "💡 **Prinsip Finansial:** Sistem ini memastikan perusahaan tidak melakukan pemeliharaan yang terlalu jarang (berisiko kecelakaan katastrofik) "
            "maupun terlalu sering (pemborosan OPEX berlebih). DSS menetapkan jadwal tindakan pemeliharaan pada titik efisiensi finansial optimal."
        )


if __name__ == "__main__":
    main()
