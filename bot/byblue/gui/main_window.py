from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from byblue.core import credentials
from byblue.core.history_store import HistoryStore
from byblue.core.iq_client import IQClient, IQClientError
from byblue.core.models import BalanceMode, OptionMode
from byblue.gui.workers import SessionSettings, make_worker_thread

HISTORY_COLUMNS = ["Hora", "Activo", "Dirección", "Monto", "Resultado", "Payout", "Modo"]


class MainWindow(QMainWindow):
    request_start = pyqtSignal(object)  # SessionSettings
    request_stop = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ByblueTrader")
        self.resize(900, 600)

        self._thread, self._worker = make_worker_thread()
        self._wire_worker()
        self._thread.start()

        self._history_store = HistoryStore()

        self._build_ui()
        self._load_history()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        form = QFormLayout()
        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember_password_check = QCheckBox("Recordar contraseña (cifrada en Windows)")
        self.email_input.editingFinished.connect(self._on_email_changed)

        self.balance_mode_combo = QComboBox()
        self.balance_mode_combo.addItems([m.value for m in BalanceMode])

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([m.value for m in OptionMode])

        self.asset_combo = QComboBox()
        self.refresh_assets_btn = QPushButton("Actualizar activos")
        self.refresh_assets_btn.clicked.connect(self._on_refresh_assets)

        self.stake_input = QDoubleSpinBox()
        self.stake_input.setRange(1, 10000)
        self.stake_input.setValue(1)

        self.stop_win_input = QDoubleSpinBox()
        self.stop_win_input.setRange(1, 100000)
        self.stop_win_input.setValue(20)

        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(1, 100000)
        self.stop_loss_input.setValue(20)

        self.mg_multiplier_input = QDoubleSpinBox()
        self.mg_multiplier_input.setRange(1, 10)
        self.mg_multiplier_input.setSingleStep(0.1)
        self.mg_multiplier_input.setValue(2.0)

        self.mg_levels_input = QSpinBox()
        self.mg_levels_input.setRange(0, 10)
        self.mg_levels_input.setValue(2)

        form.addRow("Email IQ Option:", self.email_input)
        form.addRow("Password:", self.password_input)
        form.addRow("", self.remember_password_check)
        form.addRow("Cuenta:", self.balance_mode_combo)
        form.addRow("Modo:", self.mode_combo)

        asset_row = QHBoxLayout()
        asset_row.addWidget(self.asset_combo)
        asset_row.addWidget(self.refresh_assets_btn)
        form.addRow("Activo:", asset_row)

        form.addRow("Monto base:", self.stake_input)
        form.addRow("Stop Win:", self.stop_win_input)
        form.addRow("Stop Loss:", self.stop_loss_input)
        form.addRow("Martingala multiplicador:", self.mg_multiplier_input)
        form.addRow("Martingala niveles máx.:", self.mg_levels_input)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Iniciar")
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        root.addLayout(btn_row)

        self.status_label = QLabel("Desconectado")
        root.addWidget(self.status_label)

        self.history_table = QTableWidget(0, len(HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(HISTORY_COLUMNS)
        root.addWidget(self.history_table)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(120)
        root.addWidget(self.log_output)

    # ---------- worker wiring ----------
    def _wire_worker(self) -> None:
        self.request_start.connect(self._worker.start, Qt.ConnectionType.QueuedConnection)
        self.request_stop.connect(self._worker.stop, Qt.ConnectionType.QueuedConnection)

        self._worker.log_message.connect(self._on_log)
        self._worker.balance_updated.connect(self._on_balance)
        self._worker.trade_placed.connect(self._on_trade)
        self._worker.stopped.connect(self._on_stopped)
        self._worker.connected.connect(self._on_connected)

    # ---------- actions ----------
    def _on_refresh_assets(self) -> None:
        # Lightweight one-off connection just to list open assets; runs synchronously
        # here because it's a short call typically issued before Start.
        email, password = self.email_input.text(), self.password_input.text()
        if not email or not password:
            QMessageBox.warning(self, "ByblueTrader", "Ingresa email y password primero.")
            return
        try:
            client = IQClient()
            client.login(email, password)
            open_assets = client.get_open_assets()
        except IQClientError as exc:
            QMessageBox.critical(self, "ByblueTrader", str(exc))
            return

        self.asset_combo.clear()
        mode = OptionMode(self.mode_combo.currentText())
        category = "digital" if mode == OptionMode.DIGITAL else "binary"
        self.asset_combo.addItems(open_assets.get(category, []))

    def _on_email_changed(self) -> None:
        email = self.email_input.text()
        if not email:
            return
        saved = credentials.load_password(email)
        if saved:
            self.password_input.setText(saved)
            self.remember_password_check.setChecked(True)

    def _on_start(self) -> None:
        if self.remember_password_check.isChecked():
            credentials.save_password(self.email_input.text(), self.password_input.text())
        else:
            credentials.delete_password(self.email_input.text())

        settings = SessionSettings(
            email=self.email_input.text(),
            password=self.password_input.text(),
            asset=self.asset_combo.currentText(),
            mode=OptionMode(self.mode_combo.currentText()),
            balance_mode=BalanceMode(self.balance_mode_combo.currentText()),
            base_stake=self.stake_input.value(),
            stop_win=self.stop_win_input.value(),
            stop_loss=self.stop_loss_input.value(),
            mg_multiplier=self.mg_multiplier_input.value(),
            mg_max_levels=self.mg_levels_input.value(),
        )
        if not settings.asset:
            QMessageBox.warning(self, "ByblueTrader", "Selecciona un activo (Actualizar activos).")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.request_start.emit(settings)

    def _on_stop(self) -> None:
        self.request_stop.emit()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ---------- worker signal handlers ----------
    def _on_log(self, message: str) -> None:
        self.log_output.append(message)

    def _on_balance(self, balance: float) -> None:
        self.status_label.setText(f"Conectado — Saldo: {balance:.2f}")

    def _on_connected(self, ok: bool) -> None:
        if not ok:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_stopped(self, reason: str) -> None:
        self.status_label.setText(f"Detenido: {reason}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_trade(self, trade: dict) -> None:
        self._append_history_row(trade)

    def _append_history_row(self, trade: dict) -> None:
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        values = [
            str(trade["timestamp"]),
            trade["asset"],
            trade["direction"],
            f"{trade['stake']:.2f}",
            trade["result"],
            f"{trade['payout']:.2f}",
            trade["mode"],
        ]
        for col, value in enumerate(values):
            self.history_table.setItem(row, col, QTableWidgetItem(value))

    def _load_history(self) -> None:
        for row in self._history_store.get_recent_trades():
            self._append_history_row(
                {
                    "timestamp": row["timestamp"],
                    "asset": row["asset"],
                    "direction": row["direction"],
                    "stake": row["stake"],
                    "result": row["result"],
                    "payout": row["payout"],
                    "mode": row["mode"],
                }
            )

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.request_stop.emit()
        self._thread.quit()
        self._thread.wait(2000)
        super().closeEvent(event)
