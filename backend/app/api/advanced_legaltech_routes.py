"""MongoDB-backed APIs for Nyay AI Modules 3, 4, 6, 7, 8, 9 and 10."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.models.schemas import (
    CaseOutcomeCreate, ChronologyCreate, CourtListingCreate, DictationResponse,
    PortalDocumentCreate, SignDocumentRequest, TemplateCreate, TemplateRenderRequest,
)
from app.services.mongo_advanced_service import MongoAdvancedService
from app.services.request_security import authenticated_identity, validate_upload
from app.services.evidence_service import EvidenceExtractionError, extract_evidence_text
from app.services.transcription_service import TranscriptionError, transcribe_audio

router = APIRouter()


tenant = authenticated_identity


def service():
    return MongoAdvancedService()


@router.post("/court-listings")
async def create_listing(payload: CourtListingCreate, ids=Depends(tenant)):
    return service().add_listing(*ids, payload)


@router.get("/court-listings")
async def list_listings(matter_id: str | None = None, ids=Depends(tenant)):
    return service().list_listings(ids[0], matter_id)


@router.patch("/court-listings/{listing_id}")
async def update_listing(listing_id: str, updates: dict, ids=Depends(tenant)):
    result = service().update_listing(ids[0], listing_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Court listing was not found.")
    return result


@router.post("/court-docket/sync-ndap")
async def sync_ndap_backlog(
    state: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    ids=Depends(tenant),
):
    try:
        return service().sync_ndap_backlog(ids[0], ids[1], state, case_type)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/court-docket/notifications")
async def court_notifications(
    unread_only: bool = Query(default=False),
    ids=Depends(tenant),
):
    return {
        "notifications": service().list_court_notifications(ids[0], unread_only),
    }


@router.post("/court-docket/notifications/{notification_id}/read")
async def mark_court_notification_read(notification_id: str, ids=Depends(tenant)):
    try:
        return service().mark_court_notification_read(ids[0], notification_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/templates")
async def create_template(payload: TemplateCreate, ids=Depends(tenant)):
    return service().create_template(*ids, payload)


@router.post("/templates/render")
async def render_template(payload: TemplateRenderRequest, ids=Depends(tenant)):
    try:
        content, media_type, filename = service().render_template(ids[0], payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/portal/documents")
async def create_portal_document(payload: PortalDocumentCreate, ids=Depends(tenant)):
    try:
        return service().create_portal_document(*ids, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid base64 document content.") from error


@router.get("/portal/documents")
async def list_portal_documents(ids=Depends(tenant)):
    return {"documents": service().list_portal_documents(ids[0])}


@router.get("/portal/documents/{document_id}/download")
async def download_portal_document(document_id: str, ids=Depends(tenant)):
    try:
        content, media_type, filename = service().download_portal_document(ids[0], document_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    safe_filename = filename.replace("\\", "_").replace("/", "_").replace('"', "_").replace("\r", "_").replace("\n", "_")
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post("/portal/documents/{document_id}/sign")
async def sign_document(document_id: str, payload: SignDocumentRequest, ids=Depends(tenant)):
    try:
        return service().sign_document(ids[0], ids[1], document_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/chronology")
async def chronology(payload: ChronologyCreate, ids=Depends(tenant)):
    return {"events": service().extract_chronology(*ids, payload)}


@router.post("/chronology/upload")
async def chronology_upload(
    matter_id: str = Query(..., min_length=1),
    file: UploadFile = File(...),
    ids=Depends(tenant),
):
    content = await file.read()
    safe_name = validate_upload(
        file,
        content,
        allowed_extensions={".pdf", ".docx", ".txt", ".md"},
        max_bytes=10 * 1024 * 1024,
    )
    try:
        text, source = extract_evidence_text(safe_name, content)
    except EvidenceExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not text:
        raise HTTPException(status_code=422, detail="No text could be extracted from the evidence file.")
    payload = ChronologyCreate(matter_id=matter_id, text=text)
    events = service().extract_chronology(*ids, payload)
    return {
        "filename": safe_name,
        "source": source,
        "characters": len(text),
        "events": events,
    }


@router.post("/dictation", response_model=DictationResponse)
async def dictation(
    file: UploadFile = File(...),
    transcript: str | None = Query(default=None),
    ids=Depends(tenant),
):
    content = await file.read()
    safe_name = validate_upload(
        file,
        content,
        allowed_extensions={".txt", ".md", ".mp3", ".wav", ".m4a", ".mp4", ".webm"},
        max_bytes=25 * 1024 * 1024,
    )
    text = transcript
    source = "provided_transcript"
    if not text and safe_name.lower().endswith((".txt", ".md")):
        text = content.decode("utf-8", errors="replace")
        source = "local_text_audio_adapter"
    if not text:
        try:
            text, source = transcribe_audio(safe_name, content)
        except TranscriptionError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    return service().save_dictation(*ids, text, source)


@router.post("/analytics/outcomes")
async def add_outcome(payload: CaseOutcomeCreate, ids=Depends(tenant)):
    return service().add_outcome(*ids, payload)


@router.get("/analytics")
async def analytics(group_by: str = Query(default="judge", pattern="^(judge|opposing_counsel)$"), ids=Depends(tenant)):
    return {"group_by": group_by, "groups": service().analytics(ids[0], group_by)}


@router.post("/audit")
async def audit(
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict | None = None,
    ids=Depends(tenant),
):
    return service().audit(ids[0], ids[1], action, resource_type, resource_id, metadata)
