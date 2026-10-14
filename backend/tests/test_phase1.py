import math

import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app.main import app
from app.services.embedding_service import EmbeddingService, generate_case_embedding_text
from app.services.text_generation_service import TextGenerationError, TextGenerationService
from app.services.data_loader import data_loader
from app.services.outcome_service import OutcomeCalibrationService
from app.services.prediction_service import prediction_service
from app.services.auth_service import AuthError, create_identity_token, verify_identity_token
from app.services.mongo_advanced_service import MongoAdvancedService
from app.services.evidence_service import extract_evidence_text
from app.services.request_security import (
    authenticated_identity,
    validate_startup_security,
    validate_upload,
)


def test_fastapi_app_imports():
    assert any(route.path == "/health" for route in app.routes)


def test_groq_missing_key_is_explicit():
    client = TextGenerationService(api_key="")
    try:
        client.generate("test")
    except TextGenerationError as error:
        assert "GROQ_API_KEY" in str(error)
    else:
        raise AssertionError("Expected a missing-key error")


def test_case_embedding_text_is_deterministic():
    case = {
        "case_name": "A v B",
        "court": "High Court",
        "sections": ["IPC 420"],
        "key_issues": ["fraud"],
    }
    assert generate_case_embedding_text(case) == generate_case_embedding_text(case)
    assert "CASE TITLE:" in generate_case_embedding_text(case)


def test_local_embedding_empty_text():
    service = EmbeddingService()
    assert service.generate_embedding("") == []


def test_local_embedding_dimension_and_stability():
    service = EmbeddingService()
    first = service.generate_embedding("contract breach and damages")
    second = service.generate_embedding("contract breach and damages")
    assert len(first) > 0
    assert len(first) == len(second)
    assert all(math.isfinite(value) for value in first)
    assert first == second


def test_cosine_similarity_is_dimension_safe():
    from app.services.mongo_rag_service import MongoRagService

    assert MongoRagService._cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert MongoRagService._cosine([1.0], [1.0, 0.0]) == 1.0


def test_added_datasets_are_loaded():
    catalog = data_loader.get_dataset_catalog()
    assert "judgments.csv" in catalog
    assert "NDAP_REPORT_7149.csv" in catalog
    assert catalog["judgments.csv"]["rows"] > 0
    assert catalog["NDAP_REPORT_7149.csv"]["rows"] > 0


def test_judgment_search_returns_metadata():
    results = data_loader.search_judgments("UNION OF INDIA", limit=5)
    assert results
    assert "case_no" in results[0]
    assert "judgment_date" in results[0]


def test_outcome_metrics_are_not_claimed_without_labels():
    result = __import__("asyncio").run(
        OutcomeCalibrationService().predict_outcome({"description": "documentary evidence"})
    )
    assert result["evaluation_status"] == "not_evaluated"
    assert result["model_accuracy"] is None
    assert result["data_points_used"] == 0


def test_delay_evaluation_returns_reproducible_metrics():
    result = prediction_service.evaluate_delay_model()
    assert result["evaluation_status"] == "evaluated"
    assert result["sample_size"] == result["test_size"]
    assert result["metrics"]["mae_months"] >= 0
    assert result["metrics"]["rmse_months"] >= 0
    assert 0 <= result["metrics"]["within_6_months"] <= 1


def test_identity_token_round_trip_and_tamper_detection():
    token = create_identity_token("org-test", "user-test")
    assert verify_identity_token(token) == {
        "organization_id": "org-test",
        "user_id": "user-test",
    }
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    try:
        verify_identity_token(".".join(parts))
    except AuthError:
        pass
    else:
        raise AssertionError("Tampered identity token was accepted")


def test_ndap_sync_method_is_available():
    assert hasattr(MongoAdvancedService, "sync_ndap_backlog")
    assert hasattr(MongoAdvancedService, "list_court_notifications")
    assert hasattr(MongoAdvancedService, "mark_court_notification_read")


def test_portal_document_listing_and_download_methods_are_available():
    assert hasattr(MongoAdvancedService, "list_portal_documents")
    assert hasattr(MongoAdvancedService, "download_portal_document")
    assert any(route.path == "/api/legaltech/portal/documents" for route in app.routes)
    assert any(route.path == "/api/legaltech/portal/documents/{document_id}/download" for route in app.routes)


def test_evidence_text_extraction_supports_plain_text():
    text, source = extract_evidence_text("evidence.txt", b"10 January 2024: Hearing before the Court.")
    assert source == "plain_text"
    assert "Hearing" in text


def test_production_security_guard_rejects_unsafe_configuration(monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_AUTH", False)
    with pytest.raises(RuntimeError, match="REQUIRE_AUTH"):
        validate_startup_security()


def test_identity_requires_bearer_token_outside_development(monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEV_ALLOW_INSECURE_TENANT_HEADERS", False)
    with pytest.raises(HTTPException) as error:
        authenticated_identity(None, "org-client", "user-client")
    assert error.value.status_code == 401


def test_upload_validation_rejects_unsafe_type_and_empty_content():
    empty = UploadFile(filename="evidence.pdf", file=BytesIO(b""))
    with pytest.raises(HTTPException) as error:
        validate_upload(empty, b"", allowed_extensions={".pdf"}, max_bytes=1024)
    assert error.value.status_code == 400

    invalid = UploadFile(filename="evidence.exe", file=BytesIO(b"content"))
    with pytest.raises(HTTPException) as error:
        validate_upload(invalid, b"content", allowed_extensions={".pdf"}, max_bytes=1024)
    assert error.value.status_code == 415


def test_chatbot_conversation_ownership_is_enforced():
    from app.api import chatbot_routes

    chatbot_routes.document_store.clear()
    chatbot_routes.document_store["conversation-test"] = {
        "owner": ("org-a", "user-a"),
        "documents": [],
    }
    with pytest.raises(HTTPException) as error:
        chatbot_routes._owned_conversation("conversation-test", ("org-b", "user-b"))
    assert error.value.status_code == 404
    chatbot_routes.document_store.clear()
