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
from byblue.strategy.mhi import MHIStrategy

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 1
HEARTBEAT_INTERVAL_SECONDS = 15

STRATEGIES = {
    FiveMinuteStrategy.name: FiveMinuteStrategy,
    MHIStrategy.name: MHIStrategy,
}


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
        strategy_name: str = FiveMinuteStrategy.name,
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
        self.strategy_name = strategy_name
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
        try:
            self._run_loop()
        except Exception as exc:  # noqa: BLE001 - never let the worker die silently
            logger.exception("Trading loop crashed")
            self._running = False
            self.stopped.emit(f"Error inesperado, el bot se detuvo: {exc}")

    def stop(self) -> None:
        self._running = False

    def _connect(self) -> None:
        s = self._settings
        if not self._client.connected:
            self.log_message.emit(f"Conectando a IQ Option como {s.email}...")
            self._client.login(s.email, s.password)
            self.log_message.emit("Conectado.")
        self._client.change_balance(s.balance_mode)
        self.balance_updated.emit(self._client.get_balance())

    def _run_loop(self) -> None:
        s = self._settings
        strategy_cls = STRATEGIES.get(s.strategy_name, FiveMinuteStrategy)
        strategy = strategy_cls()
        risk = RiskManager(
            RiskConfig(
                base_stake=s.base_stake,
                stop_win=s.stop_win,
                stop_loss=s.stop_loss,
                mg_multiplier=s.mg_multiplier,
                mg_max_levels=s.mg_max_levels,
            )
        )
        feed = CandleFeed(self._client, s.asset, on_debug=self.log_message.emit)

        self.log_message.emit(f"Iniciando {strategy.name} en {s.asset}...")
        last_heartbeat = time.time()

        while self._running:
            if time.time() - last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
                last_heartbeat = time.time()
                self.log_message.emit(f"(activo, esperando cierre de vela de {s.asset}...)")
            try:
                new_candle = feed.poll_for_new_closed_candle()
            except IQClientError as exc:
                self.log_message.emit(f"Error al pedir velas: {exc}")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            except Exception as exc:  # noqa: BLE001 - never let the worker die silently
                logger.exception("Unexpected error polling candles")
                self.log_message.emit(f"Error inesperado: {exc}")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if new_candle is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            signal = strategy.on_new_candle(feed.history)

            if risk.in_martingala():
                # Martingala rule: repeat the SAME direction as the losing
                # trade with the multiplied stake, ignoring the strategy's
                # fresh read of this candle until the level resolves.
                direction = risk.pending_direction
                reason = f"Martingala nivel {risk.mg_level}/{s.mg_max_levels}"
            else:
                direction = signal.direction
                reason = signal.reason

            if direction is None:
                self.log_message.emit(f"{new_candle.timestamp}: sin entrada ({reason})")
                if reason == "N/A":
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
            self.log_message.emit(
                f"Señal detectada: {direction.value} en {s.asset} por {stake} ({reason}). Comprando..."
            )
            try:
                order_id = self._client.place_order(s.mode, s.asset, stake, direction, s.expiration_minutes)
                self.log_message.emit(f"Orden {order_id} colocada, esperando resultado...")
                result, payout = self._client.check_result(s.mode, order_id, s.expiration_minutes)
            except IQClientError as exc:
                self.log_message.emit(f"Error al operar: {exc}")
                continue

            profit = payout if result == "win" else (-stake if result == "loss" else 0.0)
            risk.register_result(direction, profit)

            trade = {
                "asset": s.asset,
                "direction": direction.value,
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
