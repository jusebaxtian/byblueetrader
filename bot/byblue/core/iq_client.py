"""Synchronous wrapper around iqoptionapi.stable_api.IQ_Option.

Every method here is blocking (the underlying library busy-waits on a
background websocket thread). Callers must run this from a worker
thread, never from the GUI thread.
"""
import logging

from iqoptionapi.stable_api import IQ_Option

from byblue.core.models import BalanceMode, Candle, Direction, OptionMode

logger = logging.getLogger(__name__)

CANDLE_INTERVAL_SECONDS = 60


class IQClientError(Exception):
    pass


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

    def get_open_assets(self) -> dict[str, list[str]]:
        """Returns {"binary": [...], "turbo": [...], "digital": [...]} of open asset names."""
        api = self._require_api()
        open_time = api.get_all_open_time()
        result: dict[str, list[str]] = {}
        for category in ("binary", "turbo", "digital"):
            assets = open_time.get(category, {})
            result[category] = [name for name, info in assets.items() if info.get("open")]
        return result

    def get_candles(self, asset: str, count: int, end_time: float | None = None) -> list[Candle]:
        import time

        api = self._require_api()
        end_time = end_time or time.time()
        raw = api.get_candles(asset, CANDLE_INTERVAL_SECONDS, count, end_time)
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
        ok, order_id = api.buy(amount, asset, action, expiration_minutes)
        if not ok:
            raise IQClientError(f"Binary order rejected for {asset}")
        return order_id

    def check_binary_result(self, order_id: int) -> tuple[str, float]:
        """Blocks until result known. Returns ("win"|"loss"|"equal", payout)."""
        api = self._require_api()
        result, payout = api.check_win_v4(order_id)
        return result, payout

    def buy_digital(self, asset: str, amount: float, direction: Direction, expiration_minutes: int) -> int:
        api = self._require_api()
        action = "call" if direction == Direction.CALL else "put"
        ok, order_id = api.buy_digital_spot(asset, amount, action, expiration_minutes)
        if not ok:
            raise IQClientError(f"Digital order rejected for {asset}")
        return order_id

    def check_digital_result(self, order_id: int) -> tuple[str, float]:
        api = self._require_api()
        result, payout = api.check_win_digital_v2(order_id)
        return result, payout

    def place_order(self, mode: OptionMode, asset: str, amount: float, direction: Direction, expiration_minutes: int) -> int:
        if mode == OptionMode.BINARY:
            return self.buy_binary(asset, amount, direction, expiration_minutes)
        return self.buy_digital(asset, amount, direction, expiration_minutes)

    def check_result(self, mode: OptionMode, order_id: int) -> tuple[str, float]:
        if mode == OptionMode.BINARY:
            return self.check_binary_result(order_id)
        return self.check_digital_result(order_id)
