from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.admin_auth import require_admin
from app.core.supabase_client import get_supabase_client
from app.repositories.license_repository import SupabaseLicenseRepository

router = APIRouter(prefix="/admin", tags=["admin-users"], dependencies=[Depends(require_admin)])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _repo() -> SupabaseLicenseRepository:
    return SupabaseLicenseRepository(get_supabase_client())


@router.get("/users")
def list_users(request: Request):
    users = _repo().list_users()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@router.post("/users")
def create_user(
    iq_email: str = Form(...),
    plan: str = Form("monthly"),
    expires_at: str = Form(...),
):
    expires = datetime.fromisoformat(expires_at)
    _repo().create_user_with_license(iq_email, plan, expires)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{license_id}/status")
def set_status(license_id: str, status: str = Form(...)):
    _repo().update_license(license_id, status=status)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{license_id}/expires")
def set_expires(license_id: str, expires_at: str = Form(...)):
    _repo().update_license(license_id, expires_at=datetime.fromisoformat(expires_at))
    return RedirectResponse(url="/admin/users", status_code=303)
