"""Signed tenant identity helpers used by Nyay AI's local and production routes."""

import base64
import hashlib
import hmac
import json
import time
from typing import Dict

from app.config.settings import settings


class AuthError(ValueError):
    """Raised when a tenant identity token is invalid."""


def _segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_identity_token(organization_id: str, user_id: str) -> str:
    if not organization_id or not user_id:
        raise AuthError("Organization and user identity are required.")
    payload = {
        "organization_id": organization_id,
        "user_id": user_id,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    encoded = _segment(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"nyay.{encoded}.{_segment(signature)}"


def verify_identity_token(token: str) -> Dict[str, str]:
    try:
        prefix, encoded, supplied_signature = token.split(".", 2)
        if prefix != "nyay":
            raise AuthError("Invalid identity token.")
        expected_signature = _segment(
            hmac.new(
                settings.SECRET_KEY.encode("utf-8"),
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise AuthError("Invalid identity token signature.")
        payload = json.loads(_decode_segment(encoded))
        if int(payload["expires_at"]) < int(time.time()):
            raise AuthError("Identity token has expired.")
        if not payload.get("organization_id") or not payload.get("user_id"):
            raise AuthError("Identity token is missing tenant identity.")
        return {
            "organization_id": str(payload["organization_id"]),
            "user_id": str(payload["user_id"]),
        }
    except (AuthError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        if isinstance(error, AuthError):
            raise
        raise AuthError("Invalid identity token.") from error
