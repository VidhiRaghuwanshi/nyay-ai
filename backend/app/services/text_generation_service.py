"""Shared Groq text-generation provider."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.config.settings import settings

logger = logging.getLogger(__name__)


class TextGenerationError(RuntimeError):
    """Safe provider error that never contains credentials."""


class TextGenerationService:
    """Generate text through Groq's OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        session: Any = requests,
    ):
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.GROQ_TIMEOUT_SECONDS
        self.session = session
        self._model_verified = False

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _require_key(self) -> None:
        if not self.api_key:
            raise TextGenerationError("Groq text generation is not configured: GROQ_API_KEY is missing.")
        if not self.model:
            raise TextGenerationError("Groq text generation is not configured: GROQ_MODEL is missing.")

    def verify_model(self) -> None:
        """Verify the configured model against Groq's live models endpoint."""
        self._require_key()
        if self._model_verified:
            return
        try:
            response = self.session.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.Timeout as error:
            logger.warning("Groq model verification timed out.")
            raise TextGenerationError("Groq model verification timed out.") from error
        except requests.RequestException as error:
            logger.warning("Groq model verification request failed: %s", type(error).__name__)
            raise TextGenerationError("Groq model verification failed.") from error
        if response.status_code == 401:
            raise TextGenerationError("Groq authentication failed. Check GROQ_API_KEY.")
        if response.status_code == 429:
            raise TextGenerationError("Groq rate limit reached while verifying the configured model.")
        if response.status_code >= 400:
            logger.warning("Groq model verification returned HTTP %s.", response.status_code)
            raise TextGenerationError("Groq model verification failed.")
        try:
            models = response.json().get("data", [])
            model_ids = {item.get("id") for item in models if isinstance(item, dict)}
        except (ValueError, AttributeError, TypeError) as error:
            raise TextGenerationError("Groq returned an invalid models response.") from error
        if self.model not in model_ids:
            raise TextGenerationError(f"Configured Groq model is not available: {self.model}.")
        self._model_verified = True

    def generate(self, prompt: str, *, response_mime_type: str | None = None) -> str:
        """Generate one response and raise explicit errors for provider failures."""
        self._require_key()
        if not prompt or not prompt.strip():
            raise TextGenerationError("Groq text generation requires a non-empty prompt.")
        self.verify_model()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        if response_mime_type == "application/json":
            payload["response_format"] = {"type": "json_object"}
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as error:
            logger.warning("Groq generation timed out.")
            raise TextGenerationError("Groq text generation timed out.") from error
        except requests.RequestException as error:
            logger.warning("Groq generation request failed: %s", type(error).__name__)
            raise TextGenerationError("Groq text generation request failed.") from error
        if response.status_code == 401:
            raise TextGenerationError("Groq authentication failed. Check GROQ_API_KEY.")
        if response.status_code == 429:
            raise TextGenerationError("Groq rate limit reached. Try again later.")
        if response.status_code >= 400:
            logger.warning("Groq generation returned HTTP %s.", response.status_code)
            raise TextGenerationError("Groq text generation failed at the provider.")
        try:
            text = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise TextGenerationError("Groq returned a malformed generation response.") from error
        if not isinstance(text, str) or not text.strip():
            raise TextGenerationError("Groq returned an empty generation response.")
        return text.strip()
