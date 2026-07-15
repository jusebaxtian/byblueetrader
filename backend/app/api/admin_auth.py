from pathlib import Path

import bcrypt
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin-auth"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class AdminAuthRequired(Exception):
    pass


def require_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise AdminAuthRequired()


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    valid = email == settings.admin_email and settings.admin_password_hash and bcrypt.checkpw(
        password.encode(), settings.admin_password_hash.encode()
    )
    if not valid:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Credenciales inválidas"}, status_code=401
        )
    request.session["admin"] = True
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)
