"""QThread worker: owns every blocking IQ_Option call.

The GUI thread only ever touches this via signals/slots (QueuedConnection),
so a blocked iqoptionapi call can never freeze the window.
"""
import logging
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from byblue.core.bot_config import LICENSE_API_KEY, LICENSE_BACKEND_URL
from byblue.core.candle_feed import CandleFeed
from byblue.core.history_store import HistoryStore
from byblue.core.iq_client import IQClient, IQClientError
from byblue.core.license_client import LicenseClient, LicenseError
from byblue.core.models import BalanceMode, OptionMode
from byblue.core.risk_manager import RiskConfig, RiskManager
from byblue.strategy.five_minute import FiveMinuteStrategy

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 1


class SessionSettings:
    def __init__(
        self,
        email: str,
        password: str,
        asset: str,
        mode: OptionMode,
        balance_mode: BalanceMode,
        base_stake: float,
        stop_win: float,
        stop_loss: float,
        mg_multiplier: float,
        mg_max_levels: int,
        expiration_minutes: int = 1,
    ) -> None:
        self.email = email
        self.password = password
        self.asset = asset
        self.mode = mode
        self.balance_mode = balance_mode
        self.base_stake = base_stake
        self.stop_win = stop_win
        self.stop_loss = stop_loss
        self.mg_multiplier = mg_multiplier
        self.mg_max_levels = mg_max_levels
        self.expiration_minutes = expiration_minutes


class TradingWorker(QObject):
    log_message = pyqtSignal(str)
    balance_updated = pyqtSignal(float)
    trade_placed = pyqtSignal(dict)  # asset, direction, stake, result, payout, mode
    stopped = pyqtSignal(str)  # reason
    connected = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._client = IQClient()
        self._history_store = HistoryStore()
        self._license_client = LicenseClient(LICENSE_BACKEND_URL, LICENSE_API_KEY)
        self._running = False
        self._settings: SessionSettings | None = None

    def start(self, settings: SessionSettings) -> None:
        self._settings = settings
        self._running = True

        try:
            self.log_message.emit("Verificando licencia...")
            self._license_client.validate(settings.email)
        except LicenseError as exc:
            self.connected.emit(False)
            self.stopped.emit(f"Licencia inválida: {exc}")
            self._running = False
            return

        try:
            self._connect()
        except IQClientError as exc:
            self.connected.emit(False)
            self.stopped.emit(str(exc))
            self._running = False
            return

        self.connected.emit(True)
        self._run_loop()

    def stop(self) -> None:
        self._running = False

    def _connect(self) -> None:
        s = self._settings
        self.log_message.emit(f"Conectando a IQ Option como {s.email}...")
        self._client.login(s.email, s.password)
        self._client.change_balance(s.balance_mode)
        self.balance_updated.emit(self._client.get_balance())
        self.log_message.emit("Conectado.")

    def _run_loop(self) -> None:
        s = self._settings
        strategy = FiveMinuteStrategy()
        risk = RiskManager(
            RiskConfig(
                base_stake=s.base_stake,
                stop_win=s.stop_win,
                stop_loss=s.stop_loss,
                mg_multiplier=s.mg_multiplier,
                mg_max_levels=s.mg_max_levels,
            )
        )
        feed = CandleFeed(self._client, s.asset)

        self.log_message.emit(f"Iniciando {strategy.name} en {s.asset}...")

        while self._running:
            new_candle = feed.poll_for_new_closed_candle()
            if new_candle is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            signal = strategy.on_new_candle(feed.history)
            if signal.direction is None:
                self.log_message.emit(f"{new_candle.timestamp}: sin entrada ({signal.reason})")
                if signal.reason == "N/A":
                    na_trade = {
                        "timestamp": new_candle.timestamp,
                        "asset": s.asset,
                        "direction": "N/A",
                        "stake": 0.0,
                        "result": "N/A",
                        "payout": 0.0,
                        "mode": s.mode.value,
                        "strategy": strategy.name,
                    }
                    self._history_store.add_trade(na_trade)
                    self.trade_placed.emit(na_trade)
                continue

            if risk.should_stop():
                self.stopped.emit("Stop Win/Loss alcanzado")
                self._running = False
                break

            stake = risk.next_stake()
            try:
                order_id = self._client.place_order(s.mode, s.asset, stake, signal.direction, s.expiration_minutes)
                result, payout = self._client.check_result(s.mode, order_id)
            except IQClientError as exc:
                self.log_message.emit(f"Error al operar: {exc}")
                continue

            profit = payout if result == "win" else (-stake if result == "loss" else 0.0)
            risk.register_result(signal.direction, profit)

            trade = {
                "asset": s.asset,
                "direction": signal.direction.value,
                "stake": stake,
                "result": result,
                "payout": payout,
                "mode": s.mode.value,
                "strategy": strategy.name,
                "timestamp": new_candle.timestamp,
            }
            self._history_store.add_trade(trade)
            self.trade_placed.emit(trade)
            self.balance_updated.emit(self._client.get_balance())

            if risk.should_stop():
                self.stopped.emit("Stop Win/Loss alcanzado")
                self._running = False
                break

        if self._running is False:
            self.log_message.emit("Detenido.")


def make_worker_thread() -> tuple[QThread, TradingWorker]:
    thread = QThread()
    worker = TradingWorker()
    worker.moveToThread(thread)
    return thread, worker
