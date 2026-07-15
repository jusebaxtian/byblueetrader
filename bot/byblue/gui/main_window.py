from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from byblue.core.history_store import HistoryStore
from byblue.core.models import BalanceMode, OptionMode
from byblue.core.popular_assets import popular_assets_for
from byblue.core.version import VERSION
from byblue.gui.workers import STRATEGIES, SessionSettings, make_worker_thread

HISTORY_COLUMNS = ["Activo", "Dirección", "Monto", "Resultado", "Ganancia"]
RESULT_LABELS = {"win": "WIN", "loss": "LOSS", "equal": "EMPATE", "N/A": "N/A"}
GREEN = QColor("#22c55e")
RED = QColor("#e6413a")


class MainWindow(QWidget):
    request_start = pyqtSignal(object)  # SessionSettings
    request_stop = pyqtSignal()

    def __init__(self, email: str = "", password: str = "", license_expires_at: str = "") -> None:
        super().__init__()
        self.setWindowTitle("ByblueTrader")
        self.resize(760, 840)
        self._email = email
        self._password = password
        self._license_expires_at = license_expires_at
        self._session_total = 0.0

        self._thread, self._worker = make_worker_thread()
        self._wire_worker()
        self._thread.start()

        self._history_store = HistoryStore()

        self._build_ui()
        self._populate_popular_assets()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        root.addLayout(self._build_header())
        root.addLayout(self._build_info_row())
        root.addLayout(self._build_config_rows())

        self.history_table = QTableWidget(0, len(HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(HISTORY_COLUMNS)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.history_table, stretch=1)

        self.total_label = QLabel("Total: 0.00")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        root.addWidget(self.total_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(90)
        root.addWidget(self.log_output)

        self.status_label = QLabel("Desconectado")
        self.status_label.setProperty("role", "statusbar")
        root.addWidget(self.status_label)

        version_label = QLabel(f"V. {VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #666666; font-size: 10px;")
        root.addWidget(version_label)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.start_btn = QPushButton("INICIAR")
        self.start_btn.setProperty("role", "primary")
        self.start_btn.clicked.connect(self._on_start)
        row.addWidget(self.start_btn)

        title = QLabel("TRADING AUTOMÁTICO")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(title, stretch=1)

        self.stop_btn = QPushButton("PARAR")
        self.stop_btn.setProperty("role", "danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        row.addWidget(self.stop_btn)

        return row

    def _build_info_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.email_label = QLabel(f"Usuario: {self._email or '—'}")
        self.email_label.setProperty("role", "panel-title")
        row.addWidget(self.email_label)

        row.addStretch()

        self.balance_label = QLabel("Saldo: —")
        self.balance_label.setProperty("role", "panel-title")
        row.addWidget(self.balance_label)

        row.addStretch()

        self.license_label = QLabel(f"Licencia vigente hasta: {self._format_license_date()}")
        self.license_label.setProperty("role", "panel-title")
        row.addWidget(self.license_label)

        return row

    def _format_license_date(self) -> str:
        if not self._license_expires_at:
            return "—"
        try:
            dt = datetime.fromisoformat(self._license_expires_at)
        except ValueError:
            return self._license_expires_at
        return dt.strftime("%d/%m/%Y")

    def _build_config_rows(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(12)

        panels = [
            self._build_gerenciamento_panel(),
            self._build_martingala_panel(),
            self._build_cuenta_panel(),
            self._build_estrategia_panel(),
            self._build_activo_panel(),
            self._build_modo_panel(),
        ]
        for panel in panels:
            panel.setMinimumHeight(130)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        for panel in panels[:3]:
            top_row.addWidget(panel, stretch=1)
        column.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        for panel in panels[3:]:
            bottom_row.addWidget(panel, stretch=1)
        column.addLayout(bottom_row)

        return column

    def _build_gerenciamento_panel(self) -> QGroupBox:
        box = QGroupBox("GERENCIAMIENTO")
        form = QFormLayout(box)

        self.stake_input = QDoubleSpinBox()
        self.stake_input.setRange(1, 10000)
        self.stake_input.setValue(1)
        form.addRow("Entrada:", self.stake_input)

        self.stop_win_input = QDoubleSpinBox()
        self.stop_win_input.setRange(1, 100000)
        self.stop_win_input.setValue(20)
        form.addRow("Stop Win:", self.stop_win_input)

        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(1, 100000)
        self.stop_loss_input.setValue(20)
        form.addRow("Stop Loss:", self.stop_loss_input)

        return box

    def _build_martingala_panel(self) -> QGroupBox:
        box = QGroupBox("MARTINGALA")
        layout = QVBoxLayout(box)

        self.mg_enabled_check = QCheckBox("Activar Martingala")
        self.mg_enabled_check.setChecked(True)
        self.mg_enabled_check.toggled.connect(self._on_martingala_toggled)
        layout.addWidget(self.mg_enabled_check)

        form = QFormLayout()
        layout.addLayout(form)

        self.mg_multiplier_input = QDoubleSpinBox()
        self.mg_multiplier_input.setRange(1, 10)
        self.mg_multiplier_input.setSingleStep(0.1)
        self.mg_multiplier_input.setValue(2.0)
        form.addRow("Multiplicador:", self.mg_multiplier_input)

        self.mg_levels_input = QSpinBox()
        self.mg_levels_input.setRange(2, 3)
        self.mg_levels_input.setValue(2)
        form.addRow("Niveles (2 o 3):", self.mg_levels_input)

        return box

    def _on_martingala_toggled(self, checked: bool) -> None:
        self.mg_multiplier_input.setEnabled(checked)
        self.mg_levels_input.setEnabled(checked)

    def _build_cuenta_panel(self) -> QGroupBox:
        box = QGroupBox("CUENTA")
        layout = QVBoxLayout(box)
        self._balance_mode_group = QButtonGroup(self)
        self._balance_radios: dict[BalanceMode, QRadioButton] = {}

        labels = {BalanceMode.REAL: "REAL", BalanceMode.PRACTICE: "PRUEBA", BalanceMode.TOURNAMENT: "TORNEO"}
        for mode in BalanceMode:
            radio = QRadioButton(labels[mode])
            self._balance_mode_group.addButton(radio)
            self._balance_radios[mode] = radio
            layout.addWidget(radio)
        self._balance_radios[BalanceMode.PRACTICE].setChecked(True)

        return box

    def _build_modo_panel(self) -> QGroupBox:
        box = QGroupBox("OPERACIONES")
        layout = QVBoxLayout(box)
        self._mode_group = QButtonGroup(self)
        self._mode_radios: dict[OptionMode, QRadioButton] = {}

        labels = {OptionMode.BINARY: "BINARIAS", OptionMode.DIGITAL: "DIGITAL"}
        for mode in OptionMode:
            radio = QRadioButton(labels[mode])
            radio.toggled.connect(self._on_mode_toggled)
            self._mode_group.addButton(radio)
            self._mode_radios[mode] = radio
            layout.addWidget(radio)
        self._mode_radios[OptionMode.BINARY].setChecked(True)

        return box

    def _build_estrategia_panel(self) -> QGroupBox:
        box = QGroupBox("ESTRATEGIA")
        layout = QVBoxLayout(box)
        self._strategy_group = QButtonGroup(self)
        self._strategy_radios: dict[str, QRadioButton] = {}

        for name in STRATEGIES:
            radio = QRadioButton(name)
            self._strategy_group.addButton(radio)
            self._strategy_radios[name] = radio
            layout.addWidget(radio)
        first_strategy = next(iter(STRATEGIES))
        self._strategy_radios[first_strategy].setChecked(True)

        return box

    def _current_strategy_name(self) -> str:
        for name, radio in self._strategy_radios.items():
            if radio.isChecked():
                return name
        return next(iter(STRATEGIES))

    def _build_activo_panel(self) -> QGroupBox:
        box = QGroupBox("ACTIVO")
        layout = QVBoxLayout(box)

        self.asset_combo = QComboBox()
        layout.addWidget(self.asset_combo)

        return box

    def _current_mode(self) -> OptionMode:
        for mode, radio in self._mode_radios.items():
            if radio.isChecked():
                return mode
        return OptionMode.BINARY

    def _current_balance_mode(self) -> BalanceMode:
        for mode, radio in self._balance_radios.items():
            if radio.isChecked():
                return mode
        return BalanceMode.PRACTICE

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
    def _populate_popular_assets(self) -> None:
        self.asset_combo.clear()
        self.asset_combo.addItems(popular_assets_for(self._current_mode()))

    def _on_mode_toggled(self, checked: bool) -> None:
        if checked and hasattr(self, "asset_combo"):
            self._populate_popular_assets()

    def _on_start(self) -> None:
        settings = SessionSettings(
            email=self._email,
            password=self._password,
            asset=self.asset_combo.currentText(),
            mode=self._current_mode(),
            balance_mode=self._current_balance_mode(),
            base_stake=self.stake_input.value(),
            stop_win=self.stop_win_input.value(),
            stop_loss=self.stop_loss_input.value(),
            mg_multiplier=self.mg_multiplier_input.value(),
            mg_max_levels=self.mg_levels_input.value() if self.mg_enabled_check.isChecked() else 0,
            strategy_name=self._current_strategy_name(),
        )
        if not settings.asset:
            QMessageBox.warning(self, "ByblueTrader", "Selecciona un activo.")
            return

        self.history_table.setRowCount(0)
        self._session_total = 0.0
        self._update_total_label()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.request_start.emit(settings)

    def _on_stop(self) -> None:
        self.request_stop.emit()
        # Don't re-enable Iniciar yet: the worker may be mid-operation
        # (esperando vela/comprando/esperando resultado) and can take up to
        # ~90s to actually exit. Wait for the real `stopped` signal instead
        # of lying that it already stopped.
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Deteniendo BOT... (puede tardar hasta que termine la operación en curso)")

    # ---------- worker signal handlers ----------
    def _on_log(self, message: str) -> None:
        self.log_output.append(message)
        self.status_label.setText(message)

    def _on_balance(self, balance: float) -> None:
        self.balance_label.setText(f"Saldo: {balance:.2f}")

    def _on_connected(self, ok: bool) -> None:
        if not ok:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_stopped(self, reason: str) -> None:
        self.status_label.setText(f"BOT Detenido — {reason}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_trade(self, trade: dict) -> None:
        self._append_history_row(trade)

    def _append_history_row(self, trade: dict) -> None:
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        profit = trade.get("profit", trade.get("payout", 0.0))
        result_label = RESULT_LABELS.get(trade["result"], trade["result"])

        values = [
            trade["asset"],
            trade["direction"],
            f"{trade['stake']:.2f}",
            result_label,
            f"{profit:+.2f}",
        ]
        for col, value in enumerate(values):
            self.history_table.setItem(row, col, QTableWidgetItem(value))

        gain_item = self.history_table.item(row, HISTORY_COLUMNS.index("Ganancia"))
        if profit > 0:
            gain_item.setForeground(GREEN)
        elif profit < 0:
            gain_item.setForeground(RED)

        if trade["result"] != "N/A":
            self._session_total += profit
            self._update_total_label()

    def _update_total_label(self) -> None:
        self.total_label.setText(f"Total: {self._session_total:+.2f}")
        if self._session_total > 0:
            self.total_label.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {GREEN.name()};")
        elif self._session_total < 0:
            self.total_label.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {RED.name()};")
        else:
            self.total_label.setStyleSheet("font-weight: bold; font-size: 15px;")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.request_stop.emit()
        self._thread.quit()
        self._thread.wait(2000)
        super().closeEvent(event)
