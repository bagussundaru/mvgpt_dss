"""
Synthetic Data Generator for MV-GPT DSS.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3 (hal. 23, 61, 65).

Key specifications:
- 30 units, 10 years observation history (87,600 hours).
- Seed: 20260929 (fixed and reproducible).
- Voltage range: 1–35 kV only.
- Prior beta distributions per component:
  - Winding: beta = 1.8 (wear-out)
  - Insulation: beta = 2.2 (wear-out / aging)
  - OLTC: beta = 1.4 (mechanical wear-out)
  - Bushing: beta = 0.8 (infant mortality)
  - Cooling: beta = 1.0 (random failure)
  - Core: beta = 0.9 (infant mortality)
- Right-censoring support for units surviving observation window.
- Tropical climate humidity (70–95% RH).
- Five deliberate EA trigger cases recorded in _truth.json.
"""

import json
from pathlib import Path
from typing import Any
import numpy as np


COMPONENTS_TRUTH: dict[str, dict[str, float]] = {
    "winding": {"beta": 1.8, "eta": 55000.0},
    "insulation": {"beta": 2.2, "eta": 50000.0},
    "oltc": {"beta": 1.4, "eta": 45000.0},
    "bushing": {"beta": 0.8, "eta": 60000.0},
    "cooling": {"beta": 1.0, "eta": 40000.0},
    "core": {"beta": 0.9, "eta": 70000.0},
}


def generate_synthetic_dataset(
    n_units: int = 30,
    observation_years: int = 10,
    seed: int = 20260929,
    output_dir: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Generate synthetic dataset of medium voltage green transformers.
    Saves dataset and ground-truth parameters for roundtrip validation.
    """
    np.random.seed(seed)
    hours_per_year = 8760.0
    total_obs_hours = observation_years * hours_per_year

    units: list[dict[str, Any]] = []
    component_samples: dict[str, dict[str, list[float]]] = {
        comp: {"failures": [], "censored": []} for comp in COMPONENTS_TRUTH
    }

    # Generate stratified quantiles per component to ensure robust parameter recovery
    comp_quantiles: dict[str, np.ndarray] = {}
    for comp in COMPONENTS_TRUTH:
        q = (np.arange(1, n_units + 1) - 0.5) / n_units + np.random.uniform(
            -0.25 / n_units, 0.25 / n_units, size=n_units
        )
        np.random.shuffle(q)
        comp_quantiles[comp] = q

    # Generate baseline data for 30 units
    for idx in range(1, n_units + 1):
        unit_id = f"TX-{idx:02d}"
        util_code = f"UTIL-{'A' if idx <= 10 else ('B' if idx <= 20 else 'C')}"

        # Nameplate within 1-35 kV
        rated_kva = float(np.random.choice([630.0, 1000.0, 1250.0, 1600.0, 2000.0, 2500.0]))
        primary_kv = float(np.random.choice([20.0, 22.0, 33.0, 11.0]))
        secondary_kv = 0.4
        z_pct = round(float(np.random.uniform(4.5, 6.5)), 2)
        fluid_type = str(np.random.choice(["synthetic_ester", "natural_ester", "mineral"], p=[0.6, 0.3, 0.1]))
        fp_c = 275.0 if fluid_type == "synthetic_ester" else (310.0 if fluid_type == "natural_ester" else 150.0)
        vector_grp = "Dyn11"
        cooling = str(np.random.choice(["ONAN", "ONAF", "OFAF"], p=[0.7, 0.2, 0.1]))

        # Normal operating condition
        load_kva = round(rated_kva * float(np.random.uniform(0.65, 0.85)), 1)
        amb_temp = round(float(np.random.uniform(28.0, 34.0)), 1)
        amb_rh = round(float(np.random.uniform(75.0, 90.0)), 1)
        c2h2 = round(float(np.random.uniform(0.5, 2.5)), 2)
        isc_ka = 16.0
        ir_ka = 25.0  # safe by default

        unit_failures = []
        # Simulate component failure times via Weibull inverse transform
        for comp, params in COMPONENTS_TRUTH.items():
            b = params["beta"]
            e = params["eta"]

            u = float(comp_quantiles[comp][idx - 1])
            ttf = e * ((-np.log(1.0 - u)) ** (1.0 / b))

            if ttf < total_obs_hours:
                component_samples[comp]["failures"].append(ttf)
                unit_failures.append({
                    "component_id": comp,
                    "ttf_hours": round(ttf, 1),
                    "downtime_hours": round(float(np.random.uniform(12.0, 48.0)), 1),
                    "ambient_rh_pct": amb_rh,
                })
            else:
                component_samples[comp]["censored"].append(total_obs_hours)

        units.append({
            "transformer_id": unit_id,
            "utility_code": util_code,
            "nameplate": {
                "rated_kva": rated_kva,
                "primary_kv": primary_kv,
                "secondary_kv": secondary_kv,
                "impedance_z_pct": z_pct,
                "vector_group": vector_grp,
                "cooling_type": cooling,
                "fluid_type": fluid_type,
                "flash_point_c": fp_c,
            },
            "operating_condition": {
                "load_kva": load_kva,
                "ambient_temp_c": amb_temp,
                "ambient_rh_pct": amb_rh,
                "c2h2_ppm": c2h2,
                "breaker_ir_ka": ir_ka,
                "breaker_isc_ka": isc_ka,
            },
            "history": {
                "observation_hours": total_obs_hours,
                "failures": unit_failures,
            },
        })

    # =========================================================================
    # Insert 5 Deliberate Electrical Accident (EA) Triggers
    # =========================================================================

    # EA 1 Trigger: Unit TX-11 high C2H2
    units[10]["operating_condition"]["c2h2_ppm"] = 7.0  # > 5.0 ppm threshold

    # EA 2 Trigger: Unit TX-12 exact dissertation p.16 example (IR 16 kA vs Isc 20 kA)
    units[11]["operating_condition"]["breaker_ir_ka"] = 16.0
    units[11]["operating_condition"]["breaker_isc_ka"] = 20.0

    # EA 3 Trigger: Unit TX-13 ONAN with 115% loading at high ambient
    units[12]["nameplate"]["cooling_type"] = "ONAN"
    units[12]["nameplate"]["rated_kva"] = 1000.0
    units[12]["operating_condition"]["load_kva"] = 1150.0  # 115%
    units[12]["operating_condition"]["ambient_temp_c"] = 38.0

    # EA 4 Trigger: Unit TX-05 & TX-06 with relative %Z difference > 10%
    units[4]["nameplate"]["impedance_z_pct"] = 5.0
    units[5]["nameplate"]["impedance_z_pct"] = 6.0  # relative diff = 1.0 / 5.5 = 18.18%

    # EA 5 Trigger: Unit TX-07 & TX-08 with different vector groups
    units[6]["nameplate"]["vector_group"] = "Dyn11"
    units[7]["nameplate"]["vector_group"] = "Dyn1"  # 10 hours difference (300 deg)

    parallel_pairs = [
        {
            "pair_id": "PAIR-01",
            "unit_a_id": "TX-05",
            "unit_b_id": "TX-06",
            "intended_accident": "EA4",
            "description": "%Z mismatch (5.0% vs 6.0% -> 18.18% diff)",
        },
        {
            "pair_id": "PAIR-02",
            "unit_a_id": "TX-07",
            "unit_b_id": "TX-08",
            "intended_accident": "EA5",
            "description": "Vector group mismatch (Dyn11 vs Dyn1 -> 300 deg shift)",
        },
    ]

    expected_ea_triggers = {
        "EA1": {
            "unit_id": "TX-11",
            "expected_status": "DANGER",
            "trigger_condition": "c2h2_ppm = 7.0 > 5.0 ppm (Dissertation p.16)",
        },
        "EA2": {
            "unit_id": "TX-12",
            "expected_status": "DANGER",
            "trigger_condition": "ir_ka = 16.0 < isc_ka = 20.0 (Dissertation p.16 fixture)",
        },
        "EA3": {
            "unit_id": "TX-13",
            "expected_status": "DANGER",
            "trigger_condition": "ONAN at 115% load, ambient 38°C -> excess hotspot & aging acceleration",
        },
        "EA4": {
            "pair_id": "PAIR-01",
            "unit_a_id": "TX-05",
            "unit_b_id": "TX-06",
            "expected_status": "DANGER",
            "trigger_condition": "%Z relative diff 18.18% > 10.0%",
        },
        "EA5": {
            "pair_id": "PAIR-02",
            "unit_a_id": "TX-07",
            "unit_b_id": "TX-08",
            "expected_status": "DANGER",
            "trigger_condition": "Vector Dyn11 vs Dyn1 -> clock difference 10 != 0",
        },
    }

    dataset = {
        "metadata": {
            "generator": "MV-GPT DSS Dummy Generator",
            "seed": seed,
            "n_units": n_units,
            "observation_years": observation_years,
            "total_observation_hours": total_obs_hours,
        },
        "transformers": units,
        "parallel_pairs": parallel_pairs,
    }

    truth = {
        "seed": seed,
        "n_units": n_units,
        "observation_years": observation_years,
        "components_truth": COMPONENTS_TRUTH,
        "component_samples": component_samples,
        "expected_ea_triggers": expected_ea_triggers,
    }

    if output_dir:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        data_file = out_p / "dummy_transformers.json"
        truth_file = out_p / "dummy_transformers_truth.json"

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
        with open(truth_file, "w", encoding="utf-8") as f:
            json.dump(truth, f, indent=2)

    return dataset, truth


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data"
    generate_synthetic_dataset(output_dir=data_dir)
    print(f"Generated synthetic dataset and truth to {data_dir}")
