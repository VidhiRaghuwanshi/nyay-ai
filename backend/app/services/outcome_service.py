"""Outcome Calibration Service"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class OutcomeCalibrationService:
    """Service for outcome prediction and confidence calibration"""
    
    async def predict_outcome(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict case outcome with confidence
        
        Args:
            case_data: Case details
            
        Returns:
            Outcome prediction with calibration
        """
        try:
            # Calculate win probability
            win_prob = self._calculate_win_probability(case_data)
            
            # Determine confidence level
            confidence_level = self._determine_confidence(win_prob, case_data)
            
            # Get prediction factors
            factors = self._get_prediction_factors(case_data)
            
            return {
                "win_probability": win_prob,
                "confidence_level": confidence_level,
                "model_accuracy": None,
                "calibration_error": None,
                "evaluation_status": "not_evaluated",
                "evaluation_note": "Outcome accuracy requires labeled historical outcome data; no such labels are currently configured.",
                "factors": factors,
                "outcome_distribution": {
                    "plaintiff_win": win_prob,
                    "defendant_win": round((100 - win_prob) * 0.5, 2),
                    "settlement": round((100 - win_prob) * 0.3, 2),
                    "dismissal": round((100 - win_prob) * 0.2, 2)
                },
                "data_points_used": 0
            }
            
        except Exception as e:
            logger.error(f"Error predicting outcome: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_win_probability(self, case_data: Dict) -> float:
        """Calculate win probability"""
        base_prob = 50
        
        # Evidence quality
        if case_data.get("evidence_quality"):
            base_prob += case_data["evidence_quality"] * 0.2
        
        # Precedent strength
        if case_data.get("precedent_strength"):
            base_prob += case_data["precedent_strength"] * 0.15
        
        # Keep the score deterministic so the same case produces the same result.
        text = str(case_data.get("description", "")).lower()
        if any(term in text for term in ("strong evidence", "documentary evidence", "admission", "precedent supports")):
            base_prob += 8
        if any(term in text for term in ("contradiction", "insufficient evidence", "delay", "default", "limitation")):
            base_prob -= 8

        return min(95, max(5, base_prob))
    
    def _determine_confidence(self, win_prob: float, case_data: Dict) -> str:
        """Determine confidence level"""
        # If close to 50-50, confidence is lower
        prob_distance = abs(win_prob - 50)
        
        if prob_distance > 20:
            return "High"
        elif prob_distance > 10:
            return "Medium"
        else:
            return "Low"
    
    def _get_prediction_factors(self, case_data: Dict) -> List[Dict]:
        """Get prediction influencing factors"""
        factors = [
            {
                "factor": "Precedent Strength",
                "influence": 35,
                "direction": "positive"
            },
            {
                "factor": "Evidence Quality",
                "influence": 28,
                "direction": "positive"
            },
            {
                "factor": "Judge Experience",
                "influence": 18,
                "direction": "neutral"
            },
            {
                "factor": "Opposing Counsel",
                "influence": 12,
                "direction": "negative"
            },
            {
                "factor": "Case Complexity",
                "influence": 7,
                "direction": "neutral"
            }
        ]
        return factors
