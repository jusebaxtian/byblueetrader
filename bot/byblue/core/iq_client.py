"""Synchronous wrapper around iqoptionapi.stable_api.IQ_Option.

Every method here is blocking (the underlying library busy-waits on a
background websocket thread). Callers must run this from a worker
thread, never from the GUI thread.
"""
import logging
import threading

from iqoptionapi.stable_api import IQ_Option

from byblue.core.models import BalanceMode, Candle, Direction, OptionMode

logger = logging.getLogger(__name__)

CANDLE_INTERVAL_SECONDS = 60
OPEN_ASSETS_TIMEOUT_SECONDS = 20
ORDER_TIMEOUT_SECONDS = 30
RESULT_TIMEOUT_BUFFER_SECONDS = 60


class IQClientError(Exception):
    pass


class _TimeoutError(Exception):
    pass


def _call_with_timeout(func, args, timeout_seconds):
    """Runs `func(*args)` on a daemon thread and waits up to `timeout_seconds`.

    iqoptionapi calls can busy-wait forever on some accounts/assets. A plain
    `concurrent.futures.ThreadPoolExecutor` doesn't help: its worker threads
    aren't daemons, so a permanently stuck call still blocks interpreter
    shutdown even after `future.result(timeout=...)` raises. A daemon
    `threading.Thread` lets the caller move on and the process exit cleanly,
    abandoning the stuck call.
    """
    result: list = []
    error: list = []

    def runner():
        try:
            result.append(func(*args))
        except Exception as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise _TimeoutError()
    if error:
        raise error[0]
    return result[0]


class IQClient:
    def __init__(self) -> None:
        self._api: IQ_Option | None = None

    @property
    def connected(self) -> bool:
        return self._api is not None and self._api.check_connect()

    def login(self, email: str, password: str) -> None:
        api = IQ_Option(email, password)
        check, reason = api.connect()
        if not check:
            raise IQClientError(f"Login failed: {reason}")
        self._api = api
        logger.info("Connected to IQ Option as %s", email)

    def _require_api(self) -> IQ_Option:
        if self._api is None:
            raise IQClientError("Not connected. Call login() first.")
        return self._api

    def change_balance(self, mode: BalanceMode) -> None:
        self._require_api().change_balance(mode.value)

    def get_balance(self) -> float:
        return self._require_api().get_balance()

    def get_candles(self, asset: str, count: int, end_time: float | None = None) -> list[Candle]:
        import time

        api = self._require_api()
        end_time = end_time or time.time()
        try:
            raw = _call_with_timeout(
                api.get_candles, (asset, CANDLE_INTERVAL_SECONDS, count, end_time), OPEN_ASSETS_TIMEOUT_SECONDS
            )
        except _TimeoutError as exc:
            raise IQClientError(f"Tiempo de espera agotado al pedir velas de {asset}.") from exc

        if raw is None:
            # iqoptionapi returns None (instead of raising) for unknown/rejected assets.
            raise IQClientError(f"No se pudieron obtener velas para '{asset}' (activo inválido o cerrado).")

        return [
            Candle(
                asset=asset,
                timestamp=int(c["from"]),
                open=c["open"],
                close=c["close"],
                high=c["max"],
                low=c["min"],
            )
            for c in raw
        ]

    def buy_binary(self, asset: str, amount: float, direction: Direction, expiration_minutes: int) -> int:
        api = self._require_api()
        action = "call" if direction == Direction.CALL else "put"
        try:
            ok, order_id = _call_with_timeout(api.buy, (amount, asset, action, expiration_minutes), ORDER_TIMEOUT_SECONDS)
        except _TimeoutError as exc:
            raise IQClientError(f"Tiempo de espera agotado al comprar {asset}.") from exc
        if not ok:
            raise IQClientError(f"Binary order rejected for {asset}")
        return order_id

    def check_binary_result(self, order_id: int, expiration_minutes: int = 1) -> tuple[str, float]:
        """Blocks until result known. Returns ("win"|"loss"|"equal", net_profit).

        `check_win_v4` returns the raw status as 'win'/'loose'/'equal' (note:
        'loose', not 'loss') and its second value is already the net
        profit/loss (negative on loss, 0 on tie) — not a gross payout.
        """
        api = self._require_api()
        timeout = expiration_minutes * 60 + RESULT_TIMEOUT_BUFFER_SECONDS
        try:
            raw_status, profit = _call_with_timeout(api.check_win_v4, (order_id,), timeout)
        except _TimeoutError as exc:
            raise IQClientError(f"Tiempo de espera agotado esperando resultado de la orden {order_id}.") from exc
        status = {"win": "win", "loose": "loss", "equal": "equal"}.get(raw_status, raw_status)
        return status, profit

    def buy_digital(self, asset: str, amount: float, direction: Direction, expiration_minutes: int) -> int:
        api = self._require_api()
        action = "call" if direction == Direction.CALL else "put"
        try:
            ok, order_id = _call_with_timeout(
                api.buy_digital_spot, (asset, amount, action, expiration_minutes), ORDER_TIMEOUT_SECONDS
            )
        except _TimeoutError as exc:
            raise IQClientError(f"Tiempo de espera agotado al comprar {asset}.") from exc
        if not ok:
            raise IQClientError(f"Digital order rejected for {asset}")
        return order_id

    def check_digital_result(self, order_id: int, expiration_minutes: int = 1) -> tuple[str, float]:
        """Blocks until result known. Returns ("win"|"loss"|"equal", net_profit).

        `check_win_digital_v2` returns (closed: bool, net_profit) and can
        return (False, None) if the position simply hasn't closed yet on a
        given check — it does not itself retry until settlement. We poll it
        ourselves until closed=True or the overall timeout elapses.
        """
        import time

        api = self._require_api()
        timeout = expiration_minutes * 60 + RESULT_TIMEOUT_BUFFER_SECONDS

        def _poll_until_closed():
            while True:
                closed, profit = api.check_win_digital_v2(order_id)
                if closed:
                    return profit
                time.sleep(1)

        try:
            profit = _call_with_timeout(_poll_until_closed, (), timeout)
        except _TimeoutError as exc:
            raise IQClientError(f"Tiempo de espera agotado esperando resultado de la orden {order_id}.") from exc

        if profit is None or profit == 0:
            return "equal", 0.0
        return ("win", profit) if profit > 0 else ("loss", profit)

    def place_order(self, mode: OptionMode, asset: str, amount: float, direction: Direction, expiration_minutes: int) -> int:
        if mode == OptionMode.BINARY:
            return self.buy_binary(asset, amount, direction, expiration_minutes)
        return self.buy_digital(asset, amount, direction, expiration_minutes)

    def check_result(self, mode: OptionMode, order_id: int, expiration_minutes: int = 1) -> tuple[str, float]:
        if mode == OptionMode.BINARY:
            return self.check_binary_result(order_id, expiration_minutes)
        return self.check_digital_result(order_id, expiration_minutes)
