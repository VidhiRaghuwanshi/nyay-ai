"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

# ==================== Precedent Graph Models ====================

class CaseNode(BaseModel):
    id: str
    label: str
    type: str  # "case" or "section"
    citations: int
    court: Optional[str] = None
    year: Optional[int] = None

class CaseEdge(BaseModel):
    source: str
    target: str
    relation: str  # "cites", "applies", "overrules", etc.

class PrecedentGraphRequest(BaseModel):
    case_name: str
    case_type: str
    query: Optional[str] = None

class PrecedentGraphResponse(BaseModel):
    nodes: List[CaseNode]
    edges: List[CaseEdge]
    similar_cases: List[Dict[str, Any]]
    precedent_strength_scores: Dict[str, float]

# ==================== Risk Detector Models ====================

class Issue(BaseModel):
    id: int
    type: str  # "contradiction", "missing", "weak", "procedural"
    severity: str  # "high", "medium", "low"
    title: str
    description: str
    location: str
    suggestion: str

class CounterArgument(BaseModel):
    id: int
    argument: str
    likelihood: float  # 0-100

class RiskDetectorRequest(BaseModel):
    case_text: str
    case_type: str
    case_id: Optional[str] = None

class RiskDetectorResponse(BaseModel):
    overall_risk_score: float  # 0-100
    risk_level: str  # "high", "medium", "low"
    issues: List[Issue]
    counter_arguments: List[CounterArgument]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)

# ==================== Procedural Flow Models ====================

class TimelineStage(BaseModel):
    stage: str
    duration: int  # months
    delay_probability: float  # 0-100

class ProcedureRequest(BaseModel):
    case_type: str  # "criminal" or "civil"
    court: str  # "district", "high", "supreme"
    state: str

class ProcedureResponse(BaseModel):
    expected_duration: int  # months
    worst_case_duration: int  # months
    delay_probability: float  # 0-100
    stages: List[TimelineStage]
    delay_factors: Dict[str, float]
    stage_wise_risk: Dict[str, float]

# ==================== Chatbot Models ====================

class ChatMessage(BaseModel):
    id: Optional[str] = None
    type: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    verified: bool = False
    references: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    message_id: str
    content: str
    verified: bool
    references: List[str]
    confidence: float  # 0-1
    suggested_questions: Optional[List[str]] = None

# ==================== Outcome Calibration Models ====================

class OutcomeRequest(BaseModel):
    case_data: Dict[str, Any]
    precedent_strength: Optional[float] = None
    evidence_quality: Optional[float] = None

class PredictionFactor(BaseModel):
    factor: str
    influence: float  # 0-100
    direction: str  # "positive", "negative", "neutral"

class OutcomeResponse(BaseModel):
    win_probability: float  # 0-100
    confidence_level: str  # "high", "medium", "low"
    model_accuracy: Optional[float] = None
    calibration_error: Optional[float] = None
    factors: List[PredictionFactor]
    outcome_distribution: Dict[str, float]
    data_points_used: int

# ==================== Auto Drafting Models ====================

class Citation(BaseModel):
    case_name: str
    year: int
    citation: str
    relevance: str  # "high", "medium", "low"
    paragraphs: List[int]

class DraftingRequest(BaseModel):
    case_facts: str
    document_type: str  # "petition", "bail", "fir", "argument", "memorandum"
    case_id: Optional[str] = None

class DraftingResponse(BaseModel):
    document_id: str
    content: str
    citations: List[Citation]
    quality_metrics: Dict[str, float]
    generated_at: datetime = Field(default_factory=datetime.now)

# ==================== Error Models ====================

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== LegalTech Billing Models ====================

class TimeEntryCreate(BaseModel):
    work_date: date
    duration_minutes: int = Field(ge=0)
    rate: float = Field(ge=0)
    description: str = Field(min_length=1, max_length=5000)


class TimeEntryResponse(BaseModel):
    id: str
    matter_id: str
    user_id: str
    work_date: date
    duration_minutes: int
    rate: float
    description: str
    billed_status: str


class InvoicePreviewResponse(BaseModel):
    matter_id: str
    currency: str
    line_items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float


class InvoiceCreateRequest(BaseModel):
    tax_rate: float = Field(default=0, ge=0, le=100)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class InvoiceResponse(InvoicePreviewResponse):
    invoice_id: str
    status: str


class PrecedentIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=50)
    citation: Optional[str] = None
    court: Optional[str] = None
    case_type: Optional[str] = None
    decision_year: Optional[int] = Field(default=None, ge=1800, le=2200)
    source_uri: Optional[str] = None


class PrecedentSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    case_type: Optional[str] = None


class PrecedentSearchResponse(BaseModel):
    query: str
    retrieval_mode: str
    results: List[Dict[str, Any]]


class ContractRiskFlag(BaseModel):
    clause: str
    risk_level: str
    reason: str
    suggested_revision: str


class ContractAnalysisResponse(BaseModel):
    analysis_id: str
    filename: str
    source_type: str
    extracted_characters: int
    flags: List[ContractRiskFlag]
    analysis_source: str


class CourtListingCreate(BaseModel):
    matter_id: str = Field(min_length=1)
    court: str = Field(min_length=1)
    case_number: str = Field(min_length=1)
    hearing_date: datetime
    item_number: Optional[str] = None
    judge: Optional[str] = None
    status: str = "scheduled"


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document_type: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    placeholders: List[str] = Field(default_factory=list)


class TemplateRenderRequest(BaseModel):
    template_id: str
    values: Dict[str, Any] = Field(default_factory=dict)
    output_format: str = Field(default="docx", pattern="^(docx|pdf)$")


class PortalDocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)
    mime_type: str = "application/pdf"


class SignDocumentRequest(BaseModel):
    signer_name: str = Field(min_length=1, max_length=200)
    signer_email: Optional[str] = None
    signature_text: str = Field(min_length=1, max_length=500)


class ChronologyCreate(BaseModel):
    matter_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class DictationResponse(BaseModel):
    dictation_id: str
    transcript: str
    summary: str
    client_instructions: List[str]
    court_directives: List[str]
    action_items: List[str]
    transcription_source: str


class CaseOutcomeCreate(BaseModel):
    matter_id: str = Field(min_length=1)
    judge: Optional[str] = None
    opposing_counsel: Optional[str] = None
    outcome: str = Field(min_length=1)
    resolution_days: Optional[int] = Field(default=None, ge=0)
    settlement: bool = False
