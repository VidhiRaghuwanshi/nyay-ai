"""API Routes - Case Prediction"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from app.services.prediction_service import prediction_service
from app.services.data_loader import data_loader


class PredictionRequest(BaseModel):
    case_type: str  # Criminal, Civil, Family, Commercial, Property
    court_level: str  # District, High, Supreme
    state: str  # Delhi, Maharashtra, etc.
    number_of_hearings: Optional[int] = None
    judge_workload: Optional[int] = None


@router.post("/predict")
async def predict_case(request: PredictionRequest):
    """Predict case delay and success rate"""
    try:
        result = prediction_service.predict(
            case_type=request.case_type,
            court_level=request.court_level,
            state=request.state,
            hearings=request.number_of_hearings,
            workload=request.judge_workload,
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get dataset statistics for visualizations"""
    try:
        return prediction_service.get_dataset_stats()
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets")
async def get_dataset_catalog():
    """Return loaded dataset metadata without exposing file contents."""
    try:
        return {
            "datasets": data_loader.get_dataset_catalog(),
            "judgment_rows": len(data_loader.judgment_data) if data_loader.judgment_data is not None else 0,
            "court_backlog_rows": (
                len(data_loader.court_backlog_data)
                if data_loader.court_backlog_data is not None else 0
            ),
        }
    except Exception as e:
        logger.error(f"Dataset catalog error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation")
async def evaluate_prediction_model():
    """Return reproducible delay-model evaluation metrics."""
    try:
        return prediction_service.evaluate_delay_model()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/judgments/search")
async def search_judgments(q: str, limit: int = 20):
    """Search the imported Supreme Court judgment metadata."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100.")
    try:
        return {
            "query": q,
            "results": data_loader.search_judgments(q, limit),
        }
    except Exception as e:
        logger.error(f"Judgment search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
