"""Automatic audit logging for critical API actions."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings
from app.services.auth_service import AuthError, verify_identity_token
from app.services.mongo_advanced_service import MongoAdvancedService

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Record successful document, AI, billing, and legal-tech mutations."""

    _ignored_paths = {"/health", "/", "/docs", "/openapi.json", "/redoc"}
    _critical_prefixes = (
        "/api/chatbot",
        "/api/contracts",
        "/api/legaltech",
        "/api/detector",
        "/api/precedent",
        "/api/outcome",
        "/api/procedural",
        "/api/prediction",
        "/api/drafting",
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (
            not settings.ENABLE_LEGALTECH_PERSISTENCE
            or not settings.ENABLE_AUTOMATIC_AUDIT
            or path in self._ignored_paths
            or path.endswith("/audit")
            or not path.startswith(self._critical_prefixes)
            or response.status_code >= 400
        ):
            return response

        identity = self._identity(request)
        if not identity:
            return response
        organization_id, user_id = identity
        try:
            MongoAdvancedService().audit(
                organization_id=organization_id,
                user_id=user_id,
                action=f"{request.method} {path}",
                resource_type="api_request",
                resource_id=str(uuid4()),
                metadata={
                    "status_code": response.status_code,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            logger.exception("Automatic audit logging failed for %s", path)
        return response

    @staticmethod
    def _identity(request: Request):
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            try:
                payload = verify_identity_token(authorization.split(" ", 1)[1].strip())
                return payload["organization_id"], payload["user_id"]
            except AuthError:
                return None
        if settings.ENVIRONMENT.lower() == "development":
            organization_id = request.headers.get("x-organization-id")
            user_id = request.headers.get("x-user-id")
            if organization_id and user_id:
                return organization_id, user_id
        return None
