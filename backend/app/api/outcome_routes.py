"""API Routes - Outcome Calibration"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import OutcomeRequest
from app.services.outcome_service import OutcomeCalibrationService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
outcome_service = OutcomeCalibrationService()

@router.post("/predict")
async def predict_outcome(request: OutcomeRequest):
    """Predict case outcome"""
    try:
        result = await outcome_service.predict_outcome(request.case_data)
        return result
    except Exception as e:
        logger.error(f"Error in predict_outcome: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calibration")
async def get_calibration_metrics():
    """Get calibration metrics"""
    try:
        return {
            "model_accuracy": None,
            "calibration_quality": None,
            "calibration_error": None,
            "data_points": 0,
            "evaluation_status": "not_evaluated",
            "evaluation_note": "Provide labeled historical outcomes before reporting accuracy or calibration metrics.",
            "last_updated": None,
        }
    except Exception as e:
        logger.error(f"Error getting calibration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
