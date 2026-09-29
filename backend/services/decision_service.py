"""
Decision Service — Orchestrator for Integrated RAM-FMEA Decision Support System.
Based on Prabowo Soetadji - Proposal Bab I-III Rev3.

Synthesizes:
1. RAM Engine: Engineering Frequency
2. FMEA Engine: Engineering Tasks, RPN, 4-Row Structure
3. EA Checker: Electrical Accident deterministic verification (EA1–EA5)

Deliverable:
Engineering Action = Engineering Task (FMEA) + Engineering Frequency (RAM).
Priority Order:
1. EA DANGER first
2. Highest RPN next (descending)
3. Shortest Maintenance Interval next (ascending)
"""

from typing import Any
from backend.config_loader import ThresholdRegistry, load_thresholds
from backend.engines.fmea_engine import FMEAEngine
from backend.engines.ram_engine import RAMEngine
from backend.safety.ea_checker import (
    check_breaker_interrupting_capacity,
    check_cooling_adequacy,
    check_dga_fire_risk,
    check_parallel_impedance,
    check_vector_group_compatibility,
)
from backend.schemas.common import CheckResult, CheckStatus
from backend.schemas.decision_schemas import (
    EngineeringAction,
    EngineeringActionPlan,
    UnscheduledTask,
)


class DecisionService:
    """Decision orchestrator producing EngineeringActionPlan."""

    def __init__(self, config: ThresholdRegistry | None = None):
        self.config = config or load_thresholds()
        self.ram_engine = RAMEngine(config=self.config)
        self.fmea_engine = FMEAEngine()

    def _map_component_ea_status(
        self,
        component_id: str,
        ea_results: dict[str, CheckResult],
    ) -> CheckStatus:
        """Map Electrical Accident risk status to a specific physical component."""
        # EA1 maps to insulation system
        if component_id == "insulation" and "EA1" in ea_results:
            if ea_results["EA1"].status == CheckStatus.DANGER:
                return CheckStatus.DANGER
            if ea_results["EA1"].status == CheckStatus.WARNING:
                return CheckStatus.WARNING

        # EA3 maps to cooling system & winding thermal aging
        if component_id in ["cooling", "winding"] and "EA3" in ea_results:
            if ea_results["EA3"].status == CheckStatus.DANGER:
                return CheckStatus.DANGER
            if ea_results["EA3"].status == CheckStatus.WARNING:
                return CheckStatus.WARNING

        return CheckStatus.SAFE

    def generate_plan(
        self,
        unit_data: dict[str, Any],
        companion_unit_data: dict[str, Any] | None = None,
        target_reliability: float = 0.75,
        t_eval_months: float = 5.0,
        require_failure_history: bool = False,
    ) -> EngineeringActionPlan:
        """
        Generate integrated Engineering Action Plan for a transformer unit.
        """
        unit_id = unit_data["transformer_id"]
        util_code = unit_data.get("utility_code", "UTIL-GEN")
        nameplate = unit_data["nameplate"]
        op_cond = unit_data["operating_condition"]
        history = unit_data.get("history", {})
        failures = history.get("failures", [])

        # 1. Run EA Safety Checks
        ea_results: dict[str, CheckResult] = {}

        # EA1: DGA & Flash Point
        ea_results["EA1"] = check_dga_fire_risk(
            c2h2_ppm=op_cond.get("c2h2_ppm"),
            fluid_type=nameplate.get("fluid_type"),
            flash_point_c=nameplate.get("flash_point_c"),
            thresholds=self.config,
        )

        # EA2: Interrupting Rating vs Short Circuit
        ea_results["EA2"] = check_breaker_interrupting_capacity(
            ir_ka=op_cond.get("breaker_ir_ka"),
            isc_ka=op_cond.get("breaker_isc_ka"),
            thresholds=self.config,
        )

        # EA3: Cooling adequacy & aging acceleration
        ea_results["EA3"] = check_cooling_adequacy(
            cooling_type=nameplate.get("cooling_type"),
            load_kva=op_cond.get("load_kva"),
            rated_kva=nameplate.get("rated_kva"),
            ambient_temp_c=op_cond.get("ambient_temp_c"),
            thresholds=self.config,
        )

        # Optional parallel checks if companion unit provided
        if companion_unit_data:
            comp_np = companion_unit_data["nameplate"]
            ea_results["EA4"] = check_parallel_impedance(
                z_pct_a=nameplate.get("impedance_z_pct"),
                z_pct_b=comp_np.get("impedance_z_pct"),
                kva_a=nameplate.get("rated_kva"),
                kva_b=comp_np.get("rated_kva"),
                thresholds=self.config,
            )
            ea_results["EA5"] = check_vector_group_compatibility(
                vector_a=nameplate.get("vector_group"),
                vector_b=comp_np.get("vector_group"),
                thresholds=self.config,
            )

        # Overall safety status
        statuses = [res.status for res in ea_results.values()]
        if CheckStatus.DANGER in statuses:
            overall_status = CheckStatus.DANGER
        elif CheckStatus.WARNING in statuses:
            overall_status = CheckStatus.WARNING
        elif CheckStatus.INSUFFICIENT_DATA in statuses:
            overall_status = CheckStatus.INSUFFICIENT_DATA
        else:
            overall_status = CheckStatus.SAFE

        # 2. Extract failure counts per component
        comp_failure_counts: dict[str, int] = {}
        for f in failures:
            cid = f.get("component_id")
            if cid:
                comp_failure_counts[cid] = comp_failure_counts.get(cid, 0) + 1

        # 3. Retrieve FMEA Matrix
        matrix = self.fmea_engine.get_default_matrix()

        actions: list[EngineeringAction] = []
        unscheduled: list[UnscheduledTask] = []

        # 4. Synthesize FMEA Task + RAM Frequency
        for row in matrix.rows:
            cid = row.row_f.component_id
            fail_count = comp_failure_counts.get(cid, 0)

            if require_failure_history and fail_count == 0:
                unscheduled.append(
                    UnscheduledTask(
                        task_id=f"UT-{row.id}",
                        component_id=cid,
                        component_name=row.row_f.component_name,
                        fmea_row_id=row.id,
                        task_description=row.row_a.engineering_task,
                        reason=f"Data kegagalan untuk komponen '{cid}' belum mencukupi (failures = 0).",
                    )
                )
                continue

            # Calculate frequency from RAM engine
            interval_res = self.ram_engine.maintenance_interval(
                t=t_eval_months,
                target_reliability=target_reliability,
                unit="months",
            )

            hours_per_month = self.config.meta.hours_per_month.value
            interval_hrs = interval_res.interval_months * hours_per_month

            ea_status = self._map_component_ea_status(cid, ea_results)

            actions.append(
                EngineeringAction(
                    action_id=f"ACT-{row.id}",
                    component_id=cid,
                    component_name=row.row_f.component_name,
                    fmea_row_id=row.id,
                    task_description=row.row_a.engineering_task,
                    test_method=row.row_a.test_method,
                    interval_months=interval_res.interval_months,
                    interval_hours=interval_hrs,
                    target_reliability=target_reliability,
                    rpn=row.row_a.rpn,
                    ea_risk_status=ea_status,
                    priority_rank=0,  # assigned after sorting
                    source="RAM Eq. (2.2) & FMEA Table 3.1",
                    reference_standard=row.row_a.reference_standard,
                    reference_note=row.row_a.reference_note,
                )
            )

        # 5. Prioritize Actions: EA DANGER first -> Highest RPN -> Shortest Interval
        def sort_key(act: EngineeringAction) -> tuple[int, int, int]:
            # DANGER gets priority 0, WARNING gets 1, others 2
            ea_priority = 0 if act.ea_risk_status == CheckStatus.DANGER else (
                1 if act.ea_risk_status == CheckStatus.WARNING else 2
            )
            # -act.rpn gives descending order (highest RPN first)
            # act.interval_months gives ascending order (shortest interval first)
            return (ea_priority, -act.rpn, act.interval_months)

        actions.sort(key=sort_key)

        for rank, act in enumerate(actions, start=1):
            act.priority_rank = rank

        # 6. Overall system availability computation
        # Baseline using switchgear example MTBF and MTTR
        avail = self.ram_engine.availability(mtbf=18.0, mttr=0.033)

        summary_notes = [
            f"Evaluasi keselamatan: {len(ea_results)} Electrical Accident checks dilakukan.",
            f"Engineering Actions teridentifikasi: {len(actions)} tugas terjadwal, {len(unscheduled)} tugas belum terjadwal.",
            f"Standar rujukan naskah Bab I-III Proposal Rev3 (Prabowo Soetadji).",
        ]

        return EngineeringActionPlan(
            transformer_id=unit_id,
            utility_code=util_code,
            overall_safety_status=overall_status,
            ea_results=ea_results,
            actions=actions,
            unscheduled_tasks=unscheduled,
            system_availability=round(avail * 100.0, 2),
            summary_notes=summary_notes,
        )
