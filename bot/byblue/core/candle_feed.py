"""Detects newly closed 1-minute candles for a given asset.

Polls IQClient.get_candles once per second (simple, robust fallback —
streaming can replace this later without changing the Strategy interface)
and only reports a candle once it is fully closed (its timestamp is older
than the current minute boundary) and not already seen.
"""
import time

from byblue.core.iq_client import IQClient
from byblue.core.models import Candle

POLL_INTERVAL_SECONDS = 1
HISTORY_SIZE = 20


class CandleFeed:
    def __init__(self, client: IQClient, asset: str) -> None:
        self._client = client
        self._asset = asset
        self._last_seen_ts: int | None = None
        self.history: list[Candle] = []

    def poll_for_new_closed_candle(self) -> Candle | None:
        candles = self._client.get_candles(self._asset, HISTORY_SIZE)
        if not candles:
            return None

        now = time.time()
        closed = [c for c in candles if c.timestamp + 60 <= now]
        if not closed:
            return None

        latest = closed[-1]
        if self._last_seen_ts is not None and latest.timestamp <= self._last_seen_ts:
            return None

        self._last_seen_ts = latest.timestamp
        self.history = closed[-HISTORY_SIZE:]
        return latest
