"""Procedural Flow Engine Service"""
import logging
from typing import Dict, List, Any
from .data_loader import data_loader

logger = logging.getLogger(__name__)

class ProceduralFlowService:
    """Service for case timeline and procedural flow prediction"""
    
    # Timeline data based on case type and court
    TIMELINE_DATA = {
        "criminal": {
            "district": {
                "stages": [
                    {"stage": "FIR Filing", "duration": 1, "delay_prob": 5},
                    {"stage": "Investigation", "duration": 3, "delay_prob": 15},
                    {"stage": "First Hearing", "duration": 2, "delay_prob": 35},
                    {"stage": "Chargesheet", "duration": 2, "delay_prob": 20},
                    {"stage": "Evidence", "duration": 8, "delay_prob": 45},
                    {"stage": "Arguments", "duration": 3, "delay_prob": 30},
                    {"stage": "Judgment", "duration": 1, "delay_prob": 25}
                ],
                "total_months": 20,
                "delay_likelihood": 65
            },
            "high": {
                "stages": [
                    {"stage": "Appeal Filing", "duration": 2, "delay_prob": 20},
                    {"stage": "Admission", "duration": 3, "delay_prob": 50},
                    {"stage": "Arguments", "duration": 4, "delay_prob": 40},
                    {"stage": "Judgment", "duration": 2, "delay_prob": 35}
                ],
                "total_months": 30,
                "delay_likelihood": 72
            }
        },
        "civil": {
            "district": {
                "stages": [
                    {"stage": "Filing", "duration": 1, "delay_prob": 8},
                    {"stage": "Admission", "duration": 2, "delay_prob": 40},
                    {"stage": "Evidence", "duration": 12, "delay_prob": 50},
                    {"stage": "Arguments", "duration": 4, "delay_prob": 35},
                    {"stage": "Judgment", "duration": 2, "delay_prob": 40}
                ],
                "total_months": 21,
                "delay_likelihood": 72
            }
        }
    }
    
    async def predict_timeline(self, case_type: str, court: str, state: str) -> Dict[str, Any]:
        """
        Predict case timeline
        
        Args:
            case_type: "criminal" or "civil"
            court: "district", "high", or "supreme"
            state: State name
            
        Returns:
            Timeline prediction with stages
        """
        try:
            evidence = self._get_backlog_evidence(case_type, court, state)
            if evidence:
                return self._build_data_backed_timeline(case_type, court, state, evidence)

            # Get timeline data when no matching public backlog row exists.
            timeline_key = court if court in ["district", "high"] else "district"
            case_key = case_type if case_type in ["criminal", "civil"] else "criminal"
            
            if case_key not in self.TIMELINE_DATA or timeline_key not in self.TIMELINE_DATA[case_key]:
                timeline_data = self.TIMELINE_DATA["criminal"]["district"]
            else:
                timeline_data = self.TIMELINE_DATA[case_key][timeline_key]
            
            stages = timeline_data["stages"]
            total_months = timeline_data["total_months"]
            delay_likelihood = timeline_data["delay_likelihood"]
            
            return {
                "case_type": case_type,
                "court": court,
                "state": state,
                "expected_duration": total_months,
                "worst_case_duration": int(total_months * 1.5),
                "delay_probability": delay_likelihood,
                "stages": stages,
                "delay_factors": self._get_delay_factors(),
                "stage_wise_risk": self._calculate_stage_risk(stages)
            }
            
        except Exception as e:
            logger.error(f"Error predicting timeline: {str(e)}")
            return {"error": str(e)}

    def _get_backlog_evidence(self, case_type: str, court: str, state: str) -> Dict[str, Any] | None:
        """Find a matching NDAP high-court row and derive measurable backlog signals."""
        frame = data_loader.court_backlog_data
        if frame is None or court.lower() not in {"high", "supreme"}:
            return None

        state_key = state.strip().lower()
        type_key = case_type.strip().lower()
        rows = frame[
            frame["State"].astype(str).str.strip().str.lower().eq(state_key)
            & frame["Court case type"].astype(str).str.strip().str.lower().eq(type_key)
        ]
        if rows.empty:
            rows = frame[
                frame["State"].astype(str).str.strip().str.lower().eq(state_key)
                & frame["Court case type"].astype(str).str.strip().str.lower().eq("total")
            ]
        if rows.empty:
            return None

        row = rows.iloc[0]
        age_columns = [
            "Cases pending for a period of 5 to 10 years at high court",
            "Cases pending for a period of 10 to 20 years at high court",
            "Cases pending for a period of 20 to 30 years at high court",
            "Cases pending for a period of more than 30 years at high court",
        ]
        total = float(row.get("Pending cases in high court", 0) or 0)
        aged = sum(float(row.get(column, 0) or 0) for column in age_columns)
        instituted = float(row.get("Cases that were instituted in last month", 0) or 0)
        disposed = float(row.get("Cases that were disposed in last month", 0) or 0)
        return {
            "pending_cases": round(total, 2),
            "aged_cases": round(aged, 2),
            "aged_ratio": aged / total if total else 0,
            "monthly_instituted": round(instituted, 2),
            "monthly_disposed": round(disposed, 2),
            "source": "NDAP_REPORT_7149.csv",
        }

    def _build_data_backed_timeline(self, case_type: str, court: str, state: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Convert observed backlog and throughput into transparent timeline estimates."""
        aged_ratio = min(1.0, max(0.0, evidence["aged_ratio"]))
        throughput = evidence["monthly_instituted"] + evidence["monthly_disposed"]
        pressure = evidence["pending_cases"] / max(throughput, 1)
        expected_duration = max(6, min(180, round(12 + pressure * 0.35)))
        delay_probability = round(min(95, max(5, aged_ratio * 70 + min(25, pressure / 12))), 1)
        stages = [
            {"stage": "Filing and Admission", "duration": max(1, round(expected_duration * 0.08)), "delay_prob": round(delay_probability * 0.55, 1)},
            {"stage": "Evidence and Hearings", "duration": max(1, round(expected_duration * 0.52)), "delay_prob": round(delay_probability, 1)},
            {"stage": "Arguments", "duration": max(1, round(expected_duration * 0.22)), "delay_prob": round(delay_probability * 0.82, 1)},
            {"stage": "Judgment", "duration": max(1, round(expected_duration * 0.18)), "delay_prob": round(delay_probability * 0.68, 1)},
        ]
        return {
            "case_type": case_type,
            "court": court,
            "state": state,
            "expected_duration": expected_duration,
            "worst_case_duration": min(240, round(expected_duration * (1 + delay_probability / 100))),
            "delay_probability": delay_probability,
            "stages": stages,
            "delay_factors": {
                "court_backlog": round(min(60, pressure / 10), 1),
                "aged_pending_cases": round(aged_ratio * 100, 1),
                "monthly_throughput": round(min(30, throughput / max(evidence["pending_cases"], 1) * 100), 1),
                "other": 10,
            },
            "stage_wise_risk": self._calculate_stage_risk(stages),
            "data_evidence": evidence,
        }
    
    def _get_delay_factors(self) -> Dict[str, float]:
        """Get delay contributing factors"""
        return {
            "court_backlog": 35,
            "judge_availability": 25,
            "adjournments": 20,
            "evidence_complexity": 15,
            "other": 5
        }
    
    def _calculate_stage_risk(self, stages: List[Dict]) -> Dict[str, float]:
        """Calculate stage-wise risk"""
        risk_map = {}
        for stage in stages:
            risk_map[stage["stage"]] = stage["delay_prob"]
        return risk_map
