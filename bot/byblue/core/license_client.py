"""Calls the ByblueTrader backend to validate a user's license at startup."""
import requests

DEFAULT_TIMEOUT_SECONDS = 10


class LicenseError(Exception):
    pass


class LicenseClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def validate(self, iq_email: str, device_id: str | None = None) -> dict:
        try:
            response = requests.post(
                f"{self._base_url}/api/license/validate",
                json={"iq_email": iq_email, "device_id": device_id},
                headers={"X-Api-Key": self._api_key},
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise LicenseError(f"No se pudo contactar al servidor de licencias: {exc}") from exc

        if response.status_code != 200:
            raise LicenseError(f"Servidor de licencias respondió {response.status_code}")

        data = response.json()
        if not data.get("valid"):
            raise LicenseError(f"Licencia no válida (estado: {data.get('status')})")
        return data
