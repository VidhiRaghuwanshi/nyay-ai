"""Case Prediction Service - Predicts delay and success rate from judicial dataset"""
import logging
import math
from typing import Dict, Any, List, Optional
from .data_loader import data_loader

logger = logging.getLogger(__name__)


class CasePredictionService:
    """Predict case delay and success rate using judicial delay dataset"""

    def __init__(self):
        self.data_loader = data_loader
        self._build_model()

    def _build_model(self):
        """Build prediction lookup tables from dataset"""
        cases = self.data_loader.get_all_cases()
        if not cases:
            self._stats = {}
            return

        # Build aggregated statistics by (case_type, court_level, state)
        self._stats = {}
        self._global_stats = {
            "total_cases": 0,
            "total_delay": 0,
            "total_hearings": 0,
            "total_disposal": 0,
        }

        for case in cases:
            ct = case.get("case_type", "Unknown").lower()
            cl = case.get("court_level", "District").lower()
            st = case.get("state", "Unknown").lower()
            delay = case.get("delay_months", 30)
            hearings = case.get("number_of_hearings", 15)
            workload = case.get("judge_workload", 400)
            disposal = case.get("historical_disposal_rate", 0.5)

            self._global_stats["total_cases"] += 1
            self._global_stats["total_delay"] += delay
            self._global_stats["total_hearings"] += hearings
            self._global_stats["total_disposal"] += disposal

            # Multi-level aggregation
            for key in [
                (ct,),
                (ct, cl),
                (ct, st),
                (ct, cl, st),
                (cl,),
                (st,),
            ]:
                if key not in self._stats:
                    self._stats[key] = {
                        "count": 0,
                        "delay_sum": 0,
                        "delay_sq_sum": 0,
                        "hearings_sum": 0,
                        "workload_sum": 0,
                        "disposal_sum": 0,
                        "delays": [],
                    }
                s = self._stats[key]
                s["count"] += 1
                s["delay_sum"] += delay
                s["delay_sq_sum"] += delay * delay
                s["hearings_sum"] += hearings
                s["workload_sum"] += workload
                s["disposal_sum"] += disposal
                if len(s["delays"]) < 500:  # cap memory
                    s["delays"].append(delay)

    def predict(self, case_type: str, court_level: str, state: str,
                hearings: Optional[int] = None, workload: Optional[int] = None) -> Dict[str, Any]:
        """Predict delay and success rate for a case"""
        try:
            ct = case_type.lower()
            cl = court_level.lower()
            st = state.lower()

            # Find best matching stats (most specific first)
            stats = None
            match_level = "global"
            for key, label in [
                ((ct, cl, st), "exact"),
                ((ct, cl), "type+court"),
                ((ct, st), "type+state"),
                ((ct,), "type"),
                ((cl,), "court"),
                ((st,), "state"),
            ]:
                if key in self._stats and self._stats[key]["count"] >= 5:
                    stats = self._stats[key]
                    match_level = label
                    break

            if not stats:
                # Fallback to global
                total = self._global_stats["total_cases"] or 1
                avg_delay = self._global_stats["total_delay"] / total
                avg_disposal = self._global_stats["total_disposal"] / total
                stats = {
                    "count": total,
                    "delay_sum": self._global_stats["total_delay"],
                    "delay_sq_sum": avg_delay * avg_delay * total,
                    "hearings_sum": self._global_stats["total_hearings"],
                    "workload_sum": 400 * total,
                    "disposal_sum": self._global_stats["total_disposal"],
                    "delays": [],
                }

            n = stats["count"]
            avg_delay = stats["delay_sum"] / n
            avg_hearings = stats["hearings_sum"] / n
            avg_workload = stats["workload_sum"] / n
            avg_disposal = stats["disposal_sum"] / n

            # Variance and std dev for delay
            variance = (stats["delay_sq_sum"] / n) - (avg_delay * avg_delay)
            std_delay = math.sqrt(max(0, variance))

            # Adjust prediction based on optional inputs
            predicted_delay = avg_delay
            if hearings is not None:
                hearing_factor = (hearings - avg_hearings) / max(avg_hearings, 1) * 0.3
                predicted_delay += avg_delay * hearing_factor
            if workload is not None:
                workload_factor = (workload - avg_workload) / max(avg_workload, 1) * 0.2
                predicted_delay += avg_delay * workload_factor

            predicted_delay = max(1, round(predicted_delay, 1))

            # Success rate derived from disposal rate and delay
            base_success = avg_disposal * 100
            delay_penalty = max(0, (predicted_delay - 24) * 0.5)
            success_rate = min(95, max(10, base_success - delay_penalty))

            # Confidence based on sample size and match specificity
            confidence_map = {"exact": 92, "type+court": 85, "type+state": 82, "type": 75, "court": 65, "state": 60, "global": 50}
            base_confidence = confidence_map.get(match_level, 50)
            sample_bonus = min(15, n / 50)
            confidence = min(98, base_confidence + sample_bonus)

            # Percentile calculation
            delays = stats.get("delays", [])
            percentile_25 = sorted(delays)[len(delays) // 4] if delays else predicted_delay * 0.7
            percentile_75 = sorted(delays)[3 * len(delays) // 4] if delays else predicted_delay * 1.3
            percentile_90 = sorted(delays)[int(len(delays) * 0.9)] if delays else predicted_delay * 1.6

            # Contributing factors
            factors = self._get_contributing_factors(ct, cl, st, predicted_delay, avg_delay)

            # Get comparable cases from dataset
            comparable = self._get_comparable_cases(ct, cl, st, limit=5)

            return {
                "predicted_delay_months": predicted_delay,
                "success_rate": round(success_rate, 1),
                "confidence": round(confidence, 1),
                "match_level": match_level,
                "sample_size": n,
                "statistics": {
                    "avg_delay": round(avg_delay, 1),
                    "std_delay": round(std_delay, 1),
                    "min_delay": round(percentile_25, 1),
                    "max_delay": round(percentile_90, 1),
                    "median_delay": round((percentile_25 + percentile_75) / 2, 1),
                    "avg_hearings": round(avg_hearings, 1),
                    "avg_disposal_rate": round(avg_disposal, 3),
                },
                "percentiles": {
                    "p25": round(percentile_25, 1),
                    "p50": round((percentile_25 + percentile_75) / 2, 1),
                    "p75": round(percentile_75, 1),
                    "p90": round(percentile_90, 1),
                },
                "contributing_factors": factors,
                "comparable_cases": comparable,
                "risk_level": "High" if predicted_delay > 40 else "Medium" if predicted_delay > 20 else "Low",
            }

        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return {"error": str(e)}

    def _get_contributing_factors(self, ct, cl, st, predicted, avg) -> List[Dict]:
        """Get factors contributing to the prediction"""
        factors = []

        # Court level impact
        court_delays = {"supreme": 35, "high": 30, "district": 28}
        court_impact = court_delays.get(cl, 30)
        factors.append({
            "factor": "Court Level",
            "impact": round(min(40, court_impact), 1),
            "direction": "negative" if court_impact > 30 else "positive",
            "detail": f"{cl.title()} courts average {court_impact} months"
        })

        # Case type impact
        type_key = (ct,)
        if type_key in self._stats:
            type_avg = self._stats[type_key]["delay_sum"] / self._stats[type_key]["count"]
            global_avg = self._global_stats["total_delay"] / max(self._global_stats["total_cases"], 1)
            diff = ((type_avg - global_avg) / max(global_avg, 1)) * 100
            factors.append({
                "factor": "Case Type",
                "impact": round(min(35, abs(diff) + 10), 1),
                "direction": "negative" if diff > 5 else "positive" if diff < -5 else "neutral",
                "detail": f"{ct.title()} cases average {type_avg:.0f} months"
            })

        # State impact
        state_key = (st,)
        if state_key in self._stats:
            state_avg = self._stats[state_key]["delay_sum"] / self._stats[state_key]["count"]
            factors.append({
                "factor": "State Judiciary",
                "impact": round(min(30, abs(state_avg - avg) / max(avg, 1) * 100 + 10), 1),
                "direction": "negative" if state_avg > avg else "positive",
                "detail": f"{st.title()} average: {state_avg:.0f} months"
            })

        # Judge workload
        factors.append({
            "factor": "Judge Workload",
            "impact": 20,
            "direction": "negative",
            "detail": "Average workload impacts scheduling delays"
        })

        # Evidence complexity
        factors.append({
            "factor": "Evidence Complexity",
            "impact": 15,
            "direction": "neutral",
            "detail": "Based on typical hearing count for this category"
        })

        return factors

    def _get_comparable_cases(self, ct, cl, st, limit=5) -> List[Dict]:
        """Get comparable cases from dataset"""
        cases = self.data_loader.get_all_cases()
        comparable = []
        for case in cases:
            if case.get("case_type", "").lower() == ct:
                score = 30
                if case.get("court_level", "").lower() == cl:
                    score += 35
                if case.get("state", "").lower() == st:
                    score += 35
                comparable.append({
                    "case_type": case["case_type"],
                    "court_level": case["court_level"],
                    "state": case["state"],
                    "delay_months": case["delay_months"],
                    "hearings": case["number_of_hearings"],
                    "disposal_rate": case["historical_disposal_rate"],
                    "match_score": score,
                })
        comparable.sort(key=lambda x: x["match_score"], reverse=True)
        return comparable[:limit]

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics from dataset"""
        stats = self.data_loader.get_case_statistics()

        # Build breakdowns
        cases = self.data_loader.get_all_cases()
        type_breakdown = {}
        state_breakdown = {}
        court_breakdown = {}

        for case in cases:
            ct = case.get("case_type", "Unknown")
            st = case.get("state", "Unknown")
            cl = case.get("court_level", "Unknown")
            delay = case.get("delay_months", 0)

            for breakdown, key in [(type_breakdown, ct), (state_breakdown, st), (court_breakdown, cl)]:
                if key not in breakdown:
                    breakdown[key] = {"count": 0, "total_delay": 0}
                breakdown[key]["count"] += 1
                breakdown[key]["total_delay"] += delay

        def summarize(breakdown):
            return [
                {"name": k, "count": v["count"], "avg_delay": round(v["total_delay"] / v["count"], 1)}
                for k, v in sorted(breakdown.items(), key=lambda x: x[1]["count"], reverse=True)
            ]

        return {
            "total_cases": stats.get("total_cases", 0),
            "average_delay": round(stats.get("average_delay_months", 0), 1),
            "average_hearings": stats.get("average_hearings", 0),
            "avg_disposal_rate": round(stats.get("avg_disposal_rate", 0), 3),
            "by_case_type": summarize(type_breakdown),
            "by_state": summarize(state_breakdown),
            "by_court": summarize(court_breakdown),
        }

    def evaluate_delay_model(self, test_fraction: float = 0.2) -> Dict[str, Any]:
        """Evaluate delay estimates on a deterministic holdout from the delay dataset."""
        frame = self.data_loader.judicial_data
        if frame is None or frame.empty:
            return {
                "evaluation_status": "unavailable",
                "evaluation_note": "The judicial delay dataset is not loaded.",
                "sample_size": 0,
            }

        if not 0 < test_fraction < 1:
            raise ValueError("test_fraction must be between 0 and 1.")

        rows = frame.reset_index(drop=True).copy()
        split_index = max(1, min(len(rows) - 1, round(len(rows) * (1 - test_fraction))))
        train = rows.iloc[:split_index]
        test = rows.iloc[split_index:]
        global_mean = float(train["delay_months"].mean())
        group_columns = ["case_type", "court_level", "state"]
        grouped = train.groupby(group_columns)["delay_months"].mean().to_dict()

        actual = []
        predicted = []
        for _, row in test.iterrows():
            key = (row["case_type"], row["court_level"], row["state"])
            estimate = grouped.get(key)
            if estimate is None:
                estimate = global_mean
            actual.append(float(row["delay_months"]))
            predicted.append(float(estimate))

        errors = [estimate - observed for estimate, observed in zip(predicted, actual)]
        absolute_errors = [abs(error) for error in errors]
        squared_errors = [error * error for error in errors]
        actual_mean = sum(actual) / len(actual)
        total_variance = sum((value - actual_mean) ** 2 for value in actual)
        residual_sum = sum(squared_errors)
        mae = sum(absolute_errors) / len(actual)
        rmse = math.sqrt(residual_sum / len(actual))
        r2 = 1 - (residual_sum / total_variance) if total_variance else 0.0
        within_6_months = sum(error <= 6 for error in absolute_errors) / len(actual)

        return {
            "evaluation_status": "evaluated",
            "target": "delay_months",
            "dataset": "judicial_delay_dataset.csv",
            "sample_size": len(actual),
            "train_size": len(train),
            "test_size": len(test),
            "test_fraction": round(len(test) / len(rows), 4),
            "split_method": "deterministic chronological holdout",
            "metrics": {
                "mae_months": round(mae, 4),
                "rmse_months": round(rmse, 4),
                "r2": round(r2, 4),
                "within_6_months": round(within_6_months, 4),
            },
            "error_distribution": {
                "mean_error_months": round(sum(errors) / len(errors), 4),
                "median_absolute_error_months": round(sorted(absolute_errors)[len(absolute_errors) // 2], 4),
                "max_absolute_error_months": round(max(absolute_errors), 4),
            },
            "limitations": [
                "This evaluates delay duration only; it is not an outcome win-rate accuracy.",
                "The holdout is chronological because the source data has no event timestamp suitable for random stratification.",
            ],
        }


# Singleton
prediction_service = CasePredictionService()
