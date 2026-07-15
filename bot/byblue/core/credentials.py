"""Stores the IQ Option password in the OS credential vault (Windows Credential
Manager via `keyring`) — never written to disk in plaintext or sent to the backend."""
import os
from pathlib import Path

import keyring

SERVICE_NAME = "ByblueTrader-IQOption"
_LAST_EMAIL_KEY = "__last_email__"


def save_password(email: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, email, password)


def load_password(email: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, email)


def delete_password(email: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, email)
    except keyring.errors.PasswordDeleteError:
        pass


def _last_email_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    directory = Path(appdata) / "ByblueTrader"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "last_email.txt"


def save_last_email(email: str) -> None:
    _last_email_path().write_text(email, encoding="utf-8")


def load_last_email() -> str | None:
    path = _last_email_path()
    if not path.exists():
        return None
    email = path.read_text(encoding="utf-8").strip()
    return email or None
