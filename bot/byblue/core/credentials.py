"""Stores the IQ Option password in the OS credential vault (Windows Credential
Manager via `keyring`) — never written to disk in plaintext or sent to the backend."""
import keyring

SERVICE_NAME = "ByblueTrader-IQOption"


def save_password(email: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, email, password)


def load_password(email: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, email)


def delete_password(email: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, email)
    except keyring.errors.PasswordDeleteError:
        pass
