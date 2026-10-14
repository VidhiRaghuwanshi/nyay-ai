"""Shared request identity and upload validation helpers."""

import os
import re
from pathlib import PurePath

from fastapi import Header, HTTPException, UploadFile

from app.config.settings import settings
from app.services.auth_service import AuthError, verify_identity_token


def authenticated_identity(
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> tuple[str, str]:
    """Return a verified identity, allowing headers only in explicit local mode."""
    if authorization and authorization.lower().startswith("bearer "):
        try:
            identity = verify_identity_token(authorization.split(" ", 1)[1].strip())
            return identity["organization_id"], identity["user_id"]
        except AuthError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    if (
        settings.ENVIRONMENT.lower() == "development"
        and settings.DEV_ALLOW_INSECURE_TENANT_HEADERS
        and x_organization_id
        and x_user_id
    ):
        return x_organization_id, x_user_id

    raise HTTPException(status_code=401, detail="A valid bearer token is required.")


def validate_startup_security() -> None:
    """Fail closed for unsafe production configuration."""
    if settings.ENVIRONMENT.lower() == "development":
        return
    if not settings.REQUIRE_AUTH:
        raise RuntimeError("Production requires REQUIRE_AUTH=True.")
    if settings.DEV_ALLOW_INSECURE_TENANT_HEADERS:
        raise RuntimeError("Development tenant headers must be disabled outside development.")
    if len(settings.SECRET_KEY) < 32 or settings.SECRET_KEY == "your-secret-key-change-in-production":
        raise RuntimeError("Production requires a strong non-placeholder SECRET_KEY.")
    if "*" in settings.ALLOWED_ORIGINS:
        raise RuntimeError("Production CORS origins must be explicit; wildcard origins are not allowed.")
    if not settings.TRUSTED_HOSTS:
        raise RuntimeError("Production requires explicit TRUSTED_HOSTS.")
    if settings.ORGANIZATION_MEMBERSHIP_BACKEND.lower() == "unconfigured":
        raise RuntimeError("Production requires a configured organization membership backend.")


def validate_upload(
    file: UploadFile,
    content: bytes,
    *,
    allowed_extensions: set[str],
    max_bytes: int,
) -> str:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    safe_name = os.path.basename(filename)
    if (
        safe_name != filename
        or "/" in filename
        or "\\" in filename
        or any(ord(char) < 32 for char in filename)
    ):
        raise HTTPException(status_code=400, detail="The filename is not safe.")
    suffix = PurePath(safe_name).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Supported file types: {', '.join(sorted(allowed_extensions))}.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="The uploaded file is too large.")
    if not re.search(r"[A-Za-z0-9]", safe_name):
        raise HTTPException(status_code=400, detail="The filename is invalid.")
    return safe_name
