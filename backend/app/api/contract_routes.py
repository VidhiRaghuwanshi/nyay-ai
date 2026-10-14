"""Contract risk analysis and DOCX redlining routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.models.schemas import ContractAnalysisResponse
from app.services.contract_service import ContractService
from app.services.request_security import authenticated_identity, validate_upload

router = APIRouter()
contract_service = ContractService()
MAX_CONTRACT_SIZE = 10 * 1024 * 1024


@router.post("/analyze", response_model=ContractAnalysisResponse)
async def analyze_contract(
    file: UploadFile = File(...),
    identity: tuple[str, str] = Depends(authenticated_identity),
):
    content = await file.read()
    filename = validate_upload(
        file,
        content,
        allowed_extensions={".pdf", ".docx"},
        max_bytes=MAX_CONTRACT_SIZE,
    )
    try:
        return contract_service.analyze(
            filename=filename,
            content=content,
            organization_id=identity[0],
            user_id=identity[1],
        )
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=422, detail="Contract analysis failed.") from error


@router.get("/{analysis_id}/redline")
async def download_redline(
    analysis_id: str,
    identity: tuple[str, str] = Depends(authenticated_identity),
):
    try:
        content, filename = contract_service.redline(
            analysis_id,
            organization_id=identity[0],
            user_id=identity[1],
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
