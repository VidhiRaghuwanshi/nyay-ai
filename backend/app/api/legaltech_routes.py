"""Feature-flagged LegalTech APIs for the additive Modules 1 and 5 foundation."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db import get_db_session
from app.models.schemas import (
    InvoiceCreateRequest,
    InvoicePreviewResponse,
    InvoiceResponse,
    PrecedentIngestRequest,
    PrecedentSearchRequest,
    PrecedentSearchResponse,
    TimeEntryCreate,
    TimeEntryResponse,
)
from app.services.billing_service import BillingService
from app.services.mongo_billing_service import MongoBillingService
from app.services.mongo_rag_service import MongoRagService
from app.services.request_security import authenticated_identity

router = APIRouter()


def require_billing_enabled():
    if not settings.ENABLE_LEGALTECH_PERSISTENCE or not settings.ENABLE_TIME_TRACKING:
        raise HTTPException(
            status_code=503,
            detail="LegalTech time tracking is disabled. Configure PostgreSQL persistence and ENABLE_TIME_TRACKING=True.",
        )


def require_rag_enabled():
    if not settings.ENABLE_LEGALTECH_PERSISTENCE or not settings.ENABLE_PRECEDENT_RAG:
        raise HTTPException(
            status_code=503,
            detail="Precedent RAG is disabled. Configure MongoDB persistence and ENABLE_PRECEDENT_RAG=True.",
        )


def get_billing_service(session: Session | None):
    if settings.DATABASE_BACKEND.lower() == "mongo":
        return MongoBillingService()
    if session is None:
        raise HTTPException(status_code=503, detail="Database session is unavailable.")
    return BillingService


def tenant_context(
    identity: tuple[str, str] = Depends(authenticated_identity),
) -> tuple[UUID, UUID]:
    try:
        return UUID(identity[0]), UUID(identity[1])
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="X-Organization-ID and X-User-ID must be valid UUIDs.",
        ) from error


def serialize_time_entry(entry) -> TimeEntryResponse:
    if isinstance(entry, dict):
        return TimeEntryResponse(
            id=entry["_id"],
            matter_id=entry["matter_id"],
            user_id=entry["user_id"],
            work_date=entry["work_date"].date(),
            duration_minutes=entry["duration_minutes"],
            rate=float(entry["rate"]),
            description=entry["description"],
            billed_status=entry["billed_status"],
        )
    return TimeEntryResponse(
        id=str(entry.id),
        matter_id=str(entry.matter_id),
        user_id=str(entry.user_id),
        work_date=entry.work_date,
        duration_minutes=entry.duration_minutes,
        rate=float(entry.rate),
        description=entry.description,
        billed_status=entry.billed_status,
    )


def serialize_invoice(invoice) -> InvoiceResponse:
    return InvoiceResponse(
        invoice_id=invoice["_id"],
        matter_id=invoice["matter_id"],
        currency=invoice["currency"],
        line_items=invoice["line_items"],
        subtotal=invoice["subtotal"],
        tax=invoice["tax"],
        total=invoice["total"],
        status=invoice["status"],
    )


@router.get("/status")
async def legaltech_status():
    return {
        "persistence_enabled": settings.ENABLE_LEGALTECH_PERSISTENCE,
        "precedent_rag_enabled": settings.ENABLE_PRECEDENT_RAG,
        "time_tracking_enabled": settings.ENABLE_TIME_TRACKING,
        "invoicing_enabled": settings.ENABLE_INVOICING,
        "rag_backend": settings.DATABASE_BACKEND if settings.ENABLE_PRECEDENT_RAG else "disabled",
    }


@router.post("/precedents/ingest")
async def ingest_precedent(
    request: PrecedentIngestRequest,
    _: None = Depends(require_rag_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
):
    if not settings.ENABLE_PRECEDENT_RAG or settings.DATABASE_BACKEND.lower() != "mongo":
        raise HTTPException(status_code=503, detail="Precedent RAG is disabled.")
    organization_id, _ = tenant
    return MongoRagService().ingest(organization_id=organization_id, payload=request)


@router.post("/precedents/search", response_model=PrecedentSearchResponse)
async def search_precedents(
    request: PrecedentSearchRequest,
    _: None = Depends(require_rag_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
):
    if not settings.ENABLE_PRECEDENT_RAG or settings.DATABASE_BACKEND.lower() != "mongo":
        raise HTTPException(status_code=503, detail="Precedent RAG is disabled.")
    organization_id, _ = tenant
    results = MongoRagService().search(organization_id=organization_id, payload=request)
    return {
        "query": request.query,
        "retrieval_mode": "hybrid_vector_keyword",
        "results": results,
    }


@router.post("/precedents/{document_id}/reindex")
async def reindex_precedent(
    document_id: str,
    _: None = Depends(require_rag_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
):
    if settings.DATABASE_BACKEND.lower() != "mongo":
        raise HTTPException(status_code=503, detail="Precedent re-indexing is available in MongoDB mode.")
    organization_id, _ = tenant
    try:
        return MongoRagService().reindex_document(
            organization_id=organization_id,
            document_id=document_id,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/matters/{matter_id}/time-entries", response_model=TimeEntryResponse)
async def create_time_entry(
    matter_id: UUID,
    request: TimeEntryCreate,
    _: None = Depends(require_billing_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
    session: Session = Depends(get_db_session),
):
    organization_id, user_id = tenant
    service = get_billing_service(session)
    arguments = dict(
        organization_id=organization_id,
        user_id=user_id,
        matter_id=matter_id,
        work_date=request.work_date,
        duration_minutes=request.duration_minutes,
        rate=request.rate,
        description=request.description,
    )
    entry = service.create_time_entry(session, **arguments) if session is not None else service.create_time_entry(**arguments)
    return serialize_time_entry(entry)


@router.get("/matters/{matter_id}/time-entries", response_model=list[TimeEntryResponse])
async def list_time_entries(
    matter_id: UUID,
    _: None = Depends(require_billing_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
    session: Session = Depends(get_db_session),
):
    organization_id, _ = tenant
    service = get_billing_service(session)
    entries = (
        service.list_time_entries(session, organization_id=organization_id, matter_id=matter_id)
        if session is not None
        else service.list_time_entries(organization_id=organization_id, matter_id=matter_id)
    )
    return [serialize_time_entry(entry) for entry in entries]


@router.get("/matters/{matter_id}/invoice-preview", response_model=InvoicePreviewResponse)
async def invoice_preview(
    matter_id: UUID,
    tax_rate: float = 0,
    _: None = Depends(require_billing_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
    session: Session = Depends(get_db_session),
):
    organization_id, _ = tenant
    service = get_billing_service(session)
    arguments = dict(
        organization_id=organization_id,
        matter_id=matter_id,
        tax_rate=Decimal(str(tax_rate)),
    )
    return service.preview_unbilled(session, **arguments) if session is not None else service.preview_unbilled(**arguments)


@router.post("/matters/{matter_id}/invoices", response_model=InvoiceResponse)
async def create_invoice(
    matter_id: UUID,
    request: InvoiceCreateRequest,
    _: None = Depends(require_billing_enabled),
    tenant: tuple[UUID, UUID] = Depends(tenant_context),
    session: Session = Depends(get_db_session),
):
    organization_id, user_id = tenant
    if settings.DATABASE_BACKEND.lower() != "mongo":
        raise HTTPException(
            status_code=501,
            detail="Invoice creation is currently implemented for MongoDB development mode.",
        )
    try:
        invoice = MongoBillingService().create_invoice(
            organization_id=organization_id,
            user_id=user_id,
            matter_id=matter_id,
            tax_rate=Decimal(str(request.tax_rate)),
            currency=request.currency,
        )
        return serialize_invoice(invoice)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
