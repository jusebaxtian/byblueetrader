from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin_auth, admin_users, license
from app.api.admin_auth import AdminAuthRequired
from app.core.config import settings

app = FastAPI(title="ByblueTrader License API")
app.add_middleware(SessionMiddleware, secret_key=settings.admin_session_secret)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


@app.exception_handler(AdminAuthRequired)
def _redirect_to_login(request: Request, exc: AdminAuthRequired):
    return RedirectResponse(url="/admin/login", status_code=303)


app.include_router(license.router)
app.include_router(admin_auth.router)
app.include_router(admin_users.router)


@app.get("/")
def root():
    return {"service": "ByblueTrader License API"}
