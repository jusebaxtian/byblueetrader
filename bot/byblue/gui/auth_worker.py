"""QThread worker for the login screen: validates license + IQ Option
credentials before the main window is allowed to open."""
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from byblue.core.bot_config import LICENSE_API_KEY, LICENSE_BACKEND_URL
from byblue.core.iq_client import IQClient, IQClientError
from byblue.core.license_client import LicenseClient, LicenseError


class AuthWorker(QObject):
    authenticated = pyqtSignal(str, str)  # email, password
    auth_failed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._license_client = LicenseClient(LICENSE_BACKEND_URL, LICENSE_API_KEY)

    def login(self, email: str, password: str) -> None:
        try:
            self._license_client.validate(email)
        except LicenseError as exc:
            self.auth_failed.emit(f"Licencia inválida: {exc}")
            return

        try:
            IQClient().login(email, password)
        except IQClientError as exc:
            self.auth_failed.emit(f"Error de autenticación con IQ Option: {exc}")
            return

        self.authenticated.emit(email, password)


def make_auth_worker_thread() -> tuple[QThread, AuthWorker]:
    thread = QThread()
    worker = AuthWorker()
    worker.moveToThread(thread)
    return thread, worker
