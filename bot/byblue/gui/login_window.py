from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from byblue.core import credentials
from byblue.gui.auth_worker import make_auth_worker_thread


class LoginWindow(QWidget):
    login_succeeded = pyqtSignal(str, str, str)  # email, password, license_expires_at
    request_login = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(360, 260)
        self.setObjectName("LoginWindow")

        self._thread, self._worker = make_auth_worker_thread()
        self.request_login.connect(self._worker.login, Qt.ConnectionType.QueuedConnection)
        self._worker.authenticated.connect(self._on_authenticated)
        self._worker.auth_failed.connect(self._on_auth_failed)
        self._thread.start()

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 20)

        top_row = QHBoxLayout()
        top_row.addStretch()
        close_btn = QPushButton()
        close_btn.setProperty("role", "close")
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)
        root.addLayout(top_row)

        title = QLabel("ByblueTrader")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px;")
        root.addWidget(title)
        root.addSpacing(10)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email IQ Option")
        root.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._on_submit)
        root.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        root.addStretch()

        self.submit_btn = QPushButton("INGRESAR")
        self.submit_btn.setProperty("role", "primary")
        self.submit_btn.clicked.connect(self._on_submit)
        root.addWidget(self.submit_btn)

        saved_email = credentials.load_last_email()
        if saved_email:
            self.email_input.setText(saved_email)
            saved_password = credentials.load_password(saved_email)
            if saved_password:
                self.password_input.setText(saved_password)

    def _on_submit(self) -> None:
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if not email or not password:
            self._show_error("Ingresa email y contraseña.")
            return

        self.error_label.setVisible(False)
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Verificando...")
        self.request_login.emit(email, password)

    def _on_authenticated(self, email: str, password: str, license_expires_at: str) -> None:
        credentials.save_password(email, password)
        credentials.save_last_email(email)
        self.login_succeeded.emit(email, password, license_expires_at)
        self.close()

    def _on_auth_failed(self, message: str) -> None:
        self.submit_btn.setEnabled(True)
        self.submit_btn.setText("INGRESAR")
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._thread.quit()
        self._thread.wait(2000)
        super().closeEvent(event)
