import json

import requests
import pytest

from app.config.settings import settings
from app.services.contract_service import ContractService
from app.services.text_generation_service import TextGenerationError, TextGenerationService


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, model_response=None, generation_response=None):
        self.model_response = model_response or FakeResponse(
            200, {"data": [{"id": "openai/gpt-oss-120b"}]}
        )
        self.generation_response = generation_response or FakeResponse(
            200,
            {"choices": [{"message": {"content": "Generated answer"}}]},
        )
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.model_response

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self.generation_response


def service(session=None, **kwargs):
    return TextGenerationService(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        base_url="https://groq.test/openai/v1",
        session=session or FakeSession(),
        **kwargs,
    )


def test_model_is_verified_and_text_is_generated():
    fake = FakeSession()
    result = service(fake).generate("Explain bail.")
    assert result == "Generated answer"
    assert fake.get_calls[0][0].endswith("/models")
    assert fake.post_calls[0][0].endswith("/chat/completions")


def test_unavailable_model_is_rejected():
    fake = FakeSession(model_response=FakeResponse(200, {"data": [{"id": "other-model"}]}))
    with pytest.raises(TextGenerationError, match="not available"):
        service(fake).generate("test")


def test_timeout_is_explicit():
    class TimeoutSession(FakeSession):
        def get(self, url, **kwargs):
            raise requests.Timeout()

    with pytest.raises(TextGenerationError, match="timed out"):
        service(TimeoutSession()).generate("test")


def test_rate_limit_is_explicit():
    fake = FakeSession(model_response=FakeResponse(429, {}))
    with pytest.raises(TextGenerationError, match="rate limit"):
        service(fake).generate("test")


def test_provider_error_is_explicit():
    fake = FakeSession(
        generation_response=FakeResponse(500, {"error": {"message": "provider error"}})
    )
    with pytest.raises(TextGenerationError, match="failed at the provider"):
        service(fake).generate("test")


def test_malformed_response_is_explicit():
    fake = FakeSession(generation_response=FakeResponse(200, {"unexpected": True}))
    with pytest.raises(TextGenerationError, match="malformed"):
        service(fake).generate("test")


def test_missing_key_is_explicit():
    with pytest.raises(TextGenerationError, match="GROQ_API_KEY"):
        TextGenerationService(api_key="").generate("test")


def test_contract_json_generation_uses_shared_service(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
    contract = ContractService.__new__(ContractService)

    class FakeGenerator:
        def generate(self, prompt, *, response_mime_type=None):
            assert response_mime_type == "application/json"
            return json.dumps(
                [{
                    "clause": "Liability",
                    "risk_level": "high",
                    "reason": "Exposure is uncapped.",
                    "suggested_revision": "Add a liability cap.",
                }]
            )

    contract.text_generation = FakeGenerator()
    flags = contract._llm_flags("The supplier has unlimited liability.")
    assert len(flags) == 1
    assert flags[0].clause == "Liability"
