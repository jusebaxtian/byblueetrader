from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.license_service import validate_license
from app.core.supabase_client import get_supabase_client
from app.repositories.license_repository import SupabaseLicenseRepository

router = APIRouter(prefix="/api/license", tags=["license"])


class ValidateRequest(BaseModel):
    iq_email: str
    device_id: str | None = None


class ValidateResponse(BaseModel):
    valid: bool
    status: str
    expires_at: str | None


def _check_api_key(x_api_key: str | None) -> None:
    if x_api_key != settings.bot_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/validate", response_model=ValidateResponse)
def validate(payload: ValidateRequest, x_api_key: str | None = Header(default=None)) -> ValidateResponse:
    _check_api_key(x_api_key)
    repo = SupabaseLicenseRepository(get_supabase_client())
    result = validate_license(repo, payload.iq_email)
    return ValidateResponse(
        valid=result.valid,
        status=result.status,
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
    )
