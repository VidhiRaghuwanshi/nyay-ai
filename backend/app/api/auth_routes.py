from fastapi import APIRouter, Header, HTTPException

from app.config.settings import settings
from app.services.auth_service import AuthError, create_identity_token, verify_identity_token

router = APIRouter()


@router.post("/identity-token")
async def create_identity_token_route(
    x_organization_id: str = Header(...),
    x_user_id: str = Header(...),
):
    """Issue a signed development identity token from the current tenant headers."""
    if (
        settings.ENVIRONMENT.lower() != "development"
        or not settings.DEV_ALLOW_INSECURE_TENANT_HEADERS
    ):
        raise HTTPException(
            status_code=403,
            detail="Development identity tokens are disabled outside development.",
        )
    try:
        return {
            "access_token": create_identity_token(x_organization_id, x_user_id),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    except AuthError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/verify")
async def verify_identity(authorization: str = Header(...)):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer identity token is required.")
    try:
        return verify_identity_token(authorization.split(" ", 1)[1].strip())
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
